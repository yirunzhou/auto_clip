import argparse
from pathlib import Path

from auto_clip_lib.captions import find_best_segment, parse_captions
from auto_clip_lib.config import TRANSCRIPT_SOURCES
from auto_clip_lib.media import download_transcript, download_video, trim_clip
from auto_clip_lib.searchers import search_youtube
from auto_clip_lib.workflow import run_metadata_workflow
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

    print(f"→ Parsing captions from {srt_file.name}...")
    search_providers = (
        # (search_archive_org, "Archive.org"),
        # (search_cspan, "C-SPAN"),  # Enable once API token is available
        # (search_nasa, "NASA"),
        (search_youtube, "YouTube"),
    )
    (
        segments,
        unique_output_dir,
        metadata_path,
        trimmed_dir,
    ) = run_metadata_workflow(
        str(srt_file),
        log_func=print,
        search_providers=search_providers,
        create_trimmed_dir=True,
    )

    if download_enabled:
        print("→ Download mode enabled: clips will be downloaded and trimmed.")
    else:
        print("→ Metadata-only mode: skipping clip downloads.")

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

    if download_enabled:
        # print(f"\n✅ Done. Clips saved under {unique_output_dir}/trimmed/")
        print("Download not supported yet")
    else:
        print("\n✅ Done. Metadata collected without downloading clips.")
    print(f"Metadata: {metadata_path}")


if __name__ == "__main__":
    main()
