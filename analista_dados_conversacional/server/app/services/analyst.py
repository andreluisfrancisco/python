"""Do texto da pergunta até um SELECT executado, ou um pedido de esclarecimento."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from psycopg import Connection

from app.catalog.indexer import schema_context
from app.config import get_settings
from app.conversation.history import render_history
from app.llm.grok import complete, stream_text
from app.llm.parsing import ModelFormatError, parse_model_json
from app.llm.prompts import render
from app.sql_guard.executor import QueryFailed, run_readonly
from app.sql_guard.validator import SqlRejected, validate

logger = logging.getLogger(__name__)

INTENTS = {"query", "clarify", "refuse", "chat"}


@dataclass
class Execution:
    intent: str
    sql: str | None = None
    message: str | None = None
    assumptions: list[str] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    rows: list[tuple] = field(default_factory=list)
    error: str | None = None
    status: str = "erro"


def answer(conn: Connection, question: str, history: list[dict]) -> Execution:
    settings = get_settings()
    schema = schema_context(conn, question)
    user_prompt = render(
        "text_to_sql_user.md",
        SCHEMA=schema,
        HISTORY=render_history(history, max_messages=settings.history_max_messages),
        QUESTION=question.strip(),
    )
    system_prompt = render("text_to_sql_system.md")
    try:
        raw = complete(system_prompt, user_prompt, temperature=0, max_tokens=1200)
        plan = _plan(raw)
    except ModelFormatError as exc:
        return Execution(intent="erro", error=str(exc), status="erro")

    if plan["intent"] != "query":
        status = {"clarify": "esclarecimento", "refuse": "recusa", "chat": "conversa"}[plan["intent"]]
        return Execution(
            intent=plan["intent"],
            message=plan.get("message") or "Não consegui responder com os dados disponíveis.",
            assumptions=_assumptions(plan),
            status=status,
        )

    return _run_query(conn, question.strip(), plan)


def stream_narrative(question: str, execution: Execution):
    preview = execution.rows[:30]
    payload = render(
        "narrativa.md",
        QUESTION=question.strip(),
        ASSUMPTIONS="; ".join(execution.assumptions) or "nenhuma",
        COLUMNS=", ".join(execution.columns) or "(nenhuma)",
        TRUNCATED="sim" if len(execution.rows) > 30 else "não",
        ROW_COUNT=str(len(execution.rows)),
        ROWS=json.dumps(_json_rows(execution.columns, preview), ensure_ascii=False, default=_json_default),
    )
    yield from stream_text(
        "Você escreve a resposta final para o usuário.",
        payload,
        temperature=0.2,
        max_tokens=800,
    )


def _run_query(conn: Connection, question: str, plan: dict) -> Execution:
    assumptions = _assumptions(plan)
    sql_text = plan.get("sql") or ""
    try:
        sql = validate(sql_text, max_rows=get_settings().sql_row_limit)
        columns, rows = run_readonly(conn, sql, timeout_ms=get_settings().sql_timeout_ms)
        return Execution(
            intent="query",
            sql=sql,
            assumptions=assumptions,
            columns=columns,
            rows=rows,
            status="sucesso",
        )
    except (SqlRejected, QueryFailed) as first_error:
        reason = first_error.reason if isinstance(first_error, SqlRejected) else first_error.detail
        logger.info("primeira consulta recusada: %s", reason)
        try:
            repaired = _repair(question, sql_text, reason)
        except ModelFormatError as exc:
            return Execution(intent="query", sql=sql_text, assumptions=assumptions, error=str(exc), status="erro")
        if repaired["intent"] != "query":
            status = {"clarify": "esclarecimento", "refuse": "recusa", "chat": "conversa"}.get(
                repaired["intent"], "erro"
            )
            return Execution(
                intent=repaired["intent"],
                message=repaired.get("message"),
                assumptions=_assumptions(repaired),
                status=status,
            )
        try:
            sql = validate(repaired.get("sql") or "", max_rows=get_settings().sql_row_limit)
            columns, rows = run_readonly(conn, sql, timeout_ms=get_settings().sql_timeout_ms)
        except (SqlRejected, QueryFailed) as second_error:
            message = second_error.reason if isinstance(second_error, SqlRejected) else second_error.user_message
            return Execution(
                intent="query",
                sql=repaired.get("sql"),
                assumptions=assumptions,
                error=message,
                status="erro",
            )
        return Execution(
            intent="query",
            sql=sql,
            assumptions=_assumptions(repaired) or assumptions,
            columns=columns,
            rows=rows,
            status="sucesso",
        )


def _repair(question: str, sql: str, error: str) -> dict:
    raw = complete(
        render("text_to_sql_system.md"),
        render("repair.md", QUESTION=question, SQL=sql or "(vazio)", ERROR=error),
        temperature=0,
        max_tokens=1200,
    )
    return _plan(raw)


def _plan(raw: str) -> dict:
    payload = parse_model_json(raw)
    intent = str(payload.get("intent") or "").strip().lower()
    if intent not in INTENTS:
        raise ModelFormatError("O modelo devolveu um intent desconhecido.")
    payload["intent"] = intent
    return payload


def _assumptions(plan: dict) -> list[str]:
    values = plan.get("assumptions") or []
    if not isinstance(values, list):
        return []
    return [str(item) for item in values if str(item).strip()]


def _json_rows(columns: list[str], rows: list[tuple]) -> list[dict]:
    rendered = []
    for row in rows:
        rendered.append({column: _json_default(value) for column, value in zip(columns, row, strict=True)})
    return rendered


def _json_default(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value
