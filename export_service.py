"""
Export Service for YouTube Knowledge Clipper.
Handles exporting transcripts to TXT, Markdown, and SRT formats.
"""

from pathlib import Path
from utils import format_timestamp, format_srt_timestamp, get_current_date


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


def export_markdown(segments: list[dict], output_path: str, metadata: dict = None) -> str:
    """
    Export transcript segments to an Obsidian-friendly Markdown file.

    Format:
        # <video_title>

        Source: <url>
        Date: <date>
        Language: <language>
        Mode: <mode>

        ## Transcript

        [00:00:01] Content...
        [00:00:05] Content...

    Args:
        segments: List of transcript segments with 'start' and 'text' keys.
        output_path: Full path to the output .md file.
        metadata: Optional dict with 'url', 'language', 'title', 'mode' keys.

    Returns:
        The output file path.
    """
    metadata = metadata or {}
    lines = []

    title = metadata.get("title", "YouTube Transcript")
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"> Source: {metadata.get('url', 'N/A')}")
    lines.append(f"> Date: {metadata.get('date', get_current_date())}")
    lines.append(f"> Language: {metadata.get('language', 'N/A')}")
    lines.append(f"> Mode: {metadata.get('mode', 'N/A')}")
    lines.append("")
    lines.append("## Transcript")
    lines.append("")

    for seg in segments:
        start = seg.get("start", 0)
        text = seg.get("text", "")
        timestamp = format_timestamp(start)
        lines.append(f"{timestamp} {text}")

    lines.append("")
    lines.append("## My Notes")
    lines.append("")
    lines.append("<!-- Add your notes here -->")
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
