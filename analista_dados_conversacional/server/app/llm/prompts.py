"""Carrega os prompts versionados em server/prompts/."""

from __future__ import annotations

import re

from app.config import SERVER_ROOT

PROMPTS = SERVER_ROOT / "prompts"
_PLACEHOLDER = re.compile(r"<<[A-Z_]+>>")


def render(filename: str, **values: str) -> str:
    text = (PROMPTS / filename).read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace(f"<<{key}>>", value)
    missing = _PLACEHOLDER.findall(text)
    if missing:
        raise RuntimeError(f"Placeholders sem valor em {filename}: {missing}")
    return text
