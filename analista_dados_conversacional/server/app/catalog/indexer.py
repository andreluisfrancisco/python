"""Grava e recupera o catálogo do schema no pgvector."""

from __future__ import annotations

import logging

from psycopg import Connection

from app.catalog.chunks import CHUNKS
from app.catalog.retrieval import select_chunk_names
from app.config import get_settings
from app.llm.embeddings import embed_texts
from app.llm.grok import LlmNotConfigured

logger = logging.getLogger(__name__)


def upsert_chunks(conn: Connection) -> None:
    for chunk in CHUNKS:
        conn.execute(
            """
            INSERT INTO analista.schema_chunks (object_name, chunk_text)
            VALUES (%s, %s)
            ON CONFLICT (object_name) DO UPDATE
            SET chunk_text = EXCLUDED.chunk_text,
                embedding = CASE
                    WHEN analista.schema_chunks.chunk_text IS DISTINCT FROM EXCLUDED.chunk_text THEN NULL
                    ELSE analista.schema_chunks.embedding
                END
            """,
            (chunk.object_name, chunk.text),
        )


def index_missing_embeddings(conn: Connection) -> int:
    rows = conn.execute(
        "SELECT object_name, chunk_text FROM analista.schema_chunks WHERE embedding IS NULL ORDER BY id"
    ).fetchall()
    if not rows:
        return 0
    try:
        vectors = embed_texts([row["chunk_text"] for row in rows], kind="passage")
    except LlmNotConfigured:
        logger.info("Catálogo sem embeddings: XAI_API_KEY não definida.")
        return 0
    for row, vector in zip(rows, vectors, strict=True):
        conn.execute(
            "UPDATE analista.schema_chunks SET embedding = %s WHERE object_name = %s",
            (vector, row["object_name"]),
        )
    return len(rows)


def schema_context(conn: Connection, question: str) -> str:
    rows = conn.execute(
        """
        SELECT object_name, chunk_text, (embedding IS NOT NULL) AS ready
        FROM analista.schema_chunks
        ORDER BY id
        """
    ).fetchall()
    if not rows:
        return "\n\n".join(chunk.text for chunk in CHUNKS)

    available = [row["object_name"] for row in rows]
    by_name = {row["object_name"]: row["chunk_text"] for row in rows}
    settings = get_settings()
    ranked: list[str] = []
    if all(row["ready"] for row in rows):
        try:
            vector = embed_texts([question], kind="query")[0]
            found = conn.execute(
                """
                SELECT object_name
                FROM analista.schema_chunks
                ORDER BY embedding <=> %s
                LIMIT %s
                """,
                (vector, settings.catalog_top_k + len(available)),
            ).fetchall()
            ranked = [row["object_name"] for row in found]
        except (LlmNotConfigured, RuntimeError):
            logger.info("Busca vetorial indisponível; o prompt recebe o catálogo inteiro.")
            ranked = []

    names = select_chunk_names(available, ranked, top_k=settings.catalog_top_k)
    return "\n\n".join(by_name[name] for name in names)
