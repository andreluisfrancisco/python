"""Configuração lida do ambiente e do arquivo .env na raiz do projeto."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

SERVER_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SERVER_ROOT.parent
ROOT = PROJECT_ROOT


class Settings(BaseSettings):
    database_url: str = "postgresql://developer@127.0.0.1:5432/app"
    migration_database_url: str = ""
    xai_api_key: str = ""
    xai_model: str = "grok-4.7"
    xai_base_url: str = "https://api.x.ai/v1"
    embedding_model: str = "v1"
    embedding_dimensions: int = 768
    jwt_secret: str = "troque-por-uma-string-longa-e-aleatoria"
    jwt_ttl_minutes: int = 720
    sql_row_limit: int = 200
    sql_timeout_ms: int = 5000
    history_max_messages: int = 12
    catalog_top_k: int = 4
    demo_user_email: str = "demo@aurora.local"
    demo_user_password: str = "demo1234"
    demo_user_name: str = "Ana Demo"
    api_base_url: str = "http://localhost:8000"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
