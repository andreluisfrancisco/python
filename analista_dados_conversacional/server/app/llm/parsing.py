"""Leitura do JSON que o modelo devolve na etapa de Text-to-SQL."""

from __future__ import annotations

import json
import re
from typing import Any


class ModelFormatError(ValueError):
    """A resposta do modelo não veio no JSON combinado."""


def parse_model_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, count=1, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ModelFormatError("O modelo não devolveu um objeto JSON.")
    try:
        payload = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ModelFormatError("O JSON do modelo está inválido.") from exc
    if not isinstance(payload, dict):
        raise ModelFormatError("O modelo não devolveu um objeto JSON.")
    return payload
