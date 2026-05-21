"""
Persistent app settings for YouTube Knowledge Clipper.
Stores lightweight user preferences in a JSON file next to the app.
"""

import json
from pathlib import Path

from utils import get_base_dir


DEFAULT_SETTINGS = {
    "obsidian_vault_path": "",
    "obsidian_subfolder": "Resources/YouTube",
    "filename_pattern": "{date_compact}_{title}",
    "markdown_mode": "Clean Transcript",
    "auto_open_after_export": False,
    "last_export_dir": "",
    "selected_language": "Auto",
    "selected_mode": "Auto",
    "selected_whisper_model": "small",
    "show_timestamps": True,
}


def get_settings_path() -> Path:
    return get_base_dir() / "settings.json"


def load_settings() -> dict:
    settings = dict(DEFAULT_SETTINGS)
    path = get_settings_path()
    if not path.exists():
        return settings

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return settings

    if isinstance(data, dict):
        for key in DEFAULT_SETTINGS:
            if key in data:
                settings[key] = data[key]
    return settings


def save_settings(settings: dict) -> dict:
    merged = dict(DEFAULT_SETTINGS)
    merged.update({key: settings.get(key, value) for key, value in DEFAULT_SETTINGS.items()})

    path = get_settings_path()
    path.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return merged
