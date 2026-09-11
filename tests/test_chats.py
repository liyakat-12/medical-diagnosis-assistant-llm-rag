from __future__ import annotations


def test_register_login_me_logout(client):
    register = client.post(
        "/api/v1/auth/register",
        json={"name": "Asha", "email": "asha@test.local", "password": "securepass"},
    )
    assert register.status_code == 200, register.text
    assert register.json()["email"] == "asha@test.local"
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["name"] == "Asha"
    client.post("/api/v1/auth/logout")
    denied = client.get("/api/v1/auth/me")
    assert denied.status_code == 401


def test_demo_login(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@clinic.local", "password": "demo123"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["email"] == "demo@clinic.local"


def test_invalid_login(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@clinic.local", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_chat_ownership(client):
    client.post("/api/v1/auth/register", json={"name": "Asha", "email": "asha@test.local", "password": "securepass"})
    created = client.post("/api/v1/chats", json={})
    assert created.status_code == 200
    chat_id = created.json()["id"]
    listed = client.get("/api/v1/chats")
    assert listed.json()[0]["id"] == chat_id
    renamed = client.patch(f"/api/v1/chats/{chat_id}", json={"title": "Headache notes"})
    assert renamed.json()["title"] == "Headache notes"
    client.post("/api/v1/auth/logout")
    client.post("/api/v1/auth/register", json={"name": "Ben", "email": "ben@test.local", "password": "securepass"})
    forbidden = client.get(f"/api/v1/chats/{chat_id}")
    assert forbidden.status_code == 404
    client.post("/api/v1/auth/logout")
    client.post("/api/v1/auth/login", json={"email": "asha@test.local", "password": "securepass"})
    deleted = client.delete(f"/api/v1/chats/{chat_id}")
    assert deleted.status_code == 200
    missing = client.get(f"/api/v1/chats/{chat_id}")
    assert missing.status_code == 404


def test_unauthenticated_chats(client):
    response = client.get("/api/v1/chats")
    assert response.status_code == 401
