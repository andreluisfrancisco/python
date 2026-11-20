"""Escolhe os chunks que entram no prompt.

O chunk de métricas entra sempre. Os outros vêm do ranking do pgvector.
Sem embeddings, o schema inteiro entra: são nove textos curtos.
"""

from __future__ import annotations

from app.catalog.chunks import PINNED_CHUNKS


def select_chunk_names(
    available: list[str],
    ranked: list[str],
    *,
    top_k: int,
) -> list[str]:
    known = set(available)
    chosen: list[str] = [name for name in available if name in PINNED_CHUNKS and name in known]
    if not ranked:
        for name in available:
            if name not in chosen:
                chosen.append(name)
        return chosen

    added = 0
    for name in ranked:
        if name not in known or name in PINNED_CHUNKS or name in chosen:
            continue
        chosen.append(name)
        added += 1
        if added >= top_k:
            break
    return chosen
