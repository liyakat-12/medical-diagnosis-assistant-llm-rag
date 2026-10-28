from __future__ import annotations


def test_haversine_and_parse_hospitals():
    from app.services.hospital_service import haversine_km, parse_elements

    assert haversine_km(28.61, 77.21, 28.61, 77.21) == 0
    nearby = haversine_km(28.61, 77.21, 28.62, 77.22)
    assert 1 < nearby < 3

    elements = [
        {
            "lat": 28.62,
            "lon": 77.22,
            "tags": {
                "name": "City General Hospital",
                "phone": "+91 11 1234 5678",
                "addr:street": "Ring Road",
                "addr:city": "Delhi",
                "emergency": "yes",
            },
        },
        {"lat": 28.63, "lon": 77.23, "tags": {"name": "City General Hospital"}},
        {"lat": 28.70, "lon": 77.30, "tags": {"amenity": "hospital"}},
    ]
    rows = parse_elements(elements, 28.61, 77.21)
    assert len(rows) == 1
    assert rows[0]["name"] == "City General Hospital"
    assert rows[0]["phone"] == "+91 11 1234 5678"
    assert rows[0]["emergency"] is True
    assert "maps.google.com" in rows[0]["maps_url"] or "google.com/maps" in rows[0]["maps_url"]


def test_parse_nominatim_hospitals():
    from app.services.hospital_service import parse_nominatim

    rows = parse_nominatim(
        [
            {
                "name": "Bowring Hospital",
                "lat": "12.98",
                "lon": "77.60",
                "display_name": "Bowring Hospital, Shivajinagar, Bengaluru",
                "address": {"road": "Shivajinagar", "city": "Bengaluru", "state": "Karnataka"},
                "extratags": {"phone": "080-25591362", "emergency": "yes"},
            },
            {"name": "Bowring Hospital", "lat": "12.99", "lon": "77.61"},
        ],
        12.99,
        77.59,
    )
    assert len(rows) == 1
    assert rows[0]["name"] == "Bowring Hospital"
    assert rows[0]["phone"] == "080-25591362"
    assert rows[0]["emergency"] is True


def test_parse_elements_skips_invalid_coordinates():
    from app.services.hospital_service import parse_elements

    rows = parse_elements(
        [
            {"lat": 0, "lon": 0, "tags": {"name": "Null Island Hospital"}},
            {"lat": 28.62, "lon": 77.22, "tags": {"name": "Valid Hospital"}},
        ],
        28.61,
        77.21,
    )
    assert [row["name"] for row in rows] == ["Valid Hospital"]


def test_nearby_cache_reuses_same_area(monkeypatch):
    from app.services import hospital_service as hs

    hs._NEARBY_CACHE.clear()
    calls = {"n": 0}

    def fake_overpass(lat, lng, radius):
        calls["n"] += 1
        return [
            {
                "name": "Cached Hospital",
                "phone": "",
                "address": "Main Road",
                "distance_km": 1.0,
                "lat": lat,
                "lng": lng,
                "maps_url": "https://www.google.com/maps",
                "emergency": False,
            }
        ]

    monkeypatch.setattr(hs, "_fetch_overpass", fake_overpass)
    first = hs.find_nearby_hospitals(12.971, 77.594)
    second = hs.find_nearby_hospitals(12.9712, 77.5944)
    assert calls["n"] == 1
    assert first["hospitals"][0]["name"] == "Cached Hospital"
    assert second["hospitals"][0]["name"] == "Cached Hospital"


def test_nearby_hospitals_endpoint(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.hospitals.find_nearby_hospitals",
        lambda lat, lng: {
            "hospitals": [
                {
                    "name": "Test Hospital",
                    "phone": "108",
                    "address": "Main Road",
                    "distance_km": 1.2,
                    "lat": lat,
                    "lng": lng,
                    "maps_url": "https://www.google.com/maps",
                    "emergency": True,
                }
            ],
            "emergency_number": "112",
            "error": None,
        },
    )
    client.post("/api/v1/auth/register", json={"name": "Asha", "email": "asha-hosp@test.local", "password": "securepass"})
    listed = client.get("/api/v1/hospitals/nearby?lat=28.61&lng=77.21")
    assert listed.status_code == 200, listed.text
    payload = listed.json()
    assert payload["emergency_number"] == "112"
    assert payload["hospitals"][0]["name"] == "Test Hospital"


def test_map_tile_rejects_invalid_zoom():
    from app.services.hospital_service import fetch_map_tile

    try:
        fetch_map_tile(0, 0, 0)
    except ValueError:
        return
    raise AssertionError("invalid zoom should be rejected")


def test_map_tile_uses_png_fallback(monkeypatch):
    from app.services import hospital_service as hs

    hs._TILE_CACHE.clear()
    hs._HTTP = None

    class FakeResponse:
        def __init__(self, status_code: int, content: bytes):
            self.status_code = status_code
            self.content = content

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def get(self, url: str, **_kwargs):
            if "arcgisonline" in url:
                return FakeResponse(403, b"<html>Access blocked</html>")
            return FakeResponse(200, b"\x89PNG\r\n\x1a\n" + b"tile")

    monkeypatch.setattr(hs, "_http", lambda: FakeClient())
    data = hs.fetch_map_tile(12, 2900, 1700)
    assert data.startswith(b"\x89PNG")
