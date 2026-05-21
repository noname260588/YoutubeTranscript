# Changelog

## v1.0.0 - 2026-05-21

### Added
- Persistent local settings in `settings.json`.
- Remembered export folder, transcript mode, language, Whisper model, and timestamp toggle.
- Obsidian direct Markdown export with vault path and default subfolder settings.
- Default Markdown filename pattern: `{date_compact}_{title}` for names like `20260521_video-title.md`.
- Markdown export modes: Raw Transcript, Clean Transcript, and Learning Notes.
- Rule-based clean transcript formatting for Markdown export.
- Obsidian-ready Markdown frontmatter and note sections.
- Sample exported Markdown note under `samples/`.

### Changed
- Markdown export now uses v1.0 frontmatter fields: `type`, `title`, `source`, `language`, `created`, `mode`, and `tags`.
- Main window layout is more compact while keeping transcript actions visible.

### Verified
- `python app.py` launches successfully.
- TXT, Markdown, and SRT export paths remain available.
- Existing YouTube transcript, Whisper fallback, yt-dlp download, global hotkey, and `build.bat` workflows are preserved.
