from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_user
from app.services.hospital_service import find_nearby_hospitals

router = APIRouter(prefix="/hospitals", tags=["hospitals"])


@router.get("/nearby")
async def nearby_hospitals(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    _user: dict = Depends(get_current_user),
) -> dict:
    return find_nearby_hospitals(lat, lng)
