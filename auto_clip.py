import json
import os
import subprocess
from pathlib import Path
import argparse

import numpy as np
import pysrt
import torch
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer, util
from datetime import datetime

# ========== CONFIG ==========
SRT_DIR = "input"
OUTPUT_DIR = "output"
RESULT_JSON = "clips_metadata.json"
SEARCH_RESULTS = 2  # how many YouTube results per caption
CLIP_BUFFER = 1.5  # seconds extra for editors
# =============================

model = SentenceTransformer("all-MiniLM-L6-v2")


def parse_captions(srt_path):
    try:
        subs = pysrt.open(srt_path)
    except Exception:
        return []
    segments = []
    for s in subs:
        start = s.start.ordinal / 1000
        end = s.end.ordinal / 1000
        text = s.text.replace("\n", " ").strip()
        if text:
            segments.append({"start": start, "end": end, "text": text})
    return segments


def find_best_segment(original_text, transcript_segments):
    if not transcript_segments:
        return None

    original_embedding = model.encode(original_text, convert_to_tensor=True)
    transcript_texts = [seg["text"] for seg in transcript_segments]
    transcript_embeddings = model.encode(transcript_texts, convert_to_tensor=True)

    cos_scores = util.cos_sim(original_embedding, transcript_embeddings)[0]
    best_match_idx = torch.argmax(cos_scores).item()

    return transcript_segments[best_match_idx]


def extract_keywords(segments):
    kw_model = KeyBERT()
    for seg in segments:
        keywords = kw_model.extract_keywords(
            seg["text"], keyphrase_ngram_range=(1, 2), stop_words="english"
        )
        seg["keywords"] = [k[0] for k in keywords[:3]]
    return segments


def download_transcript(video_id, output_dir):
    url = f"https://www.youtube.com/watch?v={video_id}"
    out_path = os.path.join(output_dir, f"{video_id}.en.srt")
    if not os.path.exists(out_path):
        subprocess.run(
            [
                "yt-dlp",
                "--write-auto-sub",
                "--sub-lang",
                "en",
                "--skip-download",
                "-o",
                out_path,
                url,
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    if os.path.exists(out_path):
        return out_path
    return None


def search_youtube(query, max_results=3):
    """Use yt-dlp to search YouTube without API key"""
    cmd = ["yt-dlp", f"ytsearch{max_results}:{query}", "--get-id", "--get-title"]
    output = subprocess.check_output(cmd).decode().splitlines()
    results = [
        {"title": output[i], "id": output[i + 1]} for i in range(0, len(output), 2)
    ]
    return results


def download_video(video_id, output_dir):
    url = f"https://www.youtube.com/watch?v={video_id}"
    out_path = os.path.join(output_dir, f"{video_id}.mp4")
    if not os.path.exists(out_path):
        subprocess.run(
            ["yt-dlp", "-f", "best[height<=720]", "-o", out_path, url],
            check=False,
        )
    return out_path


def trim_clip(input_file, start, end, output_file):
    duration = max(0.5, end - start + CLIP_BUFFER)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            str(start),
            "-t",
            str(duration),
            "-i",
            input_file,
            "-c",
            "copy",
            output_file,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Automate geopolitical video clip fetching and trimming."
    )
    parser.add_argument(
        "srt_file", type=str, help="Path to the source SRT caption file."
    )
    args = parser.parse_args()

    SRT_FILE = args.srt_file

    # Create a unique output directory based on SRT file name and timestamp
    srt_base_name = Path(SRT_FILE).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_output_dir = Path(OUTPUT_DIR) / f"{srt_base_name}_{timestamp}"

    unique_output_dir.mkdir(parents=True, exist_ok=True)
    trimmed_dir = unique_output_dir / "trimmed"
    trimmed_dir.mkdir(exist_ok=True)

    print(f"→ Parsing captions from {Path(SRT_FILE).name}...")
    segments = parse_captions(SRT_FILE)

    print("→ Extracting keywords...")
    segments = extract_keywords(segments)

    for i, seg in enumerate(segments):
        query = " ".join(seg["keywords"]) or seg["text"].split()[0:3]
        print(f"[{i}] Searching: {query}")
        try:
            results = search_youtube(query, SEARCH_RESULTS)
        except Exception as e:
            print("  search error:", e)
            results = []
        seg["yt_results"] = results

        if not results:
            continue

        # pick the first result for prototype
        vid = results[0]["id"]
        clip_path = download_video(vid, str(unique_output_dir))

        # New logic: find best segment in downloaded video
        transcript_path = download_transcript(vid, str(unique_output_dir))
        if transcript_path:
            transcript_segments = parse_captions(transcript_path)
            best_seg = find_best_segment(seg["text"], transcript_segments)
            if best_seg:
                start_time = best_seg["start"]
                end_time = best_seg["end"]
                print(f"  ✅ Found best clip at {start_time:.2f}s in {vid}")
            else:
                start_time, end_time = seg["start"], seg["end"]
        else:
            # fallback to original timing
            start_time, end_time = seg["start"], seg["end"]

        out_file = trimmed_dir / f"seg_{i}_{vid}.mp4"
        trim_clip(clip_path, start_time, end_time, str(out_file))
        seg["clip_file"] = str(out_file)

    # Save metadata
    with open(unique_output_dir / RESULT_JSON, "w") as f:
        json.dump(segments, f, indent=2)

    print(f"\n✅ Done. Clips saved under {unique_output_dir}/trimmed/")
    print(f"Metadata: {unique_output_dir}/{RESULT_JSON}")


if __name__ == "__main__":
    main()
