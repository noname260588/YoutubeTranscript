"""
Export Service for YouTube Knowledge Clipper.
Handles exporting transcripts to TXT, Markdown, and SRT formats.
"""

import re
from pathlib import Path
from services.youtube_metadata_service import (
    clean_youtube_description,
    extract_chapters_from_description,
)
from utils import format_timestamp, format_srt_timestamp, get_current_date

MARKDOWN_MODES = ["Raw Transcript", "Clean Transcript", "Learning Notes"]


def export_txt(segments: list[dict], output_path: str, metadata: dict = None) -> str:
    """
    Export transcript segments to a plain text file.

    Format:
        YouTube Transcript
        Source: <url>
        Language: <language>

        [00:00:01] Content...
        [00:00:05] Content...

    Args:
        segments: List of transcript segments with 'start' and 'text' keys.
        output_path: Full path to the output .txt file.
        metadata: Optional dict with 'url', 'language', 'title' keys.

    Returns:
        The output file path.
    """
    metadata = metadata or {}
    lines = []

    lines.append("YouTube Transcript")
    lines.append(f"Source: {metadata.get('url', 'N/A')}")
    lines.append(f"Language: {metadata.get('language', 'N/A')}")
    lines.append("")

    for seg in segments:
        start = seg.get("start", 0)
        text = seg.get("text", "")
        timestamp = format_timestamp(start)
        lines.append(f"{timestamp} {text}")

    content = "\n".join(lines)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")

    return str(output)


def _yaml_quote(value: str) -> str:
    value = "" if value is None else str(value)
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _strip_fillers(text: str) -> str:
    filler_patterns = [
        r"\b(um+|uh+|erm+|hmm+|you know)\b",
        r"(?<!\w)(ừ+|ừm+|ờ+|à+|á+|ơ+|ờm+)(?!\w)",
    ]
    cleaned = text
    for pattern in filler_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    return _normalize_spaces(cleaned)


def _dedupe_repeated_words(text: str) -> str:
    return re.sub(r"\b(\w+)(\s+\1\b)+", r"\1", text, flags=re.IGNORECASE)


def _dedupe_repeated_lines(lines: list[str]) -> list[str]:
    result = []
    previous = ""
    for line in lines:
        normalized = line.lower().strip()
        if not normalized:
            if result and result[-1] != "":
                result.append("")
            previous = ""
            continue
        if normalized != previous:
            result.append(line)
        previous = normalized
    return result


def _basic_punctuation(text: str) -> str:
    text = _normalize_spaces(text)
    if not text:
        return ""
    text = text[0].upper() + text[1:] if len(text) > 1 else text.upper()
    if text[-1] not in ".!?;:":
        text += "."
    return text


def _clean_segment_text(text: str) -> str:
    text = _strip_fillers(text)
    text = _dedupe_repeated_words(text)
    return _basic_punctuation(text)


def _clean_transcript_paragraphs(segments: list[dict]) -> list[tuple[float, str]]:
    paragraphs = []
    current_start = None
    current_parts = []
    last_start = 0.0
    previous_text = ""

    for seg in segments:
        start = float(seg.get("start", 0) or 0)
        text = _clean_segment_text(seg.get("text", ""))
        if not text:
            continue
        normalized_text = _normalize_spaces(text).lower()
        if normalized_text == previous_text:
            continue
        previous_text = normalized_text

        current_text = " ".join(current_parts)
        is_short_segment = len(text) < 80
        should_break = (
            current_parts
            and start - last_start >= 45
            and not is_short_segment
        ) or (
            current_parts
            and len(current_text) + len(text) > 520
        )

        if should_break and current_parts:
            paragraphs.append((current_start or 0.0, " ".join(current_parts)))
            current_parts = []
            current_start = start
        elif current_start is None:
            current_start = start

        current_parts.append(text)
        last_start = start

    if current_parts:
        paragraphs.append((current_start or 0.0, " ".join(current_parts)))

    return paragraphs


