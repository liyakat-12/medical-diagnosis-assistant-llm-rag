from __future__ import annotations

from fastapi import APIRouter

from app.core import config
from src.ai.registry import available_providers

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "embedding_mode": config.EMBEDDING_MODE,
        "llm_provider": config.LLM_PROVIDER,
        "effective_llm_provider": config.resolve_llm_provider(),
        "providers": available_providers(),
    }
