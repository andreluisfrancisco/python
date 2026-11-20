"""Conversas do usuário e o caso de uso de enviar uma pergunta."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from app.config import get_settings
from app.conversation import store
from app.db.pool import get_pool
from app.llm.grok import LlmNotConfigured
from app.services.analyst import answer, stream_narrative


class ConversationNotFound(Exception):
    """A conversa não existe ou é de outro usuário."""


@dataclass(frozen=True)
class TurnEvent:
    name: str
    payload: dict


def list_conversations(user_id: UUID) -> list[dict]:
    with get_pool().connection() as conn:
        rows = store.list_conversations(conn, user_id)
    return [_conversation(row) for row in rows]


def create_conversation(user_id: UUID, title: str) -> dict:
    cleaned = " ".join(title.split()) or "Nova conversa"
    with get_pool().connection() as conn, conn.transaction():
        conversation_id = store.create_conversation(conn, user_id=user_id, title=cleaned[:80])
        row = store.get_conversation(conn, user_id=user_id, conversation_id=conversation_id)
    return _conversation(row)


def list_messages(user_id: UUID, conversation_id: UUID) -> list[dict]:
    with get_pool().connection() as conn:
        if store.get_conversation(conn, user_id=user_id, conversation_id=conversation_id) is None:
            raise ConversationNotFound()
        return store.list_messages(conn, user_id=user_id, conversation_id=conversation_id)


def require_conversation(user_id: UUID, conversation_id: UUID) -> None:
    if not get_settings().xai_api_key.strip():
        raise LlmNotConfigured("Defina XAI_API_KEY no arquivo .env para consultar o Grok.")
    with get_pool().connection() as conn:
        if store.get_conversation(conn, user_id=user_id, conversation_id=conversation_id) is None:
            raise ConversationNotFound()


def respond(user_id: UUID, conversation_id: UUID, question: str) -> Iterator[TurnEvent]:
    """Grava a pergunta, consulta o analista e devolve os passos da resposta."""
    yield TurnEvent("status", {"text": "Lendo o histórico e o catálogo."})
    with get_pool().connection() as conn:
        history = store.list_messages(conn, user_id=user_id, conversation_id=conversation_id)
        with conn.transaction():
            store.add_message(conn, conversation_id=conversation_id, role="user", content=question)
            store.rename_if_default(conn, conversation_id=conversation_id, title=question)
        execution = answer(conn, question, history)

    if execution.status == "sucesso":
        yield TurnEvent("sql", {"sql": execution.sql, "assumptions": execution.assumptions})
        preview = execution.rows[:50]
        yield TurnEvent(
            "result",
            {
                "columns": execution.columns,
                "rows": [_json_row(execution.columns, row) for row in preview],
                "row_count": len(execution.rows),
                "truncated": len(execution.rows) > 50,
            },
        )
        yield TurnEvent("status", {"text": "Escrevendo a resposta."})
        parts: list[str] = []
        for token in stream_narrative(question, execution):
            parts.append(token)
            yield TurnEvent("token", {"text": token})
        narrative = "".join(parts).strip()
        if not narrative:
            narrative = f"A consulta retornou {len(execution.rows)} linha(s). Os dados estão na tabela."
            yield TurnEvent("token", {"text": narrative})
        _persist(user_id, conversation_id, question, execution, narrative)
        yield TurnEvent("done", {"status": execution.status})
        return

    if execution.error:
        yield TurnEvent("error", {"message": execution.error})
        _persist(user_id, conversation_id, question, execution, execution.error)
        yield TurnEvent("done", {"status": "erro"})
        return

    message = execution.message or "Não consegui responder."
    yield TurnEvent("token", {"text": message})
    _persist(user_id, conversation_id, question, execution, message)
    yield TurnEvent("done", {"status": execution.status})


def _persist(user_id: UUID, conversation_id: UUID, question: str, execution, content: str) -> None:
    with get_pool().connection() as conn, conn.transaction():
        store.add_message(
            conn,
            conversation_id=conversation_id,
            role="assistant",
            content=content,
            sql=execution.sql if execution.status == "sucesso" else None,
        )
        store.audit(
            conn,
            user_id=user_id,
            conversation_id=conversation_id,
            question=question,
            sql=execution.sql,
            status=execution.status,
            detail=execution.error,
        )


def _conversation(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "title": row["titulo"],
        "created_at": row["criada_em"].isoformat(),
    }


def _json_row(columns: list[str], row: tuple) -> dict:
    return {column: _json_value(value) for column, value in zip(columns, row, strict=True)}


def _json_value(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value
