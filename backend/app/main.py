from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core import config
from app.connection.indexes import ensure_indexes
from app.connection.mongodb import connect, disconnect
from app.services.auth_service import seed_demo_user

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("mediassist")


def _warmup_rag() -> None:
    """Load MiniLM, Chroma, and the re-ranker in a worker thread so the first chat is not a cold start."""
    import time

    started = time.perf_counter()
    try:
        from src import config
        from src.embeddings.embedding_models import get_embedding_model
        from src.retrieval.retriever import retrieve

        get_embedding_model(config.EMBEDDING_MODE).encode(["headache"])
        retrieve("headache", top_k=4)
        if config.RERANK_ENABLED:
            from src.retrieval.reranker import _load_model

            _load_model()
        logger.info("RAG models warmed in %.1fs", time.perf_counter() - started)
    except Exception:
        logger.exception("RAG warmup skipped")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    from src.config import validate_runtime_config

    validate_runtime_config()
    await connect()
    await ensure_indexes()
    await seed_demo_user()
    await asyncio.to_thread(_warmup_rag)
    logger.info("MediAssist API ready")
    yield
    await disconnect()
    logger.info("MediAssist API stopped")


app = FastAPI(
    title="MediAssist API",
    description="Medical-information and general conversational assistant. Not a substitute for professional diagnosis.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.exception_handler(Exception)
async def unhandled_error(_request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, HTTPException):
        raise exc
    logger.error("Unhandled server error: %s", type(exc).__name__, exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong. Please try again."})


@app.get("/")
def root() -> dict:
    return {
        "service": "MediAssist API",
        "website": "http://localhost:5173",
        "health": "/api/v1/health",
        "docs": "/docs",
    }
