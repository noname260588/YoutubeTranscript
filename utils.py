"""
Utility functions for YouTube Knowledge Clipper.
Includes URL parsing, timestamp formatting, filename sanitization, and directory management.
"""

import re
import os
import shutil
from pathlib import Path
from datetime import datetime


def get_base_dir() -> Path:
    """Get the base directory of the application (where app.py lives)."""
    return Path(__file__).parent.resolve()


def extract_video_id(url: str) -> str:
    """
    Extract video ID from various YouTube URL formats.

    Supported formats:
        https://www.youtube.com/watch?v=VIDEO_ID
        https://youtu.be/VIDEO_ID
        https://www.youtube.com/shorts/VIDEO_ID
        https://m.youtube.com/watch?v=VIDEO_ID

    Raises:
        ValueError: If the URL is not a valid YouTube URL.
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL không được để trống.")

    url = url.strip()

    patterns = [
        # Standard and mobile watch URLs
        r'(?:https?://)?(?:www\.|m\.)?youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})',
        # Short URLs
        r'(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})',
        # Shorts URLs
        r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
        # Embed URLs
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    raise ValueError(
        "URL YouTube không hợp lệ. Vui lòng dùng link dạng:\n"
        "• https://www.youtube.com/watch?v=...\n"
        "• https://youtu.be/...\n"
        "• https://www.youtube.com/shorts/..."
    )


def format_timestamp(seconds: float) -> str:
    """
    Format seconds to [HH:MM:SS] timestamp string.

    Args:
        seconds: Time in seconds.

    Returns:
        Formatted timestamp string like [00:01:30].
    """
    seconds = max(0, float(seconds))
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"[{hours:02d}:{minutes:02d}:{secs:02d}]"


def format_srt_timestamp(seconds: float) -> str:
    """
    Format seconds to SRT timestamp format: HH:MM:SS,mmm

    Args:
        seconds: Time in seconds.

    Returns:
        Formatted SRT timestamp string like 00:01:30,500.
    """
    seconds = max(0, float(seconds))
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def sanitize_filename(name: str) -> str:
    """
    Remove or replace characters that are invalid in Windows filenames.

    Args:
        name: Original filename string.

    Returns:
        Sanitized filename safe for Windows.
    """
    if not name:
        return "untitled"

    # Replace invalid Windows filename characters
    invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
    sanitized = re.sub(invalid_chars, '_', name)

    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip('. ')

    # Truncate to reasonable length
    if len(sanitized) > 200:
        sanitized = sanitized[:200]

    return sanitized if sanitized else "untitled"


def ensure_dirs() -> None:
    """Create required directories if they don't exist."""
    base = get_base_dir()
    dirs = ['downloads', 'exports', 'models']
    for d in dirs:
        (base / d).mkdir(exist_ok=True)


def get_ffmpeg_path() -> str | None:
    """
    Find ffmpeg executable path.

    Search order:
        1. ffmpeg/ directory next to app.py
        2. System PATH

    Returns:
        Path to ffmpeg executable, or None if not found.
    """
    # Check local ffmpeg folder first
    local_ffmpeg = get_base_dir() / "ffmpeg" / "ffmpeg.exe"
    if local_ffmpeg.exists():
        return str(local_ffmpeg)

    # Fallback to system PATH
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    return None


def get_ffmpeg_dir() -> str | None:
    """
    Get the directory containing ffmpeg executable.

    Returns:
        Directory path containing ffmpeg, or None if not found.
    """
    ffmpeg_path = get_ffmpeg_path()
    if ffmpeg_path:
        return str(Path(ffmpeg_path).parent)
    return None


def get_current_date() -> str:
    """Return current date as YYYY-MM-DD string."""
    return datetime.now().strftime("%Y-%m-%d")


def get_video_title_from_url(video_id: str) -> str:
    """
    Return a default title based on video ID.
    Actual title fetching is done in audio_service via yt-dlp.
    """
    return f"YouTube Video {video_id}"
