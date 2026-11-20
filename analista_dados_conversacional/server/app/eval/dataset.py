"""Lê o conjunto de perguntas versionado em dataset.json."""

from __future__ import annotations

import json
from pathlib import Path

DATASET_PATH = Path(__file__).with_name("dataset.json")


def load_dataset() -> list[dict]:
    payload = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    return payload["perguntas"]
