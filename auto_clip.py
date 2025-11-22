import argparse
import internetarchive
import json
import os
import subprocess
from pathlib import Path

import numpy as np
import pysrt
import requests
import torch
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer, util
from datetime import datetime
from qwen_helper import fetch_qwen_keywords

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ========== CONFIG ==========
SRT_DIR = "input"
OUTPUT_DIR = "output"
RESULT_JSON = "clips_metadata.json"
SEARCH_RESULTS = 2  # how many YouTube results per caption
CLIP_BUFFER = 1.5  # seconds extra for editors
TRANSCRIPT_SOURCES = {"archive.org", "c-span", "youtube"}
DIRECT_DOWNLOAD_EXTS = (".mp4", ".mov", ".m4v")
# =============================


# logging templates
NO_SEARCH_RESULT = '{search_source} returns no result for {keywords}'

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
        text = seg["text"]
        keywords = fetch_qwen_keywords(text)
        if not keywords:
            keywords = kw_model.extract_keywords(
                text, keyphrase_ngram_range=(1, 2), stop_words="english"
            )
        seg["keywords"] = keywords[:5]
    return segments


def generate_queries(segment, max_attempts=3):
    """Generate a few fallback queries per caption."""
    queries = []
    keywords = [kw for kw in segment.get("keywords", []) if kw]
    joined = " ".join(keywords).strip()
    if joined:
        queries.append(joined)
    if keywords:
        queries.extend(keywords)
    text = segment.get("text", "").strip()
    if text:
        words = text.split()
        snippet = " ".join(words[:5]).strip()
        if snippet:
            queries.append(snippet)
        queries.append(text)
    deduped = []
    seen = set()
    for q in queries:
        q = q.strip()
        if not q:
            continue
        lower = q.lower()
        if lower in seen:
            continue
        deduped.append(q)
        seen.add(lower)
        if len(deduped) >= max_attempts:
            break
    if not deduped:
        deduped.append("geopolitics")
    return deduped


def _sanitize_id(identifier, fallback="video"):
    identifier = identifier or fallback
    safe = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in identifier)
    return safe or fallback


def _compose_video_filename(result, suffix: str) -> str:
    source = _sanitize_id(result.get("source"), fallback="source")
    title = _sanitize_id(result.get("title"), fallback="title")
    identifier = _sanitize_id(result.get("id") or result.get("url"), fallback="video")
    suffix = (suffix or "mp4").lstrip(".")
    base = f"{source}_{title}_{identifier}"
    return f"{base}.{suffix or 'mp4'}"


