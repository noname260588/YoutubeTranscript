"""
YouTube metadata extraction helpers.
Uses yt-dlp in metadata-only mode and never downloads media.
"""

import re

from utils import (
    apply_cookie_browser_option,
    get_cookie_browser_attempts,
    looks_like_youtube_auth_error,
)


METADATA_KEYS = [
    "id",
    "title",
    "description",
    "channel",
    "channel_id",
    "uploader",
    "upload_date",
    "duration",
    "thumbnail",
    "webpage_url",
    "tags",
    "categories",
]


def _empty_metadata() -> dict:
    return {
        "id": "",
        "title": "Unknown",
        "description": "",
        "channel": "",
        "channel_id": "",
        "uploader": "",
        "upload_date": "",
        "duration": 0,
        "thumbnail": "",
        "webpage_url": "",
        "tags": [],
        "categories": [],
    }


def clean_youtube_description(description: str) -> str:
    """Normalize a YouTube description while preserving useful line breaks."""
    if not description:
        return ""

    text = str(description).replace("\r\n", "\n").replace("\r", "\n")
    cleaned_lines = []
    blank_count = 0

    for raw_line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        line = re.sub(r"[-=_]{4,}", "---", line)

        if not line:
            blank_count += 1
            if blank_count <= 1:
                cleaned_lines.append("")
            continue

        blank_count = 0
        cleaned_lines.append(line)

    cleaned = "\n".join(cleaned_lines).strip()
    return re.sub(r"\n{3,}", "\n\n", cleaned)


def _timestamp_to_seconds(timestamp: str) -> int:
    parts = [int(part) for part in timestamp.split(":")]
    seconds = 0
    for part in parts:
        seconds = seconds * 60 + part
    return seconds


def extract_chapters_from_description(description: str) -> list:
    """
    Extract timestamp chapters from a YouTube description.
    Returns dict items: {"timestamp", "seconds", "title"}.
    """
    if not description:
        return []

    chapters = []
    pattern = re.compile(
        r"^\s*(?:[-*•]\s*)?(?:\(?)(?P<time>\d{1,2}:\d{2}(?::\d{2})?)(?:\)?)"
        r"\s*(?:[-–—|:]\s*)?(?P<title>.*)$"
    )

    for line in str(description).replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        match = pattern.match(line)
        if not match:
            continue

        timestamp = match.group("time")
        title = match.group("title").strip(" -–—|:")
        chapters.append({
            "timestamp": timestamp,
            "seconds": _timestamp_to_seconds(timestamp),
            "title": title or "Untitled",
        })

    # Keep stable order but remove duplicate timestamps.
    result = []
    seen = set()
    for chapter in sorted(chapters, key=lambda item: item["seconds"]):
        if chapter["seconds"] in seen:
            continue
        seen.add(chapter["seconds"])
        result.append(chapter)
    return result


def _normalize_info(info: dict) -> dict:
    metadata = _empty_metadata()
    for key in METADATA_KEYS:
        value = info.get(key)
        if key in ("tags", "categories"):
            metadata[key] = value if isinstance(value, list) else []
        elif key == "duration":
            metadata[key] = int(value or 0)
        else:
            metadata[key] = value or metadata[key]
    return metadata


def get_youtube_metadata(url: str) -> dict:
    """
    Return YouTube metadata using yt-dlp without downloading the video.
    Falls back to empty metadata if yt-dlp is unavailable or extraction fails.
    """
    metadata = _empty_metadata()
    metadata["webpage_url"] = url or ""

    if not url:
        return metadata

    try:
        import yt_dlp
    except ImportError:
        return metadata

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "extractor_args": {"youtube": ["player_client=android"]},
    }

    attempts = get_cookie_browser_attempts("Auto")
    for browser in attempts:
        current_opts = apply_cookie_browser_option(ydl_opts, browser)
        try:
            with yt_dlp.YoutubeDL(current_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                extracted = _normalize_info(info or {})
                if not extracted.get("webpage_url"):
                    extracted["webpage_url"] = url
                return extracted
        except yt_dlp.utils.DownloadError as error:
            should_retry = (
                browser is None
                and len(attempts) > 1
                and looks_like_youtube_auth_error(str(error))
            ) or (browser is not None and len(attempts) > 1)
            if should_retry:
                continue
        except Exception:
            if browser is not None and len(attempts) > 1:
                continue

    return metadata

def get_playlist_info(url: str) -> list[dict]:
    """
    Return list of videos from a YouTube playlist using yt-dlp in flat extraction mode.
    Returns [{'id': '...', 'title': '...', 'duration': 123, 'url': '...'}, ...]
    """
    if not url:
        return []

    try:
        import yt_dlp
    except ImportError:
        return []

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "extractor_args": {"youtube": ["player_client=android"]},
    }

    attempts = get_cookie_browser_attempts("Auto")
    for browser in attempts:
        current_opts = apply_cookie_browser_option(ydl_opts, browser)
        try:
            with yt_dlp.YoutubeDL(current_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info or 'entries' not in info:
                    return []
                
                videos = []
                for entry in info['entries']:
                    if entry and entry.get('id'):
                        videos.append({
                            "id": entry.get("id"),
                            "title": entry.get("title") or "Unknown",
                            "duration": entry.get("duration") or 0,
                            "url": entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id')}"
                        })
                return videos
        except yt_dlp.utils.DownloadError as error:
            should_retry = (
                browser is None
                and len(attempts) > 1
                and looks_like_youtube_auth_error(str(error))
            ) or (browser is not None and len(attempts) > 1)
            if should_retry:
                continue
        except Exception:
            if browser is not None and len(attempts) > 1:
                continue

    return []
