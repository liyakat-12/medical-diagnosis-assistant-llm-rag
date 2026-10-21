from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core import config
from app.connection.indexes import ensure_indexes
from app.connection.mongodb import connect, disconnect
from app.services.auth_service import seed_demo_user

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("mediassist")


def _warmup_rag() -> None:
    """Load MiniLM, the re-ranker, and Chroma once so the first chat is not a 2–4 minute wait."""
    import time

    started = time.perf_counter()
    try:
        from src.retrieval.retriever import retrieve

        retrieve("headache", top_k=4)
        logger.info("RAG models warmed in %.1fs", time.perf_counter() - started)
    except Exception:
        logger.exception("RAG warmup skipped")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await connect()
    await ensure_indexes()
    await seed_demo_user()
    _warmup_rag()
    logger.info("MediAssist API ready")
    yield
    await disconnect()
    logger.info("MediAssist API stopped")


app = FastAPI(
    title="MediAssist API",
    description="Medical RAG assistant with triage, citations, and persistent chats.",
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


@app.get("/")
def root() -> dict:
    return {
        "service": "MediAssist API",
        "website": "http://localhost:5173",
        "health": "/api/v1/health",
        "docs": "/docs",
    }
