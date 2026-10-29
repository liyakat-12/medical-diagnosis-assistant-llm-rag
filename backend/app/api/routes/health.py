from __future__ import annotations

from fastapi import APIRouter, Response

from app.core import config

router = APIRouter(tags=["health"])


def _retrieval_status() -> dict:
    """Inspect Chroma population without exposing secrets or filesystem paths."""
    try:
        from src.retrieval.retriever import _get_store

        mode = (config.EMBEDDING_MODE or "general").strip().lower()
        store = _get_store(mode)
        count = int(store.count())
        ready = count > 0
        return {
            "retrieval_ready": ready,
            "retrieval_mode": mode,
            "retrieval_documents": count,
            "retrieval_error": None if ready else "Knowledge-base index is empty or unavailable.",
        }
    except Exception:
        return {
            "retrieval_ready": False,
            "retrieval_mode": (config.EMBEDDING_MODE or "general").strip().lower(),
            "retrieval_documents": 0,
            "retrieval_error": "Knowledge-base index could not be opened.",
        }


@router.get("/health")
def health(response: Response) -> dict:
    """Platform health/readiness probe used by Render.

    Returns HTTP 503 in production when the retrieval index is empty so an
    empty Chroma collection is never treated as a healthy deployment.
    """
    try:
        database_mode = config.mongo_uri_mode()
    except ValueError:
        database_mode = "invalid"
    retrieval = _retrieval_status()
    ready = bool(retrieval["retrieval_ready"]) and database_mode != "invalid"
    if config.is_production() and not ready:
        response.status_code = 503
        status = "unavailable"
    else:
        status = "ok" if ready else "degraded"
    return {
        "status": status,
        "service": "MediAssist",
        "disclaimer": "Medical-information tool, not a substitute for professional diagnosis.",
        "app_env": config.APP_ENV,
        "database_mode": database_mode,
        "emergency_region": config.EMERGENCY_REGION,
        "emergency_number": config.EMERGENCY_NUMBER,
        **retrieval,
    }
