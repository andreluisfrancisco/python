"""Executa o SELECT já validado em transação somente leitura."""

from __future__ import annotations

import logging

import psycopg

logger = logging.getLogger(__name__)

READ_ROLE = "analista_leitura"


class QueryFailed(Exception):
    def __init__(self, detail: str, *, user_message: str) -> None:
        super().__init__(detail)
        self.detail = detail
        self.user_message = user_message


def run_readonly(conn: psycopg.Connection, sql: str, *, timeout_ms: int) -> tuple[list[str], list[tuple]]:
    timeout = int(timeout_ms)
    if not 100 <= timeout <= 30_000:
        raise QueryFailed("timeout fora da faixa", user_message="Tempo limite da consulta está inválido.")
    try:
        with conn.transaction():
            conn.execute("SET LOCAL transaction_read_only = on")
            conn.execute(f"SET LOCAL statement_timeout = {timeout}")
            conn.execute("SET LOCAL search_path = analista")
            conn.execute(f"SET LOCAL ROLE {READ_ROLE}")
            cursor = conn.execute(sql)
            columns = [column.name for column in cursor.description or []]
            fetched = cursor.fetchall()
    except psycopg.errors.QueryCanceled as exc:
        raise QueryFailed(str(exc), user_message="A consulta passou do tempo limite. Tente um recorte menor.") from exc
    except psycopg.Error as exc:
        detail = str(exc).splitlines()[0][:300]
        logger.info("consulta recusada pelo banco: %s", detail)
        raise QueryFailed(detail, user_message="A consulta não pôde ser executada.") from exc

    rows: list[tuple] = []
    for item in fetched:
        if isinstance(item, dict):
            rows.append(tuple(item.get(column) for column in columns))
        else:
            rows.append(tuple(item))
    return columns, rows
