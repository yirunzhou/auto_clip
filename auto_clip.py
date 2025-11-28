import argparse
import json
from datetime import datetime
from pathlib import Path

from auto_clip_lib.captions import find_best_segment, parse_captions
from auto_clip_lib.chunking import chunk_segments
from auto_clip_lib.config import (
    NO_SEARCH_RESULT,
    OUTPUT_DIR,
    RESULT_JSON,
    SEARCH_RESULTS,
    TRANSCRIPT_SOURCES,
)
from auto_clip_lib.keywords import extract_keywords
from auto_clip_lib.media import download_transcript, download_video, trim_clip
from auto_clip_lib.queries import generate_queries
from auto_clip_lib.searchers import search_archive_org, search_nasa, search_youtube
from auto_clip_lib.utils import sanitize_id

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


def main():
    parser = argparse.ArgumentParser(
        description="Automate geopolitical video clip fetching and trimming."
    )
    parser.add_argument(
        "srt_file", type=str, help="Path to the source SRT caption file."
    )
    parser.add_argument(
        "--download-clips",
        action="store_true",
        help="Download and trim clips instead of metadata-only mode (default).",
    )
    args = parser.parse_args()

    srt_file = Path(args.srt_file)
    download_enabled = args.download_clips

    srt_base_name = srt_file.stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_output_dir = Path(OUTPUT_DIR) / f"{srt_base_name}_{timestamp}"

    unique_output_dir.mkdir(parents=True, exist_ok=True)
    trimmed_dir = unique_output_dir / "trimmed"
    trimmed_dir.mkdir(exist_ok=True)

    print(f"→ Parsing captions from {srt_file.name}...")
    segments = parse_captions(str(srt_file))

    segments = chunk_segments(segments)
    print(f"→ Regrouped into {len(segments)} multi-sentence segments for search.")

    print("→ Extracting keywords...")
    segments = extract_keywords(segments)

    if download_enabled:
        print("→ Download mode enabled: clips will be downloaded and trimmed.")
    else:
        print("→ Metadata-only mode: skipping clip downloads.")

    search_providers = (
        # (search_archive_org, "Archive.org"),
        # (search_cspan, "C-SPAN"),  # Enable once API token is available
        # (search_nasa, "NASA"),
        (search_youtube, "YouTube"),
    )

    for i, seg in enumerate(segments):
        query_candidates = generate_queries(seg)
        print(f"[{i}] Searching: {query_candidates[0]}")
        seg["queries_tried"] = query_candidates
        results = []

        for search_func, label in search_providers:
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

        #        chosen = results[0]
        #
        #        seg["clip_source"] = chosen["source"]
        #        seg["clip_source_url"] = chosen["url"]
        #        if chosen.get("center"):
        #            seg["clip_source_center"] = chosen["center"]
        #        if chosen.get("channel"):
        #            seg["clip_source_channel"] = chosen["channel"]
        #
        #        if not download_enabled:
        #            seg["clip_file"] = None
        #            continue
        #
        #        clip_path = download_video(chosen, str(unique_output_dir))
        #        if not clip_path:
        #            print("  ⚠️ Skipping clip due to download error.")
        #            continue
        #
        #        transcript_path = None
        #        if chosen["source"] in TRANSCRIPT_SOURCES:
        #            transcript_path = download_transcript(
        #                chosen["id"],
        #                chosen.get("download_url") or chosen["url"],
        #                str(unique_output_dir),
        #            )
        #        if transcript_path:
        #            transcript_segments = parse_captions(transcript_path)
        #            best_seg = find_best_segment(seg["text"], transcript_segments)
        #            if best_seg:
        #                start_time = best_seg["start"]
        #                end_time = best_seg["end"]
        #                print(
        #                    f"  ✅ Found best clip at {start_time:.2f}s from {chosen['source']}"
        #                )
        #            else:
        #                start_time, end_time = seg["start"], seg["end"]
        #        else:
        #            start_time, end_time = seg["start"], seg["end"]
        #
        #        safe_source_id = sanitize_id(chosen["id"])
        #        out_file = trimmed_dir / f"seg_{i}_{safe_source_id}.mp4"
        #        trim_clip(clip_path, start_time, end_time, str(out_file))
        #        seg["clip_file"] = str(out_file)

    with open(unique_output_dir / RESULT_JSON, "w") as f:
        json.dump(segments, f, indent=2)

    if download_enabled:
        # print(f"\n✅ Done. Clips saved under {unique_output_dir}/trimmed/")
        print("Download not supported yet")
    else:
        print("\n✅ Done. Metadata collected without downloading clips.")
    print(f"Metadata: {unique_output_dir}/{RESULT_JSON}")


if __name__ == "__main__":
    main()
