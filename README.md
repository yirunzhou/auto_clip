# auto_clip quickstart

auto_clip helps you turn long transcripts into curated YouTube references. Upload an `.srt`, skim the suggested clips, and (optionally) download or trim them straight from the browser.

## What you need

- Python 3.11+.
- `ffmpeg` on your machine if you plan to trim clips.
- `yt-dlp` (installed automatically with our requirements). Set `YT_DLP_PATH` if you use a custom binary.
- Optional: DashScope/Qwen API keys for smarter keyword extraction.

## One-time setup

1. **Clone & create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install pip-tools
   pip-compile requirements.in
   pip install -r requirements.txt
   ```

## Start the web app

```bash
python web_app.py            # default production-style server
# or, if you need hot reload while developing:
flask --app web_app.py --debug run
```

Then browse to `http://127.0.0.1:5000`:
- **Transcript workflow**: upload an `.srt` and review the suggested segments + YouTube hits.
- **Manual workflow**: paste a list of YouTube links and download or trim them with custom timecodes.

Every request is logged to `logs/web_app.log`, making it easy to share stack traces when editors report issues.

## Prefer the CLI?

Run the metadata pipeline directly:

```bash
python auto_clip.py path/to/video.srt
```

Results are saved under `output/<srt-name>_<timestamp>/clips_metadata.json`.

## Tips

- Install `ffmpeg` via Homebrew (`brew install ffmpeg`), Chocolatey (`choco install ffmpeg`), or grab binaries from https://ffmpeg.org/.
- `yt-dlp` defaults to your PATH or `YT_DLP_PATH`; no need to hardcode the repo’s `venv` path.
- Keep both `requirements.in` (top-level deps) and the compiled `requirements.txt` in version control for reproducible installs.
