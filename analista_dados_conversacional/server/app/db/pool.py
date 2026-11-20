"""Pool de conexões. O configure registra o tipo vector em cada conexão."""

from __future__ import annotations

from pgvector.psycopg import register_vector
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

_pool: ConnectionPool | None = None


def open_pool(database_url: str) -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            database_url,
            min_size=1,
            max_size=8,
            kwargs={"row_factory": dict_row, "autocommit": True},
            configure=register_vector,
            open=True,
        )
    return _pool


def get_pool() -> ConnectionPool:
    if _pool is None:
        raise RuntimeError("O pool de conexões não foi iniciado.")
    return _pool


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
