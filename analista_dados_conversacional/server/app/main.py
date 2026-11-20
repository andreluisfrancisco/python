"""API do analista de dados conversacional."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.config import get_settings
from app.db.pool import close_pool, get_pool, open_pool

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    open_pool(get_settings().database_url)
    yield
    close_pool()


app = FastAPI(
    title="Analista de Dados Conversacional",
    summary="Text-to-SQL com Grok, Postgres e pgvector.",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(auth_router)
app.include_router(chat_router)


@app.get("/health")
def health() -> JSONResponse:
    try:
        with get_pool().connection() as conn:
            conn.execute("SELECT 1")
            vector = conn.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'").fetchone()
        body = {"status": "ok", "database": True, "pgvector": vector["extversion"] if vector else None}
        return JSONResponse(status_code=200, content=body)
    except Exception:
        logger.exception("health check falhou")
        return JSONResponse(status_code=503, content={"status": "erro", "database": False, "pgvector": None})
