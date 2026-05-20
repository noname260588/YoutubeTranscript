"""
Video Service for YouTube Knowledge Clipper.
Downloads high-quality video from YouTube using yt-dlp and merges audio/video via ffmpeg.
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

class VideoDownloadError(Exception):
    """Raised when video download fails."""
    pass

def download_video(
    video_url: str,
    output_dir: str = "downloads",
    format_type: str = "Video (MP4)",
    quality: str = "Best",
    cookie_browser: str | None = "Auto",
    progress_callback=None
) -> tuple[str, str]:
    """
    Download video or audio from YouTube.

    Args:
        video_url: Full YouTube video URL.
        output_dir: Directory to save the file (relative to base dir).
        format_type: "Video (MP4)" or "Audio (M4A)".
        quality: "Best", "1080p", "720p", "480p".
        cookie_browser: Browser to read cookies from if YouTube requires login.
                        'Auto' tries anonymous first, then common browsers.
        progress_callback: Optional callback function for progress updates.
                          Called with (status_message: str).

    Returns:
        Tuple of (video_file_path, video_title).

    Raises:
        VideoDownloadError: If download or merging fails.
    """
    try:
        import yt_dlp
    except ImportError:
        raise VideoDownloadError(
            "yt-dlp chưa được cài đặt.\n"
            "Chạy: pip install yt-dlp"
        )

    # Check ffmpeg
    ffmpeg_path = get_ffmpeg_path()
    if ffmpeg_path is None:
        raise VideoDownloadError(
            "FFmpeg không tìm thấy.\n"
            "Vui lòng đặt ffmpeg.exe vào thư mục 'ffmpeg/' cạnh ứng dụng,\n"
            "hoặc cài ffmpeg vào system PATH."
        )

    # Prepare output directory
    base = get_base_dir()
    out_path = base / output_dir
    out_path.mkdir(exist_ok=True)

    downloaded_file = [None]
    video_title = ["Unknown"]

    def progress_hook(d):
        if d['status'] == 'downloading':
            if progress_callback:
                percent = d.get('_percent_str', '?')
                progress_callback(f"Đang tải video/audio... {percent}")
        elif d['status'] == 'finished':
            if progress_callback:
                progress_callback("Đang xử lý/merge file...")

    ffmpeg_dir = get_ffmpeg_dir()

    is_audio = (format_type == "Audio (M4A)")
    
    # Configure format string based on user choice
    if is_audio:
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'outtmpl': str(out_path / '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a',
            }],
            'progress_hooks': [progress_hook],
            'quiet': True,
            'no_warnings': True,
            'noprogress': False,
        }
    else:
        # Video quality map
        quality_map = {
            "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
            "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
            "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]/best",
            "Best": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        }
        fmt_str = quality_map.get(quality, quality_map["Best"])
        
        ydl_opts = {
            'format': fmt_str,
            'outtmpl': str(out_path / '%(title)s.%(ext)s'),
            'merge_output_format': 'mp4',
            'progress_hooks': [progress_hook],
            'quiet': True,
            'no_warnings': True,
            'noprogress': False,
        }

    if ffmpeg_dir:
        ydl_opts['ffmpeg_location'] = ffmpeg_dir

    attempts = get_cookie_browser_attempts(cookie_browser)
    last_error = None

    for browser in attempts:
        current_opts = apply_cookie_browser_option(ydl_opts, browser)
        if browser and progress_callback:
            progress_callback(f"YouTube yêu cầu xác thực. Đang thử cookies từ {browser}...")

        try:
            with yt_dlp.YoutubeDL(current_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                video_title[0] = info.get('title', 'Unknown')
                
                # Find the merged/downloaded file
                title = sanitize_filename(info.get('title', 'download'))
                ext = "m4a" if is_audio else "mp4"
                expected_file = out_path / f"{title}.{ext}"
                
                if expected_file.exists():
                    return str(expected_file), video_title[0]
                    
                # If title sanitization in yt-dlp is slightly different, check for latest file
                files = list(out_path.glob(f"*.{ext}"))
                if files:
                    latest = max(files, key=lambda f: f.stat().st_mtime)
                    return str(latest), video_title[0]

                raise VideoDownloadError(f"Tải thành công nhưng không tìm thấy file {ext.upper()}.")

        except yt_dlp.utils.DownloadError as e:
            last_error = e
            should_retry = (
                browser is None
                and len(attempts) > 1
                and looks_like_youtube_auth_error(str(e))
            ) or (browser is not None and len(attempts) > 1)

            if should_retry:
                continue

            raise VideoDownloadError(f"Không thể tải video.\nChi tiết: {str(e)}")
        except Exception as e:
            if isinstance(e, VideoDownloadError):
                raise
            if browser is not None and len(attempts) > 1:
                last_error = e
                continue
            raise VideoDownloadError(f"Lỗi không xác định khi tải video.\nChi tiết: {str(e)}")

    raise VideoDownloadError(
        "Không thể tải video dù đã thử browser cookies.\n"
        f"Chi tiết cuối: {str(last_error)}\n\n"
        "Gợi ý: mở YouTube và đăng nhập trên Edge/Chrome/Firefox, sau đó thử lại "
        "với Browser Cookies = Auto hoặc chọn đúng trình duyệt đang đăng nhập."
    )
