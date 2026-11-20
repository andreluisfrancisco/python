"""Conversas, mensagens e auditoria. Cada consulta filtra pelo usuário."""

from __future__ import annotations

from uuid import UUID, uuid4

from psycopg import Connection


def create_user(conn: Connection, *, email: str, password_hash: str, name: str) -> UUID:
    user_id = uuid4()
    conn.execute(
        """
        INSERT INTO analista.usuarios (id, email, senha_hash, nome)
        VALUES (%s, %s, %s, %s)
        """,
        (user_id, email, password_hash, name),
    )
    return user_id


def get_user_by_email(conn: Connection, email: str) -> dict | None:
    return conn.execute(
        "SELECT id, email, senha_hash, nome FROM analista.usuarios WHERE email = %s",
        (email,),
    ).fetchone()


def get_user(conn: Connection, user_id: UUID) -> dict | None:
    return conn.execute(
        "SELECT id, email, nome FROM analista.usuarios WHERE id = %s",
        (user_id,),
    ).fetchone()


def create_conversation(conn: Connection, *, user_id: UUID, title: str = "Nova conversa") -> UUID:
    conversation_id = uuid4()
    conn.execute(
        "INSERT INTO analista.conversas (id, usuario_id, titulo) VALUES (%s, %s, %s)",
        (conversation_id, user_id, title),
    )
    return conversation_id


def list_conversations(conn: Connection, user_id: UUID) -> list[dict]:
    return conn.execute(
        """
        SELECT id, titulo, criada_em
        FROM analista.conversas
        WHERE usuario_id = %s
        ORDER BY criada_em DESC
        """,
        (user_id,),
    ).fetchall()


def get_conversation(conn: Connection, *, user_id: UUID, conversation_id: UUID) -> dict | None:
    return conn.execute(
        """
        SELECT id, titulo, criada_em
        FROM analista.conversas
        WHERE id = %s AND usuario_id = %s
        """,
        (conversation_id, user_id),
    ).fetchone()


def rename_if_default(conn: Connection, *, conversation_id: UUID, title: str) -> None:
    conn.execute(
        """
        UPDATE analista.conversas
        SET titulo = %s
        WHERE id = %s AND titulo = 'Nova conversa'
        """,
        (title[:80], conversation_id),
    )


def list_messages(conn: Connection, *, user_id: UUID, conversation_id: UUID) -> list[dict]:
    rows = conn.execute(
        """
        SELECT m.papel, m.conteudo, m.sql, m.criada_em
        FROM analista.mensagens m
        JOIN analista.conversas c ON c.id = m.conversa_id
        WHERE m.conversa_id = %s AND c.usuario_id = %s
        ORDER BY m.id
        """,
        (conversation_id, user_id),
    ).fetchall()
    return [{"role": row["papel"], "content": row["conteudo"], "sql": row["sql"]} for row in rows]


def add_message(
    conn: Connection,
    *,
    conversation_id: UUID,
    role: str,
    content: str,
    sql: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO analista.mensagens (conversa_id, papel, conteudo, sql)
        VALUES (%s, %s, %s, %s)
        """,
        (conversation_id, role, content, sql),
    )


def audit(
    conn: Connection,
    *,
    user_id: UUID,
    conversation_id: UUID | None,
    question: str,
    sql: str | None,
    status: str,
    detail: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO analista.auditoria_sql (usuario_id, conversa_id, pergunta, sql, status, detalhe)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (user_id, conversation_id, question, sql, status, detail),
    )
