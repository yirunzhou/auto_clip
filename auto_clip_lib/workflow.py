"""High-level helpers for running the metadata workflow and persisting output."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .config import OUTPUT_DIR, RESULT_JSON, SEARCH_RESULTS
from .pipeline import build_segments_metadata, LogFn
from .searchers import search_youtube
from .utils import sanitize_id


def run_metadata_workflow(
    srt_path: str,
    *,
    log_func: LogFn | None = print,
    search_providers: Iterable | None = None,
    create_trimmed_dir: bool = True,
    output_prefix: str | None = None,
):
    """Process the SRT file and write clips_metadata.json like the CLI."""

    srt_file = Path(srt_path)
    srt_base_name = (output_prefix or srt_file.stem or "session").strip() or "session"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(OUTPUT_DIR) / f"{srt_base_name}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    trimmed_dir = output_dir / "trimmed"
    if create_trimmed_dir:
        trimmed_dir.mkdir(exist_ok=True)

    segments = build_segments_metadata(
        str(srt_file), log_func=log_func, search_providers=search_providers
    )

    metadata_path = output_dir / RESULT_JSON
    with metadata_path.open("w") as f:
        json.dump(segments, f, indent=2)

    return segments, output_dir, metadata_path, trimmed_dir if create_trimmed_dir else None


def run_keyword_search_workflow(
    query: str,
    *,
    log_func: LogFn | None = print,
    search_limit: int | None = None,
    output_prefix: str | None = None,
):
    """Run a direct keyword search and persist the metadata JSON."""

    raw_query = (query or "").strip()
    if not raw_query:
        raise ValueError("Search query is required")

    safe_prefix = sanitize_id(output_prefix or raw_query, fallback="search")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(OUTPUT_DIR) / f"{safe_prefix}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    limit = search_limit or SEARCH_RESULTS
    try:
        results = search_youtube(raw_query, limit)
        if log_func:
            log_func(f"YouTube search for '{raw_query}' → {len(results)} results")
    except Exception as exc:  # pragma: no cover - network error path
        if log_func:
            log_func(f"YouTube search error: {exc}")
        results = []

    metadata = {
        "query": raw_query,
        "results": results,
        "search_source": "YouTube",
        "generated_at": timestamp,
    }

    metadata_path = output_dir / RESULT_JSON
    with metadata_path.open("w") as f:
        json.dump(metadata, f, indent=2)

    return metadata, output_dir, metadata_path


def _fetch_youtube_details(url: str) -> dict | None:
    try:
        proc = subprocess.run(
            ["venv311/bin/yt-dlp", "--dump-single-json", "--skip-download", url],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return None
        data = json.loads(proc.stdout)
        if data.get("_type") == "playlist":
            entries = data.get("entries") or []
            data = entries[0] if entries else data
        video_id = data.get("id")
        title = data.get("title") or "YouTube video"
        uploader = data.get("uploader")
        webpage_url = data.get("webpage_url") or url
        return {
            "id": video_id,
            "title": title,
            "channel": uploader,
            "url": webpage_url,
            "source": "youtube",
            "duration": data.get("duration"),
            "thumbnail": data.get("thumbnail"),
        }
    except Exception:
        return None


def run_youtube_links_workflow(
    links: Iterable[str],
    *,
    log_func: LogFn | None = print,
    output_prefix: str | None = None,
):
    cleaned = [link.strip() for link in links if link and link.strip()]
    if not cleaned:
        raise ValueError("Please provide at least one YouTube link.")

    details = []
    for url in cleaned:
        info = _fetch_youtube_details(url)
        if not info:
            if log_func:
                log_func(f"Failed to fetch metadata for {url}")
            continue
        details.append(info)

    if not details:
        raise ValueError("Could not retrieve metadata for the provided links.")

    safe_prefix = sanitize_id(output_prefix or "links", fallback="links")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(OUTPUT_DIR) / f"{safe_prefix}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "source": "manual_links",
        "videos": details,
        "generated_at": timestamp,
    }

    metadata_path = output_dir / RESULT_JSON
    with metadata_path.open("w") as f:
        json.dump(metadata, f, indent=2)

    return metadata, output_dir, metadata_path
