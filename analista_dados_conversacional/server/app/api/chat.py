"""Conversas e resposta em streaming (SSE)."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from app.api.deps import current_user_id
from app.llm.grok import LlmNotConfigured
from app.services.conversations import (
    ConversationNotFound,
    create_conversation,
    list_conversations,
    list_messages,
    require_conversation,
    respond,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


class ConversationIn(BaseModel):
    title: str = "Nova conversa"


class MessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Escreva uma pergunta.")
        return cleaned


@router.get("/conversations")
def list_conversations_route(user_id: UUID = Depends(current_user_id)) -> list[dict]:
    return list_conversations(user_id)


@router.post("/conversations", status_code=201)
def create_conversation_route(body: ConversationIn, user_id: UUID = Depends(current_user_id)) -> dict:
    return create_conversation(user_id, body.title)


@router.get("/conversations/{conversation_id}/messages")
def list_messages_route(conversation_id: UUID, user_id: UUID = Depends(current_user_id)) -> list[dict]:
    try:
        return list_messages(user_id, conversation_id)
    except ConversationNotFound as exc:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.") from exc


@router.post("/conversations/{conversation_id}/messages")
def send_message(
    conversation_id: UUID,
    body: MessageIn,
    user_id: UUID = Depends(current_user_id),
) -> StreamingResponse:
    try:
        require_conversation(user_id, conversation_id)
    except ConversationNotFound as exc:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.") from exc
    except LlmNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return StreamingResponse(
        _events(user_id, conversation_id, body.content),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _events(user_id: UUID, conversation_id: UUID, question: str) -> Iterator[str]:
    try:
        for event in respond(user_id, conversation_id, question):
            yield _sse(event.name, event.payload)
    except LlmNotConfigured as exc:
        yield _sse("error", {"message": str(exc)})
        yield _sse("done", {"status": "erro"})
    except Exception:
        logger.exception("falha ao responder")
        yield _sse("error", {"message": "Não foi possível concluir a resposta."})
        yield _sse("done", {"status": "erro"})


def _sse(event: str, data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"
