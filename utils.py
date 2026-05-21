"""
Utility functions for YouTube Knowledge Clipper.
Includes URL parsing, timestamp formatting, filename sanitization, and directory management.
"""

import re
import os
import sys
import shutil
from pathlib import Path
from datetime import datetime

COOKIE_BROWSER_PRIORITY = ["edge", "chrome", "firefox", "brave", "vivaldi", "opera"]


def get_base_dir() -> Path:
    """
    Get the base directory of the application.

    - When running as .py script: returns the directory containing app.py
    - When running as PyInstaller .exe: returns the directory containing the .exe file
    """
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller EXE → use the folder where .exe is located
        return Path(sys.executable).parent.resolve()
    else:
        # Running as Python script → use the folder where this .py file is
        return Path(__file__).parent.resolve()

def get_asset_path(filename: str) -> Path:
    """
    Get the absolute path to a resource (icon, image).
    Works for dev environment and for PyInstaller bundle.
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
    except AttributeError:
        base_path = Path(__file__).parent.resolve()
        
    return base_path / filename

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
    Looks in:
        1. External ffmpeg/ directory next to app.py or the executable
        2. Bundled ffmpeg/ directory inside the PyInstaller onefile temp folder
        3. System PATH
    
    Returns:
        Path to ffmpeg executable, or None if not found.
    """
    exe_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    
    # Check external ffmpeg folder first. This lets users override the bundled
    # binary by placing a newer ffmpeg next to the app.
    local_ffmpeg = get_base_dir() / "ffmpeg" / exe_name
    if local_ffmpeg.exists():
        return str(local_ffmpeg)

    # Check for ffmpeg bundled by PyInstaller
    bundled_base = getattr(sys, '_MEIPASS', None)
    if bundled_base:
        bundled_ffmpeg = Path(bundled_base) / "ffmpeg" / exe_name
        if bundled_ffmpeg.exists():
            return str(bundled_ffmpeg)

    # Fallback to system ffmpeg
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


def normalize_cookie_browser(browser: str | None) -> str | None:
    """Normalize a UI cookie-browser value for yt-dlp."""
    if not browser:
        return None

    value = str(browser).strip().lower()
    if value in ("none", "off", "disabled", "no cookies"):
        return None
    if value in ("auto", "automatic"):
        return "auto"

    aliases = {
        "microsoft edge": "edge",
        "ms edge": "edge",
        "google chrome": "chrome",
        "mozilla firefox": "firefox",
        "brave browser": "brave",
    }
    return aliases.get(value, value)


def _existing_paths(paths: list[Path]) -> list[Path]:
    """Return paths that exist without raising on inaccessible profile folders."""
    found = []
    for path in paths:
        try:
            if path.exists():
                found.append(path)
        except OSError:
            continue
    return found


def browser_cookie_store_exists(browser: str | None) -> bool:
    """Return whether a supported browser appears to have a local cookie store."""
    normalized = normalize_cookie_browser(browser)
    local_app_data = Path(os.environ.get("LOCALAPPDATA", ""))
    app_data = Path(os.environ.get("APPDATA", ""))

    if normalized == "firefox":
        profiles_root = app_data / "Mozilla" / "Firefox" / "Profiles"
        try:
            return any(profiles_root.glob("*/cookies.sqlite"))
        except OSError:
            return False

    chromium_roots = {
        "edge": local_app_data / "Microsoft" / "Edge" / "User Data",
        "chrome": local_app_data / "Google" / "Chrome" / "User Data",
        "brave": local_app_data / "BraveSoftware" / "Brave-Browser" / "User Data",
        "vivaldi": local_app_data / "Vivaldi" / "User Data",
    }

    if normalized in chromium_roots:
        root = chromium_roots[normalized]
        cookie_paths = [
            root / "Default" / "Network" / "Cookies",
            root / "Default" / "Cookies",
        ]
        try:
            cookie_paths.extend(root.glob("Profile *\\Network\\Cookies"))
            cookie_paths.extend(root.glob("Profile *\\Cookies"))
        except OSError:
            pass
        return bool(_existing_paths(cookie_paths))

    if normalized == "opera":
        root = app_data / "Opera Software" / "Opera Stable"
        return bool(_existing_paths([
            root / "Network" / "Cookies",
            root / "Cookies",
        ]))

    return False


def get_available_cookie_browsers() -> list[str]:
    """Return priority-ordered browsers that appear to have cookie databases."""
    return [
        browser
        for browser in COOKIE_BROWSER_PRIORITY
        if browser_cookie_store_exists(browser)
    ]


def get_cookie_browser_attempts(browser: str | None) -> list[str | None]:
    """
    Return yt-dlp cookie browser attempts.

    Auto means anonymous first, then detected browser cookie stores. The first
    anonymous attempt keeps normal downloads fast and only uses browser cookies
    when needed.
    """
    normalized = normalize_cookie_browser(browser)
    if normalized == "auto":
        return [None, *get_available_cookie_browsers()]
    if normalized:
        return [normalized]
    return [None]


def apply_cookie_browser_option(ydl_opts: dict, browser: str | None) -> dict:
    """Return a copy of yt-dlp options with browser cookies enabled if requested."""
    opts = dict(ydl_opts)
    normalized = normalize_cookie_browser(browser)
    if normalized and normalized != "auto":
        opts["cookiesfrombrowser"] = (normalized, None, None, None)
    return opts


def looks_like_youtube_auth_error(error_message: str) -> bool:
    """Detect YouTube bot/login errors that are worth retrying with browser cookies."""
    message = str(error_message).lower()
    return any(
        marker in message
        for marker in (
            "sign in to confirm",
            "not a bot",
            "cookies-from-browser",
            "use --cookies",
            "confirm you're not a bot",
            "confirm you’re not a bot",
        )
    )


def get_yt_dlp_progress(progress_info: dict) -> float | None:
    """Return a 0..1 progress value from a yt-dlp progress hook payload."""
    downloaded = progress_info.get("downloaded_bytes")
    total = progress_info.get("total_bytes") or progress_info.get("total_bytes_estimate")
    if not downloaded or not total:
        return None

    try:
        return max(0.0, min(float(downloaded) / float(total), 1.0))
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def format_yt_dlp_progress_message(prefix: str, progress_info: dict) -> str:
    """Build a compact user-facing download progress message."""
    percent = str(progress_info.get("_percent_str", "?")).strip()
    speed = str(progress_info.get("_speed_str", "")).strip()
    eta = str(progress_info.get("_eta_str", "")).strip()

    parts = [part for part in (percent, speed, f"ETA {eta}" if eta else "") if part]
    return f"{prefix} {' • '.join(parts)}" if parts else prefix


def notify_progress(progress_callback, message: str, progress: float | None = None) -> None:
    """Call progress callback while preserving compatibility with one-arg callbacks."""
    if not progress_callback:
        return

    try:
        progress_callback(message, progress)
    except TypeError:
        progress_callback(message)
