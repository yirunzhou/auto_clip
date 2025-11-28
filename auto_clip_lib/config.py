"""Global configuration values for auto_clip."""

SRT_DIR = "input"
OUTPUT_DIR = "output"
RESULT_JSON = "clips_metadata.json"
SEARCH_RESULTS = 10  # how many YouTube results per caption/search
CLIP_BUFFER = 1.5  # seconds extra for editors
TRANSCRIPT_SOURCES = {"archive.org", "c-span", "youtube"}
DIRECT_DOWNLOAD_EXTS = (".mp4", ".mov", ".m4v")
NO_SEARCH_RESULT = "{search_source} returns no result for {keywords}"
