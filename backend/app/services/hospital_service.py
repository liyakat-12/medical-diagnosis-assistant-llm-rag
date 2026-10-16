from __future__ import annotations

import math
from typing import Any

import httpx

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
SEARCH_RADIUS_M = 8000
RESULT_LIMIT = 8
HEADERS = {"User-Agent": "MediAssist/1.0 academic-project (hospital-lookup)"}
FRIENDLY_ERROR = "Unable to load nearby hospitals right now. The map below still works, or call 108 if this is urgent."


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


def parse_nominatim(items: list[dict[str, Any]], lat: float, lng: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        name = str(item.get("name") or item.get("display_name") or "").split(",")[0].strip()
        if not name:
            continue
        try:
            hospital_lat = float(item["lat"])
            hospital_lng = float(item["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        address = item.get("address") or {}
        parts = [
            address.get("road") or address.get("suburb") or "",
            address.get("city") or address.get("town") or address.get("village") or "",
            address.get("state") or "",
        ]
        extras = item.get("extratags") or {}
        phone = str(extras.get("phone") or extras.get("contact:phone") or "").strip()
        rows.append(
            {
                "name": name,
                "phone": phone,
                "address": ", ".join(part for part in parts if part) or str(item.get("display_name") or "Address not listed"),
                "distance_km": haversine_km(lat, lng, hospital_lat, hospital_lng),
                "lat": hospital_lat,
                "lng": hospital_lng,
                "maps_url": f"https://www.google.com/maps/dir/?api=1&destination={hospital_lat},{hospital_lng}",
                "emergency": str(extras.get("emergency") or "").lower() in {"yes", "emergency"},
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


def _fetch_overpass(lat: float, lng: float, radius: int) -> list[dict[str, Any]]:
    query = _overpass_query(lat, lng, radius)
    last_error: Exception | None = None
    for url in OVERPASS_URLS:
        try:
            with httpx.Client(timeout=18.0, headers=HEADERS, follow_redirects=True) as client:
                response = client.post(url, data={"data": query})
                if response.status_code >= 400:
                    last_error = httpx.HTTPStatusError(
                        f"{response.status_code}",
                        request=response.request,
                        response=response,
                    )
                    continue
                payload = response.json()
                return parse_elements(payload.get("elements") or [], lat, lng)
        except Exception as exc:
            last_error = exc
            continue
    if last_error:
        raise last_error
    return []


def _fetch_nominatim(lat: float, lng: float) -> list[dict[str, Any]]:
    delta = 0.09
    params = {
        "format": "jsonv2",
        "q": "hospital",
        "limit": 12,
        "addressdetails": 1,
        "extratags": 1,
        "bounded": 1,
        "viewbox": f"{lng - delta},{lat + delta},{lng + delta},{lat - delta}",
    }
    with httpx.Client(timeout=18.0, headers=HEADERS, follow_redirects=True) as client:
        response = client.get(NOMINATIM_URL, params=params)
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, list):
        return []
    return parse_nominatim(payload, lat, lng)


def find_nearby_hospitals(lat: float, lng: float, radius: int = SEARCH_RADIUS_M) -> dict[str, Any]:
    hospitals: list[dict[str, Any]] = []
    try:
        hospitals = _fetch_overpass(lat, lng, radius)
        if not hospitals and radius < 20000:
            hospitals = _fetch_overpass(lat, lng, 20000)
    except Exception:
        hospitals = []

    if not hospitals:
        try:
            hospitals = _fetch_nominatim(lat, lng)
        except Exception:
            hospitals = []

    if hospitals:
        return {"hospitals": hospitals, "emergency_number": "108", "error": None}
    return {
        "hospitals": [],
        "emergency_number": "108",
        "error": FRIENDLY_ERROR,
    }
