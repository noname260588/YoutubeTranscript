"""
Audio Service for YouTube Knowledge Clipper.
Downloads audio from YouTube videos using yt-dlp and converts to MP3 via ffmpeg.
"""

import os
from pathlib import Path
from utils import (
    apply_cookie_browser_option,
    get_base_dir,
    get_cookie_browser_attempts,
    get_ffmpeg_dir,
    get_ffmpeg_path,
    looks_like_youtube_auth_error,
    sanitize_filename,
)


class AudioDownloadError(Exception):
    """Raised when audio download fails."""
    pass


def download_audio(
    video_url: str,
    output_dir: str = "downloads",
    cookie_browser: str | None = "Auto",
    progress_callback=None
) -> tuple[str, str]:
    """
    Download audio from a YouTube video and convert to MP3.

    Args:
        video_url: Full YouTube video URL.
        output_dir: Directory to save the audio file (relative to base dir).
        cookie_browser: Browser to read cookies from if YouTube requires login.
                        'Auto' tries anonymous first, then common browsers.
        progress_callback: Optional callback function for progress updates.
                          Called with (status_message: str).

    Returns:
        Tuple of (audio_file_path, video_title).

    Raises:
        AudioDownloadError: If download or conversion fails.
    """
    try:
        import yt_dlp
    except ImportError:
        raise AudioDownloadError(
            "yt-dlp chưa được cài đặt.\n"
            "Chạy: pip install yt-dlp"
        )

    # Check ffmpeg
    ffmpeg_path = get_ffmpeg_path()
    if ffmpeg_path is None:
        raise AudioDownloadError(
            "FFmpeg không tìm thấy.\n"
            "Vui lòng đặt ffmpeg.exe vào thư mục 'ffmpeg/' cạnh ứng dụng,\n"
            "hoặc cài ffmpeg vào system PATH."
        )

    # Prepare output directory
    base = get_base_dir()
    out_path = base / output_dir
    out_path.mkdir(exist_ok=True)

    # Track the downloaded filename
    downloaded_file = [None]
    video_title = ["Unknown"]

    def progress_hook(d):
        if d['status'] == 'downloading':
            if progress_callback:
                percent = d.get('_percent_str', '?')
                progress_callback(f"Đang tải audio... {percent}")
        elif d['status'] == 'finished':
            downloaded_file[0] = d.get('filename', None)
            if progress_callback:
                progress_callback("Đang convert audio sang MP3...")

    ffmpeg_dir = get_ffmpeg_dir()

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': str(out_path / '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'progress_hooks': [progress_hook],
        'quiet': True,
        'no_warnings': True,
        'noprogress': False,
    }

    # Set ffmpeg location if using local ffmpeg
    if ffmpeg_dir:
        ydl_opts['ffmpeg_location'] = ffmpeg_dir

    attempts = get_cookie_browser_attempts(cookie_browser)
    attempted_browsers = [browser for browser in attempts if browser]
    first_auth_error = None
    last_error = None

    for browser in attempts:
        current_opts = apply_cookie_browser_option(ydl_opts, browser)
        if browser and progress_callback:
            progress_callback(f"YouTube yêu cầu xác thực. Đang thử cookies từ {browser}...")

        try:
            with yt_dlp.YoutubeDL(current_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                video_title[0] = info.get('title', 'Unknown')

                # Find the MP3 file
                title = sanitize_filename(info.get('title', 'audio'))
                expected_mp3 = out_path / f"{title}.mp3"

                if expected_mp3.exists():
                    return str(expected_mp3), video_title[0]

                # Search for any recently created MP3 in output dir
                mp3_files = list(out_path.glob("*.mp3"))
                if mp3_files:
                    # Return the most recently modified one
                    latest = max(mp3_files, key=lambda f: f.stat().st_mtime)
                    return str(latest), video_title[0]

                raise AudioDownloadError(
                    "Tải audio thành công nhưng không tìm thấy file MP3.\n"
                    "Có thể FFmpeg chưa convert đúng."
                )

        except yt_dlp.utils.DownloadError as e:
            last_error = e
            if browser is None:
                first_auth_error = e
            should_retry = (
                browser is None
                and len(attempts) > 1
                and looks_like_youtube_auth_error(str(e))
            ) or (browser is not None and len(attempts) > 1)

            if should_retry:
                continue

            raise AudioDownloadError(
                f"Không thể tải audio từ video.\nChi tiết: {str(e)}"
            )
        except Exception as e:
            if isinstance(e, AudioDownloadError):
                raise
            if browser is not None and len(attempts) > 1:
                last_error = e
                continue
            raise AudioDownloadError(
                f"Lỗi không xác định khi tải audio.\nChi tiết: {str(e)}"
            )

    tried_text = ", ".join(attempted_browsers) if attempted_browsers else "không tìm thấy browser cookies trên máy"
    main_error = first_auth_error or last_error
    raise AudioDownloadError(
        "Không thể tải audio từ video.\n"
        f"Đã thử browser cookies: {tried_text}\n"
        f"Chi tiết chính: {str(main_error)}\n\n"
        "Gợi ý: mở YouTube và đăng nhập trên Edge/Chrome/Firefox, sau đó thử lại "
        "với Browser Cookies = Auto hoặc chọn đúng trình duyệt đang đăng nhập."
    )


def get_video_info(video_url: str, cookie_browser: str | None = "Auto") -> dict:
    """
    Get video metadata without downloading.

    Args:
        video_url: Full YouTube video URL.
        cookie_browser: Browser to read cookies from if YouTube requires login.

    Returns:
        Dict with 'title', 'duration', 'channel' keys.
    """
    try:
        import yt_dlp
    except ImportError:
        return {"title": "Unknown", "duration": 0, "channel": "Unknown"}

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }

    attempts = get_cookie_browser_attempts(cookie_browser)

    for browser in attempts:
        current_opts = apply_cookie_browser_option(ydl_opts, browser)
        try:
            with yt_dlp.YoutubeDL(current_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                return {
                    "title": info.get("title", "Unknown"),
                    "duration": info.get("duration", 0),
                    "channel": info.get("channel", "Unknown"),
                }
        except yt_dlp.utils.DownloadError as e:
            should_retry = (
                browser is None
                and len(attempts) > 1
                and looks_like_youtube_auth_error(str(e))
            ) or (browser is not None and len(attempts) > 1)
            if should_retry:
                continue
        except Exception:
            if browser is not None and len(attempts) > 1:
                continue

    return {"title": "Unknown", "duration": 0, "channel": "Unknown"}