def download_transcript(video_id, video_url, output_dir):
    safe_id = _sanitize_id(video_id)
    out_path = os.path.join(output_dir, f"{safe_id}.en.srt")
    if not os.path.exists(out_path):
        subprocess.run(
            [
                "venv311/bin/yt-dlp",
                "--write-auto-sub",
                "--sub-lang",
                "en",
                "--skip-download",
                "-o",
                out_path,
                video_url,
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    if os.path.exists(out_path):
        return out_path
    return None


def search_archive_org(query, max_results=3):
    """Search Archive.org for videos."""
    try:
        # Search for items with mediatype 'movies'
        search_results = internetarchive.search_items(
            f'({query}) AND mediatype:(movies)'
        )
        results = []
        for r in search_results:
            item = internetarchive.get_item(r['identifier'])

            # Construct URL
            video_url = f"https://archive.org/details/{item.identifier}"

            # Get license information
            license_url = item.metadata.get('licenseurl', 'N/A')

            results.append({
                'title': item.metadata.get('title', 'No Title'),
                'id': item.identifier,
                'url': video_url,
                'license': license_url,
                'source': 'archive.org'
            })

            if len(results) >= max_results:
                break
        return results
    except Exception as e:
        print(f"  Archive.org search error: {e}")
        return []


def search_cspan(query, max_results=3):
    """Search C-SPAN for relevant videos."""
    try:
        params = {
            "searchtype": "Videos",
            "sort": "Most+Recent",
            "format": "json",
            "query": query,
            "number": max_results,
        }
        resp = requests.get("https://www.c-span.org/search/api/", params=params, timeout=10)
        resp.raise_for_status()
        payload = resp.json()
        raw_results = payload.get("results") or payload.get("items") or []
        results = []
        for item in raw_results:
            video_id = str(item.get("id") or item.get("programid") or item.get("programId") or "")
            video_url = item.get("url") or (
                f"https://www.c-span.org/video/?{video_id}" if video_id else None)
            if not video_url:
                continue
            results.append(
                {
                    "title": item.get("title") or item.get("programtitle") or "C-SPAN segment",
                    "id": video_id or _sanitize_id(video_url),
                    "url": video_url,
                    "license": "C-SPAN Terms of Service",
                    "source": "c-span",
                }
            )
            if len(results) >= max_results:
                break
        return results
    except Exception as e:
        print(f"  C-SPAN search error: {e}")
        return []


def search_nasa(query, max_results=3):
    """Search NASA media API for video clips."""
    try:
        params = {"q": query, "media_type": "video"}
        resp = requests.get(
            "https://images-api.nasa.gov/search", params=params, timeout=10
        )
        resp.raise_for_status()
        items = resp.json().get("collection", {}).get("items", [])
        results = []
        for item in items:
            data = (item.get("data") or [])
            if not data:
                continue
            meta = data[0]
            nasa_id = meta.get("nasa_id")
            if not nasa_id:
                continue
            asset_resp = requests.get(
                f"https://images-api.nasa.gov/asset/{nasa_id}", timeout=10
            )
            asset_resp.raise_for_status()
            asset_items = asset_resp.json().get("collection", {}).get("items", [])
            mp4_url = None
            for asset in asset_items:
                href = asset.get("href")
                if href and href.lower().endswith(".mp4"):
                    mp4_url = href
                    break
            if not mp4_url:
                continue
            detail_url = f"https://images.nasa.gov/details-{nasa_id}.html"
            results.append(
                {
                    "title": meta.get("title", "NASA video"),
                    "id": nasa_id,
                    "url": detail_url,
                    "download_url": mp4_url,
                    "license": "Public Domain (NASA)",
                    "source": "nasa",
                    "center": meta.get("center"),
                }
            )
            if len(results) >= max_results:
                break
        return results
    except Exception as e:
        print(f"  NASA search error: {e}")
        return []


def search_youtube(query, max_results=3):
    """Search YouTube via yt-dlp's built-in search."""
    try:
        yt_query = f"ytsearch{max_results}:{query}"
        proc = subprocess.run(
            [
                "venv311/bin/yt-dlp",
                "--dump-json",
                "--default-search",
                "ytsearch",
                yt_query,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0 and not proc.stdout:
            print(f"  YouTube search error (code {proc.returncode}) for '{query}'")
            return []
        results = []
        for line in proc.stdout.strip().splitlines():
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if data.get("_type") == "playlist":
                continue
            video_id = data.get("id")
            if not video_id:
                continue
            results.append(
                {
                    "title": data.get("title", "YouTube video"),
                    "id": video_id,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "license": data.get("license") or "YouTube Terms of Service",
                    "source": "youtube",
                    "channel": data.get("uploader"),
                }
            )
        return results
    except Exception as e:
        print(f"  YouTube search error: {e}")
        return []


def download_video(result, output_dir):
    video_url = result.get("download_url") or result.get("url")
    is_direct_file = bool(video_url and video_url.lower().endswith(DIRECT_DOWNLOAD_EXTS))
    suffix = "mp4"
    out_path = os.path.join(output_dir, _compose_video_filename(result, suffix))
    if not os.path.exists(out_path):
        if is_direct_file:
            try:
                with requests.get(video_url, stream=True, timeout=30) as resp:
                    resp.raise_for_status()
                    with open(out_path, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
            except Exception as e:
                print(f"  NASA download error for {video_url}: {e}")
                return None
        else:
            subprocess.run(
                [
                    "venv311/bin/yt-dlp",
                    "-f",
                    "best[height<=720]",
                    "-o",
                    out_path,
                    video_url,
                ],
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
        query_candidates = generate_queries(seg)
        print(f"[{i}] Searching: {query_candidates[0]}")
        seg["queries_tried"] = query_candidates
        results = []
        for search_func, label in (
            (search_archive_org, "Archive.org"),
            # (search_cspan, "C-SPAN"),  # disabled until API token available
            (search_nasa, "NASA"),
            (search_youtube, "YouTube"),
        ):
            source_hits = []
            last_query = query_candidates[0]
            try:
                for attempt, query in enumerate(query_candidates):
                    last_query = query
                    source_hits = search_func(query, SEARCH_RESULTS)
                    if source_hits:
                        if attempt > 0:
                            print(
                                f"  {label} retry #{attempt} succeeded with '{query}'"
                            )
                        break
                    if attempt < len(query_candidates) - 1:
                        print(
                            NO_SEARCH_RESULT.format(
                                search_source=label, keywords=query
                            )
                        )
            except Exception as e:
                print(f"  {label} search error: {e}")
                source_hits = []
            if not source_hits:
                print(
                    NO_SEARCH_RESULT.format(
                        search_source=label, keywords=last_query
                    )
                )
            results.extend(source_hits)
        seg["video_results"] = results

        if not results:
            continue

        # pick the first result for prototype
        chosen = results[0]
        clip_path = download_video(chosen, str(unique_output_dir))
        if not clip_path:
            print("  ⚠️ Skipping clip due to download error.")
            continue

        # New logic: find best segment in downloaded video
        transcript_path = None
        if chosen["source"] in TRANSCRIPT_SOURCES:
            transcript_path = download_transcript(
                chosen["id"], chosen.get("download_url") or chosen["url"], str(unique_output_dir)
            )
        if transcript_path:
            transcript_segments = parse_captions(transcript_path)
            best_seg = find_best_segment(seg["text"], transcript_segments)
            if best_seg:
                start_time = best_seg["start"]
                end_time = best_seg["end"]
                print(
                    f"  ✅ Found best clip at {start_time:.2f}s from {chosen['source']}"
                )
            else:
                start_time, end_time = seg["start"], seg["end"]
        else:
            # fallback to original timing
            start_time, end_time = seg["start"], seg["end"]

        safe_source_id = _sanitize_id(chosen["id"])
        out_file = trimmed_dir / f"seg_{i}_{safe_source_id}.mp4"
        trim_clip(clip_path, start_time, end_time, str(out_file))
        seg["clip_file"] = str(out_file)
        seg["clip_source"] = chosen["source"]
        seg["clip_source_url"] = chosen["url"]
        if chosen.get("center"):
            seg["clip_source_center"] = chosen["center"]
        if chosen.get("channel"):
            seg["clip_source_channel"] = chosen["channel"]

    # Save metadata
    with open(unique_output_dir / RESULT_JSON, "w") as f:
        json.dump(segments, f, indent=2)

    print(f"\n✅ Done. Clips saved under {unique_output_dir}/trimmed/")
    print(f"Metadata: {unique_output_dir}/{RESULT_JSON}")


if __name__ == "__main__":
    main()
