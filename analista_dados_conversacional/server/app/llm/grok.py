"""Grok via LangChain. A chave fica no ambiente, nunca no código."""

from __future__ import annotations

from collections.abc import Iterator

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_xai import ChatXAI

from app.config import get_settings


class LlmNotConfigured(RuntimeError):
    """XAI_API_KEY ausente."""


def _model(*, temperature: float, max_tokens: int) -> ChatXAI:
    settings = get_settings()
    if not settings.xai_api_key.strip():
        raise LlmNotConfigured("Defina XAI_API_KEY no arquivo .env.")
    return ChatXAI(
        model=settings.xai_model,
        api_key=settings.xai_api_key,
        base_url=settings.xai_base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=120,
        max_retries=2,
    )


def message_text(message) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
        return "".join(parts)
    return str(content or "")


def complete(system: str, user: str, *, temperature: float, max_tokens: int) -> str:
    response = _model(temperature=temperature, max_tokens=max_tokens).invoke(
        [SystemMessage(content=system), HumanMessage(content=user)]
    )
    return message_text(response)


def stream_text(system: str, user: str, *, temperature: float, max_tokens: int) -> Iterator[str]:
    model = _model(temperature=temperature, max_tokens=max_tokens)
    for chunk in model.stream([SystemMessage(content=system), HumanMessage(content=user)]):
        text = message_text(chunk)
        if text:
            yield text
