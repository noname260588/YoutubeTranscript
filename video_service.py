"""
Video Service for YouTube Knowledge Clipper.
Downloads high-quality video from YouTube using yt-dlp and merges audio/video via ffmpeg.
"""

import os
from pathlib import Path
from utils import get_base_dir, sanitize_filename, get_ffmpeg_path, get_ffmpeg_dir

class VideoDownloadError(Exception):
    """Raised when video download fails."""
    pass

def download_video(
    video_url: str,
    output_dir: str = "downloads",
    progress_callback=None
) -> tuple[str, str]:
    """
    Download the best video and audio streams and merge them into an MP4 file.

    Args:
        video_url: Full YouTube video URL.
        output_dir: Directory to save the video file (relative to base dir).
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

    # We want bestvideo + bestaudio, merged into mp4
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': str(out_path / '%(title)s.%(ext)s'),
        'merge_output_format': 'mp4',
        'progress_hooks': [progress_hook],
        'quiet': True,
        'no_warnings': True,
        'noprogress': False,
    }

    if ffmpeg_dir:
        ydl_opts['ffmpeg_location'] = ffmpeg_dir

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            video_title[0] = info.get('title', 'Unknown')
            
            # Find the merged file
            title = sanitize_filename(info.get('title', 'video'))
            expected_mp4 = out_path / f"{title}.mp4"
            
            if expected_mp4.exists():
                return str(expected_mp4), video_title[0]
                
            # If title sanitization in yt-dlp is slightly different, check for latest mp4
            mp4_files = list(out_path.glob("*.mp4"))
            if mp4_files:
                latest = max(mp4_files, key=lambda f: f.stat().st_mtime)
                return str(latest), video_title[0]

            raise VideoDownloadError("Tải video thành công nhưng không tìm thấy file MP4.")

    except yt_dlp.utils.DownloadError as e:
        raise VideoDownloadError(f"Không thể tải video.\nChi tiết: {str(e)}")
    except Exception as e:
        if isinstance(e, VideoDownloadError):
            raise
        raise VideoDownloadError(f"Lỗi không xác định khi tải video.\nChi tiết: {str(e)}")
