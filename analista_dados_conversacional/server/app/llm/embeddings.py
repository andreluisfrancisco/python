"""Embeddings do Grok para o catálogo do schema.

O prefixo passage/query segue a recomendação da API de embeddings da xAI.
"""

from __future__ import annotations

import httpx

from app.config import get_settings
from app.llm.grok import LlmNotConfigured


def embed_texts(texts: list[str], *, kind: str) -> list[list[float]]:
    if kind not in {"query", "passage"}:
        raise ValueError("kind precisa ser query ou passage.")
    settings = get_settings()
    if not settings.xai_api_key.strip():
        raise LlmNotConfigured("Defina XAI_API_KEY no arquivo .env.")

    prefixed = [f"{kind}: {text}" for text in texts]
    response = httpx.post(
        f"{settings.xai_base_url.rstrip('/')}/embeddings",
        headers={"Authorization": f"Bearer {settings.xai_api_key}"},
        json={
            "model": settings.embedding_model,
            "input": prefixed,
            "dimensions": settings.embedding_dimensions,
            "encoding_format": "float",
        },
        timeout=60,
    )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(f"A API de embeddings respondeu {exc.response.status_code}.") from exc

    data = sorted(response.json()["data"], key=lambda item: item["index"])
    vectors = [item["embedding"] for item in data]
    expected = settings.embedding_dimensions
    for vector in vectors:
        if len(vector) != expected:
            raise RuntimeError(f"O embedding veio com {len(vector)} dimensões; o banco espera {expected}.")
    return vectors
