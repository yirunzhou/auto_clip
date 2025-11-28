import argparse
from pathlib import Path

from auto_clip_lib.searchers import search_youtube
from auto_clip_lib.workflow import run_metadata_workflow

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


def main():
    parser = argparse.ArgumentParser(
        description="Automate geopolitical video clip metadata generation."
    )
    parser.add_argument(
        "srt_file", type=str, help="Path to the source SRT caption file."
    )
    args = parser.parse_args()

    srt_file = Path(args.srt_file)

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
        _,
    ) = run_metadata_workflow(
        str(srt_file),
        log_func=print,
        search_providers=search_providers,
        create_trimmed_dir=False,
    )

    print("→ Metadata-only workflow: skipping clip downloads.")

    print("\n✅ Done. Metadata collected without downloading clips.")
    print(f"Metadata: {metadata_path}")


if __name__ == "__main__":
    main()
