"""Janela de histórico enviada ao modelo.

O banco guarda a conversa inteira. O prompt recebe só as últimas mensagens,
com texto curto, para o follow-up funcionar sem estourar o contexto.
"""

from __future__ import annotations


def render_history(messages: list[dict], *, max_messages: int, max_chars: int = 500) -> str:
    if max_messages < 1:
        return "(sem histórico)"
    window = list(messages[-max_messages:])
    while window and window[0].get("role") == "assistant":
        window = window[1:]
    if not window:
        return "(sem histórico)"

    lines: list[str] = []
    for message in window:
        content = " ".join(str(message.get("content") or "").split())
        if len(content) > max_chars:
            content = content[: max_chars - 1] + "…"
        if message.get("role") == "user":
            lines.append(f"Usuário: {content}")
            continue
        sql = message.get("sql")
        if sql:
            compact_sql = " ".join(str(sql).split())
            lines.append(f"Analista (SQL já executado: {compact_sql}): {content}")
        else:
            lines.append(f"Analista: {content}")
    return "\n".join(lines)
