from __future__ import annotations

from fastapi import APIRouter

from app.core import config

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    try:
        database_mode = config.mongo_uri_mode()
    except ValueError:
        database_mode = "invalid"
    return {
        "status": "ok",
        "service": "MediAssist",
        "disclaimer": "Medical-information tool, not a substitute for professional diagnosis.",
        "app_env": config.APP_ENV,
        "database_mode": database_mode,
        "emergency_region": config.EMERGENCY_REGION,
        "emergency_number": config.EMERGENCY_NUMBER,
    }
