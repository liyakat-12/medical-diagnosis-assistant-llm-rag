from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response

from app.core.dependencies import get_current_user
from app.services.hospital_service import fetch_map_tile, find_nearby_hospitals, geocode_place, locate_by_ip

router = APIRouter(prefix="/hospitals", tags=["hospitals"])


@router.get("/map-tiles/{z}/{x}/{y}.png")
async def map_tile(z: int, x: int, y: int) -> Response:
    """Serve map tiles so the browser is not blocked by OpenStreetMap's tile policy."""
    try:
        data = await asyncio.to_thread(fetch_map_tile, z, x, y)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid map tile.")
    except Exception:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Map tiles are temporarily unavailable.")
    return Response(
        content=data,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/nearby")
async def nearby_hospitals(
    lat: float | None = Query(None, ge=-90, le=90),
    lng: float | None = Query(None, ge=-180, le=180),
    q: str | None = Query(None, min_length=2, max_length=120),
    _user: dict = Depends(get_current_user),
) -> dict:
    label = None
    if q and (lat is None or lng is None):
        place = await asyncio.to_thread(geocode_place, q)
        if not place:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Could not find that place.")
        lat = float(place["lat"])
        lng = float(place["lng"])
        label = place["label"]
    if lat is None or lng is None:
        here = await asyncio.to_thread(locate_by_ip)
        if not here:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Share your location, or type a city name.")
        lat = float(here["lat"])
        lng = float(here["lng"])
        label = here["label"]
    result = await asyncio.to_thread(find_nearby_hospitals, lat, lng)
    result["origin"] = {"lat": lat, "lng": lng, "label": label}
    return result
