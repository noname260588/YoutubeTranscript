"""
Audio Service for YouTube Knowledge Clipper.
Downloads audio from YouTube videos using yt-dlp and converts to MP3 via ffmpeg.
"""

import os
from pathlib import Path
from utils import get_base_dir, sanitize_filename, get_ffmpeg_path, get_ffmpeg_dir


class AudioDownloadError(Exception):
    """Raised when audio download fails."""
    pass


def download_audio(
    video_url: str,
    output_dir: str = "downloads",
    progress_callback=None
) -> tuple[str, str]:
    """
    Download audio from a YouTube video and convert to MP3.

    Args:
        video_url: Full YouTube video URL.
        output_dir: Directory to save the audio file (relative to base dir).
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

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
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
        raise AudioDownloadError(
            f"Không thể tải audio từ video.\nChi tiết: {str(e)}"
        )
    except Exception as e:
        if isinstance(e, AudioDownloadError):
            raise
        raise AudioDownloadError(
            f"Lỗi không xác định khi tải audio.\nChi tiết: {str(e)}"
        )


def get_video_info(video_url: str) -> dict:
    """
    Get video metadata without downloading.

    Args:
        video_url: Full YouTube video URL.

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

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            return {
                "title": info.get("title", "Unknown"),
                "duration": info.get("duration", 0),
                "channel": info.get("channel", "Unknown"),
            }
    except Exception:
        return {"title": "Unknown", "duration": 0, "channel": "Unknown"}
