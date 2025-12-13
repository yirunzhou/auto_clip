"""Flask application for running auto_clip workflows via a browser."""

from __future__ import annotations

import json
import tempfile
import logging
from pathlib import Path
from typing import Any, Tuple

from flask import Flask, render_template, request

from auto_clip_lib.config import OUTPUT_DIR
from auto_clip_lib.media import download_video, trim_clip
from auto_clip_lib.utils import sanitize_id
from auto_clip_lib.workflow import (
    run_metadata_workflow,
    run_paginated_workflow,
    run_youtube_links_workflow,
)


app = Flask(__name__)
OUTPUT_BASE = Path(OUTPUT_DIR).resolve()
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "web_app.log"

LOG_FILE_HANDLER = logging.FileHandler(LOG_FILE, encoding="utf-8")
LOG_FILE_HANDLER.setLevel(logging.INFO)
LOG_FILE_HANDLER.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
)

logging.basicConfig(level=logging.INFO, handlers=[LOG_FILE_HANDLER])
LOGGER = logging.getLogger(__name__)
PAGE_SIZE = 8


def _log_exception(message: str, **context: Any) -> None:
    LOGGER.exception("%s | context=%s", message, context)


def _ensure_output_path(path_str: str) -> Path:
    path = Path(path_str).resolve()
    if not str(path).startswith(str(OUTPUT_BASE)):
        raise ValueError("Invalid output directory")
    if not path.exists():
        raise ValueError("Output path does not exist")
    return path


def _load_metadata(metadata_path: str) -> Any:
    meta_path = _ensure_output_path(metadata_path)
    with meta_path.open() as fh:
        return json.load(fh)


def _parse_time_value(value: str) -> float | None:
    if not value:
        return None
    try:
        numeric = float(value)
    except ValueError as exc:  # pragma: no cover - user input validation
        raise ValueError("Start/end times must be numeric.") from exc
    if numeric < 0:
        raise ValueError("Start/end times must be non-negative.")
    return numeric


def _split_metadata(metadata_obj: Any) -> tuple[list | None, list | None]:
    if isinstance(metadata_obj, list):
        return metadata_obj, None
    if isinstance(metadata_obj, dict):
        return None, metadata_obj.get("videos")
    return None, None


def _download_and_optionally_trim(
    result: dict,
    output_dir_path: Path,
    start_time: float | None,
    end_time: float | None,
    *,
    trimmed_dir: Path | None = None,
) -> Tuple[Path, bool]:
    """Download a video and optionally trim it based on start/end times."""

    video_path_str = download_video(result, str(output_dir_path))
    if not video_path_str:
        raise RuntimeError("Video download failed.")

    saved_path = Path(video_path_str)
    trimmed = False
    if start_time is not None and end_time is not None:
        if end_time <= start_time:
            raise ValueError("End time must be greater than start time.")
        clip_dir = trimmed_dir or (output_dir_path / "trimmed")
        clip_dir.mkdir(exist_ok=True)
        clip_name = (
            f"{sanitize_id(result.get('id') or result.get('title') or 'clip')}_"
            f"{start_time:.2f}_{end_time:.2f}.mp4"
        )
        clip_path = clip_dir / clip_name
        trim_clip(str(saved_path), start_time, end_time, str(clip_path))
        saved_path = clip_path
        trimmed = True
    return saved_path, trimmed


