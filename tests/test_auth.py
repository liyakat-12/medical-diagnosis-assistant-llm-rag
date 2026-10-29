from __future__ import annotations

import anyio

from app.core.security import hash_password, verify_password
from app.services.chat_service import make_title


def test_password_hash_roundtrip():
    digest = hash_password("demo1234")
    assert digest != "demo1234"
    assert verify_password("demo1234", digest)
    assert not verify_password("wrong", digest)


def test_seed_demo_user_in_production(client, monkeypatch):
    from app.core import config
    from app.repositories import user_repository
    from app.services.auth_service import seed_demo_user

    monkeypatch.setattr(config, "is_production", lambda: True)
    monkeypatch.setattr(config, "DEMO_EMAIL", "demo@clinic.local")
    monkeypatch.setattr(config, "DEMO_PASSWORD", "demo123")
    monkeypatch.setattr(config, "DEMO_NAME", "Demo Patient")

    async def break_and_repair() -> None:
        existing = await user_repository.find_by_email("demo@clinic.local")
        assert existing is not None
        await user_repository.update_user(
            str(existing["_id"]),
            {"password_hash": hash_password("wrong-old-password")},
        )
        await seed_demo_user()

    anyio.run(break_and_repair)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@clinic.local", "password": "demo123"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["email"] == "demo@clinic.local"


def test_make_title_shortens_symptom_text():
    title = make_title("I have been having a headache behind my eyes for two days.")
    assert "Headache" in title or "headache" in title.lower()
    assert len(title) <= 60