def _format_raw_transcript(segments: list[dict], include_timestamps: bool = True) -> list[str]:
    lines = []
    previous = ""
    for seg in segments:
        start = seg.get("start", 0)
        text = _normalize_spaces(seg.get("text", ""))
        if not text:
            continue
        line = f"{format_timestamp(start)} {text}" if include_timestamps else text
        normalized = text.lower()
        if normalized != previous:
            lines.append(line)
        previous = normalized
    return lines


def _format_clean_transcript(segments: list[dict], include_timestamps: bool = True) -> list[str]:
    lines = []
    for start, paragraph in _clean_transcript_paragraphs(segments):
        line = f"{format_timestamp(start)} {paragraph}" if include_timestamps else paragraph
        lines.append(line)
        lines.append("")
    while lines and lines[-1] == "":
        lines.pop()
    return _dedupe_repeated_lines(lines)


def format_clean_transcript_text(segments: list[dict], include_timestamps: bool = False) -> str:
    """Return clean transcript text for display, prompts, or Markdown export."""
    return "\n".join(_format_clean_transcript(segments, include_timestamps=include_timestamps))


def _format_duration(seconds: int | float | str) -> str:
    try:
        total = int(float(seconds or 0))
    except (TypeError, ValueError):
        return ""
    if total <= 0:
        return ""
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _format_upload_date(value: str) -> str:
    value = str(value or "").strip()
    if re.fullmatch(r"\d{8}", value):
        return f"{value[:4]}-{value[4:6]}-{value[6:8]}"
    return value


def _append_video_info(lines: list[str], metadata: dict) -> None:
    info_items = [
        ("Source", metadata.get("webpage_url") or metadata.get("url")),
        ("Channel", metadata.get("channel")),
        ("Uploader", metadata.get("uploader")),
        ("Upload date", _format_upload_date(metadata.get("upload_date", ""))),
        ("Duration", _format_duration(metadata.get("duration", 0))),
        ("Thumbnail", metadata.get("thumbnail")),
    ]

    tags = metadata.get("tags") or []
    categories = metadata.get("categories") or []
    if tags:
        info_items.append(("Tags", ", ".join(str(tag) for tag in tags[:20])))
    if categories:
        info_items.append(("Categories", ", ".join(str(category) for category in categories)))

    rendered = [(label, value) for label, value in info_items if value]
    if not rendered:
        return

    lines.append("## Video Info")
    lines.append("")
    for label, value in rendered:
        lines.append(f"- **{label}:** {value}")
    lines.append("")


def _append_description(lines: list[str], metadata: dict) -> None:
    description = metadata.get("description", "")
    if not description:
        return
    if metadata.get("clean_description", True):
        description = metadata.get("clean_description_text") or clean_youtube_description(description)

    if not description:
        return

    lines.append("## Description")
    lines.append("")
    lines.extend(description.splitlines())
    lines.append("")


def _append_chapters(lines: list[str], metadata: dict) -> None:
    chapters = metadata.get("chapters")
    if chapters is None:
        chapters = extract_chapters_from_description(metadata.get("description", ""))
    if not chapters:
        return

    lines.append("## Chapters")
    lines.append("")
    for chapter in chapters:
        if isinstance(chapter, dict):
            timestamp = chapter.get("timestamp", "")
            title = chapter.get("title", "")
            seconds = chapter.get("seconds")
            if not timestamp and seconds is not None:
                timestamp = format_timestamp(seconds).strip("[]")
            lines.append(f"- {timestamp} {title}".strip())
        else:
            lines.append(f"- {chapter}")
    lines.append("")


