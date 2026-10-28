from __future__ import annotations

from datetime import timedelta

from app.core import config
from app.core.security import create_access_token, decode_token


def test_access_token_roundtrip():
    token = create_access_token("user-123")
    assert decode_token(token, "access") == "user-123"
    assert decode_token(token, "refresh") is None


def test_expired_token_is_rejected():
    import jwt
    from datetime import datetime, timezone

    payload = {
        "sub": "user-123",
        "type": "access",
        "iat": int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()),
        "exp": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()),
    }
    token = jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")
    assert decode_token(token, "access") is None


def test_refresh_and_logout_cookies(client):
    client.post("/api/v1/auth/register", json={"name": "Asha", "email": "asha@test.local", "password": "securepass"})
    refreshed = client.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 200
    assert refreshed.json()["email"] == "asha@test.local"
    client.post("/api/v1/auth/logout")
    denied = client.get("/api/v1/auth/me")
    assert denied.status_code == 401
    stale_refresh = client.post("/api/v1/auth/refresh")
    assert stale_refresh.status_code == 401


def test_health_exposes_non_secret_config(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "jwt" not in str(body).lower()
    assert "secret" not in str(body).lower()
    assert body["emergency_number"]
    assert body["database_mode"] in {"memory", "persistent"}
    assert "not a substitute" in body["disclaimer"].lower()
    lowered = str(body).lower()
    for marker in ("groq", "openai", "ollama", "chatgpt", "gpt-oss"):
        assert marker not in lowered
    assert "llm_provider" not in body


def test_in_memory_mongo_isolation(client):
    client.post("/api/v1/auth/register", json={"name": "Asha", "email": "asha@test.local", "password": "securepass"})
    created = client.post("/api/v1/chats", json={})
    chat_id = created.json()["id"]
    client.post("/api/v1/auth/logout")
    client.post("/api/v1/auth/register", json={"name": "Ben", "email": "ben@test.local", "password": "securepass"})
    listed = client.get("/api/v1/chats")
    assert listed.status_code == 200
    assert all(item["id"] != chat_id for item in listed.json())
