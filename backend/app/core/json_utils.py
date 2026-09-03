"""Utilities for robust JSON extraction from LLM responses."""

from __future__ import annotations

import json
import re
from typing import Any


def clean_json_response(content: str) -> str:
    text = (content or "").strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    match = re.search(r"(\{.*\}|\[.*\])", text, flags=re.S)
    if match:
        text = match.group(1)
    return text.strip()


def loads_json_response(content: str) -> Any:
    cleaned = clean_json_response(content)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        repaired = (
            cleaned.replace("“", '"')
            .replace("”", '"')
            .replace("‘", "'")
            .replace("’", "'")
        )
        if repaired.count("{") > repaired.count("}"):
            repaired += "}" * (repaired.count("{") - repaired.count("}"))
        if repaired.count("[") > repaired.count("]"):
            repaired += "]" * (repaired.count("[") - repaired.count("]"))
        return json.loads(repaired)
