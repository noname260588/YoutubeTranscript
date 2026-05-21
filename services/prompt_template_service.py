"""
Prompt template loading and rendering.
This module is fully offline and does not call any AI API.
"""

import json
from pathlib import Path

from utils import get_asset_path, get_base_dir


TEMPLATE_FILENAME = "prompt_templates.json"
TRANSCRIPT_PLACEHOLDER = "{TRANSCRIPT}"


class SafeFormatDict(dict):
    """Keep unknown placeholders visible instead of raising KeyError."""

    def __missing__(self, key):
        return "{" + key + "}"


def _template_path() -> Path:
    bundled = get_asset_path(TEMPLATE_FILENAME)
    if bundled.exists():
        return bundled
    return get_base_dir() / TEMPLATE_FILENAME


def _load_template_list() -> list[dict]:
    path = _template_path()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("prompt_templates.json must contain a list")

    templates = []
    for item in data:
        if not isinstance(item, dict):
            continue
        template_id = str(item.get("id", "")).strip()
        name = str(item.get("name", "")).strip()
        template = str(item.get("template", "")).strip()
        if not template_id or not name or not template:
            continue
        templates.append({
            "id": template_id,
            "name": name,
            "description": str(item.get("description", "")).strip(),
            "template": template,
        })

    if not templates:
        raise ValueError("No valid prompt templates found")
    return templates


def list_templates() -> list[dict]:
    """Return available prompt template metadata."""
    return [
        {
            "id": template["id"],
            "name": template["name"],
            "description": template["description"],
        }
        for template in _load_template_list()
    ]


def get_template(template_id: str) -> dict:
    """Return a full template by id."""
    for template in _load_template_list():
        if template["id"] == template_id:
            return template
    raise KeyError(f"Prompt template not found: {template_id}")


def render_prompt(template_id: str, context: dict, include_transcript: bool = True) -> str:
    """
    Render a prompt template with context variables.
    When include_transcript is False, the {TRANSCRIPT} placeholder remains.
    """
    template = get_template(template_id)["template"]
    values = SafeFormatDict({
        "VIDEO_TITLE": context.get("VIDEO_TITLE", ""),
        "VIDEO_URL": context.get("VIDEO_URL", ""),
        "CHANNEL_NAME": context.get("CHANNEL_NAME", ""),
        "DESCRIPTION": context.get("DESCRIPTION", ""),
        "CHAPTERS": context.get("CHAPTERS", ""),
        "TRANSCRIPT": context.get("TRANSCRIPT", "") if include_transcript else TRANSCRIPT_PLACEHOLDER,
    })
    return template.format_map(values).strip()
