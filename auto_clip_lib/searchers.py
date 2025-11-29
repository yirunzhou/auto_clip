"""Search adapters for each media source."""

import json
import subprocess

import internetarchive
import requests

from auto_clip_lib.utils import sanitize_id
from auto_clip_lib.utils import ytdlp_cmd


def search_archive_org(query: str, max_results: int = 3) -> list[dict]:
    try:
        search_results = internetarchive.search_items(
            f'({query}) AND mediatype:(movies)'
        )
        results = []
        for r in search_results:
            item = internetarchive.get_item(r['identifier'])
            video_url = f"https://archive.org/details/{item.identifier}"
            license_url = item.metadata.get('licenseurl', 'N/A')
            results.append({
                'title': item.metadata.get('title', 'No Title'),
                'id': item.identifier,
                'url': video_url,
                'license': license_url,
                'source': 'archive.org'
            })
            if len(results) >= max_results:
                break
        return results
    except Exception as e:
        print(f"  Archive.org search error: {e}")
        return []


def search_cspan(query: str, max_results: int = 3) -> list[dict]:
    try:
        params = {
            "searchtype": "Videos",
            "sort": "Most+Recent",
            "format": "json",
            "query": query,
            "number": max_results,
        }
        resp = requests.get("https://www.c-span.org/search/api/", params=params, timeout=10)
        resp.raise_for_status()
        payload = resp.json()
        raw_results = payload.get("results") or payload.get("items") or []
        results = []
        for item in raw_results:
            video_id = str(item.get("id") or item.get("programid") or item.get("programId") or "")
            video_url = item.get("url") or (
                f"https://www.c-span.org/video/?{video_id}" if video_id else None)
            if not video_url:
                continue
            results.append(
                {
                    "title": item.get("title") or item.get("programtitle") or "C-SPAN segment",
                    "id": video_id or sanitize_id(video_url),
                    "url": video_url,
                    "license": "C-SPAN Terms of Service",
                    "source": "c-span",
                }
            )
            if len(results) >= max_results:
                break
        return results
    except Exception as e:
        print(f"  C-SPAN search error: {e}")
        return []


def search_nasa(query: str, max_results: int = 3) -> list[dict]:
    try:
        params = {"q": query, "media_type": "video"}
        resp = requests.get(
            "https://images-api.nasa.gov/search", params=params, timeout=10
        )
        resp.raise_for_status()
        items = resp.json().get("collection", {}).get("items", [])
        results = []
        for item in items:
            data = (item.get("data") or [])
            if not data:
                continue
            meta = data[0]
            nasa_id = meta.get("nasa_id")
            if not nasa_id:
                continue
            asset_resp = requests.get(
                f"https://images-api.nasa.gov/asset/{nasa_id}", timeout=10
            )
            asset_resp.raise_for_status()
            asset_items = asset_resp.json().get("collection", {}).get("items", [])
            mp4_url = None
            for asset in asset_items:
                href = asset.get("href")
                if href and href.lower().endswith(".mp4"):
                    mp4_url = href
                    break
            if not mp4_url:
                continue
            detail_url = f"https://images.nasa.gov/details-{nasa_id}.html"
            results.append(
                {
                    "title": meta.get("title", "NASA video"),
                    "id": nasa_id,
                    "url": detail_url,
                    "download_url": mp4_url,
                    "license": "Public Domain (NASA)",
                    "source": "nasa",
                    "center": meta.get("center"),
                }
            )
            if len(results) >= max_results:
                break
        return results
    except Exception as e:
        print(f"  NASA search error: {e}")
        return []


def search_youtube(query: str, max_results: int = 3) -> list[dict]:
    try:
        yt_query = f"ytsearch{max_results}:{query}"
        proc = subprocess.run(
            [
                ytdlp_cmd(),
                "--dump-json",
                "--default-search",
                "ytsearch",
                yt_query,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0 and not proc.stdout:
            print(f"  YouTube search error (code {proc.returncode}) for '{query}'")
            return []
        results = []
        for line in proc.stdout.strip().splitlines():
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if data.get("_type") == "playlist":
                continue
            video_id = data.get("id")
            if not video_id:
                continue
            results.append(
                {
                    "title": data.get("title", "YouTube video"),
                    "id": video_id,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "license": data.get("license") or "YouTube Terms of Service",
                    "source": "youtube",
                    "channel": data.get("uploader"),
                }
            )
        return results
    except Exception as e:
        print(f"  YouTube search error: {e}")
        return []
