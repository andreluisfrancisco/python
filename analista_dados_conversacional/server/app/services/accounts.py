"""Cadastro, login e leitura do usuário autenticado."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.auth.passwords import hash_password, verify_password
from app.auth.tokens import create_token
from app.config import get_settings
from app.conversation import store
from app.db.pool import get_pool


class EmailAlreadyRegistered(Exception):
    """O e-mail já tem conta."""


class InvalidCredentials(Exception):
    """E-mail ou senha não conferem."""


class UserNotFound(Exception):
    """O identificador do token não existe mais."""


@dataclass(frozen=True)
class Session:
    user_id: UUID
    access_token: str
    email: str
    name: str


def register(*, email: str, password: str, name: str) -> Session:
    with get_pool().connection() as conn, conn.transaction():
        if store.get_user_by_email(conn, email):
            raise EmailAlreadyRegistered()
        user_id = store.create_user(
            conn,
            email=email,
            password_hash=hash_password(password),
            name=name,
        )
    return _session(user_id, email, name)


def login(*, email: str, password: str) -> Session:
    with get_pool().connection() as conn:
        user = store.get_user_by_email(conn, email)
        if user is None or not verify_password(password, user["senha_hash"]):
            raise InvalidCredentials()
    return _session(user["id"], user["email"], user["nome"])


def profile(user_id: UUID) -> dict:
    with get_pool().connection() as conn:
        user = store.get_user(conn, user_id)
    if user is None:
        raise UserNotFound()
    return {"id": str(user["id"]), "email": user["email"], "name": user["nome"]}


def _session(user_id: UUID, email: str, name: str) -> Session:
    settings = get_settings()
    token = create_token(
        user_id=user_id,
        email=email,
        secret=settings.jwt_secret,
        ttl_minutes=settings.jwt_ttl_minutes,
    )
    return Session(user_id=user_id, access_token=token, email=email, name=name)
