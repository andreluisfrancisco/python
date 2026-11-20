"""Cadastro e login. Vários usuários, cada um com as próprias conversas."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.api.deps import current_user_id
from app.services.accounts import (
    EmailAlreadyRegistered,
    InvalidCredentials,
    Session,
    UserNotFound,
    login,
    profile,
    register,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=200)
    name: str = Field(min_length=1, max_length=120)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        email = value.strip().lower()
        if "@" not in email or "." not in email.split("@")[-1]:
            raise ValueError("Informe um e-mail válido.")
        return email

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        name = " ".join(value.split())
        if not name:
            raise ValueError("Informe o nome.")
        return name


class LoginIn(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str
    name: str


@router.post("/register", response_model=TokenOut)
def register_route(body: RegisterIn) -> TokenOut:
    try:
        session = register(email=body.email, password=body.password, name=body.name)
    except EmailAlreadyRegistered as exc:
        raise HTTPException(status_code=409, detail="Já existe uma conta com esse e-mail.") from exc
    return _token(session)


@router.post("/login", response_model=TokenOut)
def login_route(body: LoginIn) -> TokenOut:
    try:
        session = login(email=body.email, password=body.password)
    except InvalidCredentials as exc:
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos.") from exc
    return _token(session)


@router.get("/me")
def me(user_id: UUID = Depends(current_user_id)) -> dict:
    try:
        return profile(user_id)
    except UserNotFound as exc:
        raise HTTPException(status_code=401, detail="Usuário não encontrado.") from exc


def _token(session: Session) -> TokenOut:
    return TokenOut(access_token=session.access_token, email=session.email, name=session.name)
