# auto_clip quickstart

auto_clip helps you turn long transcripts into curated YouTube references. Upload an `.srt`, skim the suggested clips, and (optionally) download or trim them straight from the browser.

## What you need

- Python 3.11+.
- `ffmpeg` on your machine if you plan to trim clips.
- `yt-dlp` (installed automatically with our requirements). Set `YT_DLP_PATH` if you use a custom binary.
- Optional but highly recommended: DashScope/Qwen API keys for smarter keyword extraction.

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

3. **Configure environment variables**

   Copy `.env.example` to `.env` and fill in the values that apply:
   ```bash
   cp .env.example .env
   ```
   - Set `DASHSCOPE_API_KEY` (and optionally `DASHSCOPE_MODEL` / `DASHSCOPE_ENDPOINT`) if you want LLM-powered keyword extraction via Qwen/DashScope.
   - Set `HF_ENDPOINT` when you are in mainland China (the repo includes `https://hf-mirror.com` as an example).
   - Keep `HF_HOME=./.cache/huggingface` if you plan to store Hugging Face assets under the repo (the cache itself is **not** committed; you must download the models yourself). Otherwise, point it at whatever directory holds your existing Hugging Face cache.

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

## Common issues & fixes

- **“Warning: LLM keyword search failed; using local KeyBERT.”**  
  This banner (and a matching entry in `logs/web_app.log`) means the DashScope/Qwen call failed. Double-check your `.env` matches `.env.example` and that `DASHSCOPE_API_KEY` is populated. If you’re behind a firewall, make sure `DASHSCOPE_ENDPOINT` points at the reachable region endpoint.

- **Hugging Face models can’t download (mainland China / offline).**  
  Set `HF_ENDPOINT=https://hf-mirror.com` (already suggested in `.env.example`) or another mirror, then run (the repo does **not** ship the cache, so this step downloads it for you):
  ```bash
  HF_HOME=./.cache/huggingface python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
  ```
  That preloads the KeyBERT backbone into the repo-local cache. Keep `HF_HOME` pointed at the same directory so future runs stay offline-friendly.

- **DashScope credential mistakes.**  
  Missing or invalid keys cause the keyword extractor to fall back to KeyBERT silently in the CLI. Check `web_app.log` (look for `LLM keyword extraction unavailable`) or rerun with `DASHSCOPE_API_KEY` set correctly.
