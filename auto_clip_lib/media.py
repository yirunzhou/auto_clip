"""Helpers for downloading and trimming media."""

import os
import shutil
import subprocess

import requests

from auto_clip_lib.config import CLIP_BUFFER, DIRECT_DOWNLOAD_EXTS
from auto_clip_lib.utils import compose_video_filename, sanitize_id


def _ytdlp_cmd() -> str:
    return os.environ.get("YT_DLP_PATH") or shutil.which("yt-dlp") or "yt-dlp"


def download_transcript(video_id: str, video_url: str, output_dir: str) -> str | None:
    safe_id = sanitize_id(video_id)
    out_path = os.path.join(output_dir, f"{safe_id}.en.srt")
    if not os.path.exists(out_path):
        subprocess.run(
            [
                _ytdlp_cmd(),
                "--write-auto-sub",
                "--sub-lang",
                "en",
                "--skip-download",
                "-o",
                out_path,
                video_url,
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    if os.path.exists(out_path):
        return out_path
    return None


def download_video(result: dict, output_dir: str) -> str | None:
    video_url = result.get("download_url") or result.get("url")
    is_direct_file = bool(video_url and video_url.lower().endswith(DIRECT_DOWNLOAD_EXTS))
    suffix = "mp4"
    out_path = os.path.join(output_dir, compose_video_filename(result, suffix))
    if not os.path.exists(out_path):
        if is_direct_file:
            try:
                with requests.get(video_url, stream=True, timeout=30) as resp:
                    resp.raise_for_status()
                    with open(out_path, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
            except Exception as e:
                print(f"  Direct download error for {video_url}: {e}")
                return None
        else:
            proc = subprocess.run(
                [
                    _ytdlp_cmd(),
                    "-f",
                    "best[height<=720]",
                    "-o",
                    out_path,
                    video_url,
                ],
                check=False,
            )
            if proc.returncode != 0:
                return None

    if not os.path.exists(out_path):
        return None
    return out_path


def trim_clip(input_file: str, start: float, end: float, output_file: str) -> None:
    duration = max(0.5, end - start + CLIP_BUFFER)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            str(start),
            "-t",
            str(duration),
            "-i",
            input_file,
            "-c",
            "copy",
            output_file,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
