# auto_clip

Browser-based and CLI tooling that ingests long-form SRT transcripts and searches for related YouTube footage for editors.

## Prerequisites

- Python 3.11 or newer.
- `ffmpeg` in your `PATH` for any future media processing (not required if you only gather metadata).
- `yt-dlp` installed via pip (included in `requirements.txt` once you install deps).
- (Optional) API tokens such as DashScope/Qwen for advanced keyword extraction.

## Installation

1. **Create and activate a virtual environment** (recommended to keep dependencies isolated):

   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

2. **Install dependencies**. If you use `pip-tools`, compile the lockfile once:

   ```bash
   pip install pip-tools
   pip-compile requirements.in  # only needed when deps change
   ```

   Then install the pinned requirements:

   ```bash
   pip install -r requirements.txt
   ```

If you prefer not to use `pip-tools`, maintain `requirements.txt` manually with the top-level packages and run only the last command.

## Running the CLI

Generate metadata (and optionally clips) for an SRT file:

```bash
python auto_clip.py path/to/video.srt  # metadata only
```

Output lives under `output/<srt-name>_<timestamp>/clips_metadata.json`.

## Running the Web App

Launch the Flask UI for both transcript and manual-link workflows:

```bash
FLASK_APP=web_app.py FLASK_ENV=production FLASK_DEBUG=0 flask run
# or simply
python web_app.py
```

Navigate to `http://127.0.0.1:5000` and upload an `.srt` for metadata or paste YouTube links for manual downloads.

## Notes

- Ensure `ffmpeg` is installed (`brew install ffmpeg`, `choco install ffmpeg`, or grab it from https://ffmpeg.org/).
- The app shells out to `yt-dlp` via `venv311/bin/yt-dlp`; update the path if you run outside this repo’s layout.
- For reproducible installs on CI or other hosts, commit both `requirements.in` and the compiled `requirements.txt`.
