"""Cria tabelas, carga e usuário de demonstração no Postgres local."""

from __future__ import annotations

import sys
from pathlib import Path

import psycopg
import sqlparse
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.auth.passwords import hash_password
from app.catalog.indexer import index_missing_embeddings, upsert_chunks
from app.config import get_settings


def main() -> None:
    settings = get_settings()
    migration_url = settings.migration_database_url.strip() or settings.database_url
    with psycopg.connect(migration_url, autocommit=True, row_factory=dict_row) as conn:
        register_vector(conn)
        _require_bootstrap(conn)
        conn.execute("SELECT pg_advisory_lock(814231)")
        try:
            _apply(conn, ROOT / "app" / "db" / "schema.sql")
            _apply(conn, ROOT / "app" / "db" / "seed.sql")
            upsert_chunks(conn)
            _demo_user(conn, settings)
            try:
                indexed = index_missing_embeddings(conn)
            except RuntimeError as exc:
                print(f"Aviso: catálogo ainda sem embeddings ({exc}).")
                indexed = 0
        finally:
            conn.execute("SELECT pg_advisory_unlock(814231)")

        counts = conn.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM analista.pedidos) AS pedidos,
              (SELECT COUNT(*) FROM analista.itens_pedido) AS itens,
              (SELECT COUNT(*) FROM analista.schema_chunks) AS chunks,
              (SELECT COUNT(*) FROM analista.schema_chunks WHERE embedding IS NOT NULL) AS embeddings
            """
        ).fetchone()
    print(
        "Banco pronto em 127.0.0.1:5432/app, schema analista. "
        f"Pedidos={counts['pedidos']}, itens={counts['itens']}, "
        f"chunks={counts['chunks']}, embeddings novos nesta execução={indexed}, "
        f"embeddings gravados={counts['embeddings']}."
    )
    print(f"Login de demonstração: {settings.demo_user_email} / {settings.demo_user_password}")


def _require_bootstrap(conn) -> None:
    extension = conn.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'").fetchone()
    role = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = 'analista_leitura'").fetchone()
    if extension is None or role is None:
        raise SystemExit(
            "O Postgres local ainda não tem a extensão vector ou o papel analista_leitura. "
            "Rode: bash server/scripts/bootstrap_local_postgres.sh"
        )


def _apply(conn, path: Path) -> None:
    script = path.read_text(encoding="utf-8")
    for statement in sqlparse.split(script):
        if statement.strip():
            conn.execute(statement)


def _demo_user(conn, settings) -> None:
    email = settings.demo_user_email.strip().lower()
    existing = conn.execute("SELECT 1 FROM analista.usuarios WHERE email = %s", (email,)).fetchone()
    if existing:
        return
    from uuid import uuid4

    conn.execute(
        """
        INSERT INTO analista.usuarios (id, email, senha_hash, nome)
        VALUES (%s, %s, %s, %s)
        """,
        (uuid4(), email, hash_password(settings.demo_user_password), settings.demo_user_name),
    )


if __name__ == "__main__":
    main()
