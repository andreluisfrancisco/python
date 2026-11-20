"""JWT de sessão. O identificador do usuário vai no subject."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt


class InvalidToken(Exception):
    pass


def create_token(*, user_id: UUID, email: str, secret: str, ttl_minutes: int) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": now,
        "exp": now + timedelta(minutes=ttl_minutes),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def read_token(token: str, *, secret: str) -> dict:
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise InvalidToken("Token inválido.") from exc
    if not payload.get("sub"):
        raise InvalidToken("Token sem usuário.")
    return payload
