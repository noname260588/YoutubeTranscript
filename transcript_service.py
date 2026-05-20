"""
Transcript Service for YouTube Knowledge Clipper.
Fetches available transcripts/captions from YouTube videos using youtube-transcript-api.
Compatible with youtube-transcript-api v1.2.4+ (instance-based API).
"""

from youtube_transcript_api import YouTubeTranscriptApi
from utils import extract_video_id


class TranscriptNotFoundError(Exception):
    """Raised when no transcript is available for a YouTube video."""
    pass


def get_youtube_transcript(video_url: str, language: str = "auto") -> list[dict]:
    """
    Fetch transcript from a YouTube video.

    Args:
        video_url: Full YouTube video URL.
        language: Language code ('auto', 'vi', 'en', 'ja', 'zh').
                  'auto' will try vi → en → any available.

    Returns:
        List of transcript segments:
        [{"start": 0.0, "duration": 3.2, "text": "Hello world"}, ...]

    Raises:
        TranscriptNotFoundError: If no transcript is available.
        ValueError: If the URL is invalid.
    """
    video_id = extract_video_id(video_url)

    # youtube-transcript-api v1.2+ uses instance-based API
    ytt_api = YouTubeTranscriptApi()

    try:
        transcript_list = ytt_api.list(video_id)
    except Exception as e:
        raise TranscriptNotFoundError(
            f"Không thể truy cập transcript cho video này.\nChi tiết: {str(e)}"
        )

    transcript = None

    if language == "auto":
        # Priority: vi → en → any manual → any generated
        priority_languages = ['vi', 'en']

        # Try manual transcripts first with priority languages
        for lang in priority_languages:
            try:
                transcript = transcript_list.find_transcript([lang])
                break
            except Exception:
                continue

        # Try any manual transcript
        if transcript is None:
            try:
                for t in transcript_list:
                    if not t.is_generated:
                        transcript = t
                        break
            except Exception:
                pass

        # Try any auto-generated transcript
        if transcript is None:
            try:
                for t in transcript_list:
                    if t.is_generated:
                        transcript = t
                        break
            except Exception:
                pass

        # Try finding any transcript at all
        if transcript is None:
            try:
                for t in transcript_list:
                    transcript = t
                    break
            except Exception:
                pass
    else:
        # Try to find transcript in the specified language
        try:
            transcript = transcript_list.find_transcript([language])
        except Exception:
            # Try generated transcript in that language
            try:
                transcript = transcript_list.find_generated_transcript([language])
            except Exception:
                pass

    if transcript is None:
        raise TranscriptNotFoundError(
            f"Không tìm thấy transcript cho video này"
            + (f" (ngôn ngữ: {language})" if language != "auto" else "")
            + ".\nVideo có thể không có caption/phụ đề."
        )

    try:
        fetched = transcript.fetch()
        # Convert FetchedTranscriptSnippet objects to dicts
        # v1.2+ returns FetchedTranscript (iterable of FetchedTranscriptSnippet dataclass)
        segments = []
        for snippet in fetched:
            segments.append({
                "start": float(snippet.start),
                "duration": float(snippet.duration),
                "text": str(snippet.text).strip()
            })
        return segments
    except Exception as e:
        raise TranscriptNotFoundError(
            f"Lỗi khi tải transcript.\nChi tiết: {str(e)}"
        )
