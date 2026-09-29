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
            "emergency_number": "108",
            "error": None,
        },
    )
    client.post("/api/v1/auth/register", json={"name": "Asha", "email": "asha-hosp@test.local", "password": "securepass"})
    listed = client.get("/api/v1/hospitals/nearby?lat=28.61&lng=77.21")
    assert listed.status_code == 200, listed.text
    payload = listed.json()
    assert payload["emergency_number"] == "108"
    assert payload["hospitals"][0]["name"] == "Test Hospital"