@app.route("/", methods=["GET", "POST"])
def index():
    segments = None
    metadata_path = None
    output_dir = None
    error = None
    status_message = None
    pagination = None
    show_status = False

    if request.method == "POST":
        if request.form.get("continue_page"):
            try:
                start_index = int(request.form.get("next_index") or 0)
                existing_output_dir = request.form.get("output_dir") or ""
                (
                    segments,
                    output_dir_path,
                    metadata_file,
                    next_index,
                    total_segments,
                ) = run_paginated_workflow(
                    None,
                    log_func=None,
                    search_providers=None,
                    start_index=start_index,
                    page_size=PAGE_SIZE,
                    existing_output_dir=existing_output_dir,
                )
                metadata_path = str(metadata_file)
                output_dir = str(output_dir_path)
                pagination = {
                    "next_index": next_index,
                    "total_segments": total_segments,
                    "has_more": next_index < total_segments,
                    "current_start": start_index,
                    "current_end": min(next_index, total_segments),
                }
                show_status = True
            except Exception as exc:
                error = f"Failed to continue pagination: {exc}"
                segments = None
                metadata_path = None
                output_dir = None
                _log_exception("Pagination continue failed", exc=str(exc))
        else:
            upload = request.files.get("srt_file")
            if not upload or not upload.filename:
                error = "Please choose an SRT or DOCX file to upload."
            else:
                suffix = Path(upload.filename).suffix or ".srt"
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        temp_file = Path(tmp.name)
                        upload.save(str(temp_file))
                    output_prefix = Path(upload.filename).stem or "upload"
                    (
                        segments,
                        output_dir_path,
                        metadata_file,
                        next_index,
                        total_segments,
                    ) = run_paginated_workflow(
                        str(temp_file),
                        log_func=None,
                        search_providers=None,
                        start_index=0,
                        page_size=PAGE_SIZE,
                        output_prefix=output_prefix,
                    )
                    metadata_path = str(metadata_file)
                    output_dir = str(output_dir_path)
                    pagination = {
                        "next_index": next_index,
                        "total_segments": total_segments,
                        "has_more": next_index < total_segments,
                        "current_start": 0,
                        "current_end": min(next_index, total_segments),
                    }
                    show_status = True
                    LOGGER.info(
                        "Processed transcript upload '%s' → %s",
                        upload.filename,
                        metadata_path,
                    )
                except Exception as exc:  # pragma: no cover - runtime diagnostics
                    error = f"Failed to process file: {exc}"
                    segments = None
                    metadata_path = None
                    output_dir = None
                    _log_exception(
                        "Transcript processing failed",
                        filename=upload.filename,
                        exc=str(exc),
                    )
                finally:
                    if "temp_file" in locals():
                        temp_file.unlink(missing_ok=True)

    if show_status and segments:
        if any((seg.get("_keyword_source") == "keybert") for seg in segments):
            status_message = (
                "Warning: LLM keyword search failed; using local KeyBERT. "
                "Set DASHSCOPE_API_KEY in your .env (see .env.example) if you "
                "expect LLM keywords."
            )

    return render_template(
        "index.html",
        segments=segments,
        metadata_path=metadata_path,
        output_dir=output_dir,
        error=error,
        status_message=status_message,
        pagination=pagination,
    )


@app.route("/youtube-links", methods=["GET", "POST"])
def youtube_links():
    videos = None
    metadata_path = None
    output_dir = None
    raw_links = ""
    error = None
    status_message = None

    if request.method == "POST":
        raw_links = request.form.get("links", "")
        candidates = [line.strip() for line in raw_links.replace(
            ",", "\n").splitlines() if line.strip()]
        if not candidates:
            error = "Please provide at least one link."
        else:
            try:
                metadata, out_dir, metadata_file = run_youtube_links_workflow(
                    candidates,
                    log_func=None,
                    output_prefix="links",
                )
                videos = metadata.get("videos", [])
                metadata_path = str(metadata_file)
                output_dir = str(out_dir)
                status_message = f"Loaded {len(videos)} video(s)."
                LOGGER.info(
                    "Loaded %d manual links into %s",
                    len(videos),
                    metadata_path,
                )
            except Exception as exc:  # pragma: no cover - runtime diagnostics
                error = f"Failed to load links: {exc}"
                _log_exception(
                    "Manual link ingestion failed",
                    link_count=len(candidates),
                    exc=str(exc),
                )

    return render_template(
        "youtube_links.html",
        videos=videos,
        metadata_path=metadata_path,
        output_dir=output_dir,
        error=error,
        status_message=status_message,
        raw_links=raw_links,
    )


