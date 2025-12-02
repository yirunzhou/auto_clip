"""Utility helpers used across modules."""

from typing import Any, Dict
import os
import shutil


def ytdlp_cmd() -> str:
    return os.environ.get("YT_DLP_PATH") or shutil.which("yt-dlp") or "yt-dlp"


def sanitize_id(identifier: str | None, fallback: str = "video") -> str:
    identifier = identifier or fallback
    safe = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in identifier)
    return safe or fallback


def compose_video_filename(result: Dict[str, Any], suffix: str) -> str:
    source = sanitize_id(result.get("source"), fallback="source")
    title = sanitize_id(result.get("title"), fallback="title")
    identifier = sanitize_id(result.get("id") or result.get("url"), fallback="video")
    suffix = (suffix or "mp4").lstrip(".")
    base = f"{source}_{title}_{identifier}"
    return f"{base}.{suffix or 'mp4'}"


class LLMQueryStatusError(Exception):
    pass
