"""Dependências das rotas."""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.tokens import InvalidToken, read_token
from app.config import get_settings

_bearer = HTTPBearer(auto_error=False)


def current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> UUID:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Faça login para continuar.")
    settings = get_settings()
    try:
        payload = read_token(credentials.credentials, secret=settings.jwt_secret)
        return UUID(payload["sub"])
    except (InvalidToken, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Sessão inválida. Entre de novo.") from exc
