from __future__ import annotations

import math
from typing import Any

import httpx

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
SEARCH_RADIUS_M = 8000
RESULT_LIMIT = 8


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return round(2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 2)


def _tag(tags: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = tags.get(key)
        if value:
            return str(value).strip()
    return ""


def _address(tags: dict[str, Any]) -> str:
    full = _tag(tags, "addr:full")
    if full:
        return full
    parts = [
        _tag(tags, "addr:housenumber"),
        _tag(tags, "addr:street"),
        _tag(tags, "addr:suburb", "addr:locality"),
        _tag(tags, "addr:city"),
        _tag(tags, "addr:state"),
        _tag(tags, "addr:postcode"),
    ]
    return ", ".join(part for part in parts if part)


def _coords(element: dict[str, Any]) -> tuple[float, float] | None:
    if "lat" in element and "lon" in element:
        return float(element["lat"]), float(element["lon"])
    center = element.get("center") or {}
    if "lat" in center and "lon" in center:
        return float(center["lat"]), float(center["lon"])
    return None


def parse_elements(elements: list[dict[str, Any]], lat: float, lng: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for element in elements:
        tags = element.get("tags") or {}
        name = _tag(tags, "name", "official_name")
        if not name:
            continue
        coords = _coords(element)
        if not coords:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        hospital_lat, hospital_lng = coords
        phone = _tag(tags, "phone", "contact:phone", "telephone")
        rows.append(
            {
                "name": name,
                "phone": phone,
                "address": _address(tags) or "Address not listed",
                "distance_km": haversine_km(lat, lng, hospital_lat, hospital_lng),
                "lat": hospital_lat,
                "lng": hospital_lng,
                "maps_url": f"https://www.google.com/maps/dir/?api=1&destination={hospital_lat},{hospital_lng}",
                "emergency": _tag(tags, "emergency").lower() in {"yes", "emergency"},
            }
        )
    rows.sort(key=lambda item: item["distance_km"])
    return rows[:RESULT_LIMIT]


def _overpass_query(lat: float, lng: float, radius: int) -> str:
    return f"""
    [out:json][timeout:20];
    (
      node["amenity"="hospital"](around:{radius},{lat},{lng});
      way["amenity"="hospital"](around:{radius},{lat},{lng});
      node["amenity"="clinic"](around:{radius},{lat},{lng});
      way["amenity"="clinic"](around:{radius},{lat},{lng});
    );
    out center tags;
    """


def find_nearby_hospitals(lat: float, lng: float, radius: int = SEARCH_RADIUS_M) -> dict[str, Any]:
    query = _overpass_query(lat, lng, radius)
    try:
        with httpx.Client(timeout=22.0, headers={"User-Agent": "MediAssist/1.0 academic-project"}) as client:
            response = client.post(OVERPASS_URL, data={"data": query})
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        return {
            "hospitals": [],
            "emergency_number": "108",
            "error": f"Unable to load nearby hospitals right now ({exc.__class__.__name__}). Call 108 if this is urgent.",
        }

    hospitals = parse_elements(payload.get("elements") or [], lat, lng)
    if not hospitals and radius < 20000:
        return find_nearby_hospitals(lat, lng, radius=20000)
    return {
        "hospitals": hospitals,
        "emergency_number": "108",
        "error": None if hospitals else "No hospitals were found nearby. Call 108 for ambulance help.",
    }