@app.route("/download-clip", methods=["POST"])
def download_clip():
    metadata_path = request.form.get("metadata_path", "").strip()
    output_dir = request.form.get("output_dir", "").strip()
    video_id = request.form.get("video_id", "").strip()
    video_title = request.form.get("video_title", "").strip()
    video_url = request.form.get("video_url", "").strip()
    video_source = request.form.get("video_source", "").strip()
    video_channel = request.form.get("video_channel", "").strip()
    start_raw = request.form.get("start_time", "").strip()
    end_raw = request.form.get("end_time", "").strip()
    page = request.form.get("page", "srt").strip() or "srt"

    segments = None
    videos = None
    error = None
    status_message = None
    metadata_obj = None

    try:
        if not metadata_path or not output_dir:
            raise ValueError("Missing metadata context for download.")
        if not video_url:
            raise ValueError("Missing video URL.")

        metadata_obj = _load_metadata(metadata_path)
        output_dir_path = _ensure_output_path(output_dir)

        result = {
            "id": video_id,
            "title": video_title,
            "url": video_url,
            "source": video_source,
            "channel": video_channel,
        }
        start_time = _parse_time_value(start_raw)
        end_time = _parse_time_value(end_raw)
        saved_path, trimmed = _download_and_optionally_trim(
            result,
            output_dir_path,
            start_time,
            end_time,
        )
        status_message = (
            f"Trimmed clip saved to {saved_path}"
            if trimmed
            else f"Full video saved to {saved_path}"
        )
        LOGGER.info(
            "Downloaded %s (%s); trimmed=%s", video_title or video_id, saved_path, trimmed
        )

    except Exception as exc:  # pragma: no cover - runtime diagnostics
        error = f"Failed to download clip: {exc}"
        metadata_obj = None
        _log_exception(
            "Download clip failed",
            video_id=video_id,
            video_title=video_title,
            video_url=video_url,
            exc=str(exc),
        )

    if metadata_obj is None and metadata_path:
        try:
            metadata_obj = _load_metadata(metadata_path)
        except Exception:
            metadata_obj = None

    segments, videos = _split_metadata(metadata_obj)

    if page == "links":
        raw_links = "\n".join(video.get("url", "") for video in videos or [])
        return render_template(
            "youtube_links.html",
            videos=videos,
            metadata_path=metadata_path or None,
            output_dir=output_dir or None,
            error=error,
            status_message=status_message,
            raw_links=raw_links,
        )

    return render_template(
        "index.html",
        segments=segments,
        metadata_path=metadata_path or None,
        output_dir=output_dir or None,
        error=error,
        status_message=status_message,
    )


@app.route("/download-all", methods=["POST"])
def download_all_links():
    metadata_path = request.form.get("metadata_path", "").strip()
    output_dir = request.form.get("output_dir", "").strip()

    videos = None
    error = None
    status_message = None

    try:
        if not metadata_path or not output_dir:
            raise ValueError("Missing metadata context for download.")

        metadata_obj = _load_metadata(metadata_path)
        output_dir_path = _ensure_output_path(output_dir)

        if not isinstance(metadata_obj, dict) or not metadata_obj.get("videos"):
            raise ValueError("No videos available to download.")

        videos = metadata_obj.get("videos", [])
        trimmed_dir = output_dir_path / "trimmed"
        trimmed_dir.mkdir(exist_ok=True)

        successes = 0
        issues: list[str] = []
        for idx, video in enumerate(videos):
            result = {
                "id": video.get("id"),
                "title": video.get("title"),
                "url": video.get("url"),
                "source": video.get("source"),
                "channel": video.get("channel"),
            }
            try:
                start_time = _parse_time_value(
                    request.form.get(f"start_time_{idx}", "")
                )
                end_time = _parse_time_value(
                    request.form.get(f"end_time_{idx}", "")
                )
                _download_and_optionally_trim(
                    result,
                    output_dir_path,
                    start_time,
                    end_time,
                    trimmed_dir=trimmed_dir,
                )
                successes += 1
            except Exception as exc:
                issues.append(
                    f"{video.get('title') or video.get('id') or 'video'} ({exc})"
                )

        if issues:
            error = f"Issues detected: {', '.join(issues)}"
        status_message = f"Downloaded {successes} video(s)."
        LOGGER.info(
            "Bulk download complete: %d success(es), %d issue(s) → %s",
            successes,
            len(issues),
            metadata_path,
        )

    except Exception as exc:  # pragma: no cover - runtime diagnostics
        error = f"Failed to download all videos: {exc}"
        _log_exception(
            "Bulk download failed",
            metadata_path=metadata_path,
            output_dir=output_dir,
            exc=str(exc),
        )

    if videos is None and metadata_path:
        try:
            metadata_obj = _load_metadata(metadata_path)
            _, videos = _split_metadata(metadata_obj)
        except Exception:
            videos = None

    raw_links = "\n".join(video.get("url", "") for video in videos or [])

    return render_template(
        "youtube_links.html",
        videos=videos,
        metadata_path=metadata_path or None,
        output_dir=output_dir or None,
        error=error,
        status_message=status_message,
        raw_links=raw_links,
    )


if __name__ == "__main__":
    app.run(debug=False)
