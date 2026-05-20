"""
Whisper Speech-to-Text Service for YouTube Knowledge Clipper.
Uses faster-whisper for offline audio transcription.
"""

from pathlib import Path
from utils import get_base_dir


class WhisperTranscriptionError(Exception):
    """Raised when whisper transcription fails."""
    pass


# Cache loaded models to avoid reloading
_model_cache: dict = {}

# Local models directory (next to app.py)
MODELS_DIR = get_base_dir() / "models"


def transcribe_audio(
    audio_path: str,
    model_size: str = "small",
    language: str | None = None,
    progress_callback=None
) -> list[dict]:
    """
    Transcribe audio file using faster-whisper.

    Models are stored in the local 'models/' directory next to app.py,
    making the app fully portable.

    Args:
        audio_path: Path to the audio file (MP3, WAV, etc.).
        model_size: Whisper model size ('tiny', 'base', 'small', 'medium').
        language: Language code (e.g., 'vi', 'en') or None for auto-detect.
        progress_callback: Optional callback for status updates.
                          Called with (status_message: str).

    Returns:
        List of transcript segments:
        [{"start": 0.0, "end": 3.2, "text": "Xin chào"}, ...]

    Raises:
        WhisperTranscriptionError: If transcription fails.
    """
    # Validate audio file
    audio = Path(audio_path)
    if not audio.exists():
        raise WhisperTranscriptionError(
            f"File audio không tồn tại: {audio_path}"
        )

    # Import faster_whisper
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise WhisperTranscriptionError(
            "faster-whisper chưa được cài đặt.\n"
            "Chạy: pip install faster-whisper"
        )

    # Validate model size
    valid_models = ['tiny', 'base', 'small', 'medium']
    if model_size not in valid_models:
        model_size = 'small'

    # Ensure models directory exists
    MODELS_DIR.mkdir(exist_ok=True)

    # Load or get cached model
    if progress_callback:
        progress_callback(f"Đang tải Whisper model '{model_size}'... (lần đầu có thể mất vài phút)")

    try:
        if model_size not in _model_cache:
            model = WhisperModel(
                model_size,
                device="cpu",
                compute_type="int8",
                download_root=str(MODELS_DIR)
            )
            _model_cache[model_size] = model
        else:
            model = _model_cache[model_size]
    except Exception as e:
        raise WhisperTranscriptionError(
            f"Không thể tải Whisper model '{model_size}'.\n"
            f"Lần đầu chạy cần internet để download model.\n"
            f"Chi tiết: {str(e)}"
        )

    # Transcribe
    if progress_callback:
        progress_callback("Đang chuyển audio thành text... (có thể mất vài phút)")

    try:
        # Set language to None for auto-detect if "auto"
        transcribe_lang = None if language in (None, "auto", "") else language

        segments_gen, info = model.transcribe(
            str(audio_path),
            language=transcribe_lang,
            beam_size=5,
            vad_filter=True
        )

        if progress_callback:
            detected_lang = info.language if info else "unknown"
            progress_callback(
                f"Ngôn ngữ phát hiện: {detected_lang} — Đang xử lý segments..."
            )

        # Collect segments
        segments = []
        for i, segment in enumerate(segments_gen):
            segments.append({
                "start": round(segment.start, 3),
                "end": round(segment.end, 3),
                "text": segment.text.strip()
            })

            # Progress update every 50 segments
            if progress_callback and (i + 1) % 50 == 0:
                progress_callback(f"Đã xử lý {i + 1} segments...")

        if not segments:
            raise WhisperTranscriptionError(
                "Whisper không phát hiện được lời nói trong audio.\n"
                "Audio có thể chỉ chứa nhạc hoặc quá ngắn."
            )

        if progress_callback:
            progress_callback(f"Hoàn tất! Tổng cộng {len(segments)} segments.")

        return segments

    except WhisperTranscriptionError:
        raise
    except Exception as e:
        raise WhisperTranscriptionError(
            f"Lỗi khi chuyển audio thành text.\nChi tiết: {str(e)}"
        )


def get_available_models() -> list[str]:
    """Return list of available Whisper model sizes."""
    return ['tiny', 'base', 'small', 'medium']