def export_markdown(segments: list[dict], output_path: str, metadata: dict = None) -> str:
    """
    Export transcript segments to an Obsidian-friendly Markdown file.

    Args:
        segments: List of transcript segments with 'start' and 'text' keys.
        output_path: Full path to the output .md file.
        metadata: Optional dict with export settings and video metadata.

    Returns:
        The output file path.
    """
    metadata = metadata or {}
    lines = []

    title = metadata.get("title", "YouTube Transcript")
    mode = metadata.get("markdown_mode", "Clean Transcript")
    if mode not in MARKDOWN_MODES:
        mode = "Clean Transcript"
    include_timestamps = bool(metadata.get("include_timestamps", True))

    lines.append("---")
    lines.append("type: youtube-note")
    lines.append(f"title: {_yaml_quote(title)}")
    lines.append(f"source: {_yaml_quote(metadata.get('url', ''))}")
    lines.append(f"language: {_yaml_quote(metadata.get('language', 'N/A'))}")
    lines.append(f"created: {_yaml_quote(metadata.get('date', get_current_date()))}")
    lines.append(f"mode: {_yaml_quote(mode)}")
    lines.append("tags:")
    lines.append("  - youtube")
    lines.append("  - transcript")
    lines.append("---")
    lines.append("")
    lines.append(f"# {title}")
    lines.append("")

    if metadata.get("include_metadata", False):
        _append_video_info(lines, metadata)

    if metadata.get("include_video_description", False):
        _append_description(lines, metadata)

    if metadata.get("extract_chapters", False):
        _append_chapters(lines, metadata)

    lines.append("## Summary")
    lines.append("")
    if mode == "Learning Notes":
        lines.append("")

    lines.append("## Key Ideas")
    lines.append("")
    if mode == "Learning Notes":
        lines.append("")

    lines.append("## Quotes")
    lines.append("")
    if mode == "Learning Notes":
        lines.append("")

    lines.append("## Transcript")
    lines.append("")
    if mode == "Clean Transcript":
        lines.extend(_format_clean_transcript(segments, include_timestamps=include_timestamps))
    elif mode == "Learning Notes":
        lines.extend(_format_clean_transcript(segments, include_timestamps=include_timestamps))
    else:
        lines.extend(_format_raw_transcript(segments, include_timestamps=include_timestamps))
    lines.append("")
    lines.append("## My Notes")
    lines.append("")
    if mode == "Learning Notes":
        lines.append("")
    lines.append("")

    content = "\n".join(lines)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")

    return str(output)


def export_srt(segments: list[dict], output_path: str, metadata: dict = None) -> str:
    """
    Export transcript segments to SRT subtitle format.

    Format:
        1
        00:00:01,000 --> 00:00:05,000
        Content...

        2
        00:00:05,000 --> 00:00:09,000
        Next content...

    Args:
        segments: List of transcript segments with 'start' and 'text' keys.
                  Must also have 'end' or 'duration' key.
        output_path: Full path to the output .srt file.
        metadata: Optional metadata (not used in SRT but kept for API consistency).

    Returns:
        The output file path.
    """
    lines = []

    for i, seg in enumerate(segments, 1):
        start = seg.get("start", 0)
        text = seg.get("text", "")

        # Calculate end time from 'end' or 'start + duration'
        if "end" in seg:
            end = seg["end"]
        elif "duration" in seg:
            end = start + seg["duration"]
        else:
            # Default: next segment start or +3 seconds
            end = start + 3.0

        start_ts = format_srt_timestamp(start)
        end_ts = format_srt_timestamp(end)

        lines.append(str(i))
        lines.append(f"{start_ts} --> {end_ts}")
        lines.append(text)
        lines.append("")  # Blank line between entries

    content = "\n".join(lines)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")

    return str(output)


def format_transcript_text(segments: list[dict], include_timestamps: bool = True) -> str:
    """
    Format transcript segments as a displayable text string.

    Args:
        segments: List of transcript segments.
        include_timestamps: Whether to include timestamps.

    Returns:
        Formatted transcript text.
    """
    lines = []
    for seg in segments:
        text = seg.get("text", "")
        if include_timestamps:
            start = seg.get("start", 0)
            timestamp = format_timestamp(start)
            lines.append(f"{timestamp} {text}")
        else:
            lines.append(text)

    return "\n".join(lines)
