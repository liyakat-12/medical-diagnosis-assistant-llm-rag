from __future__ import annotations

from src.api.auth import authenticate, create_session, seed_demo_user, user_from_token


def test_demo_account_logs_in(tmp_path, monkeypatch):
    monkeypatch.setattr("src.config.USERS_PATH", tmp_path / "users.json")
    monkeypatch.setattr("src.config.DATA_DIR", tmp_path)
    seed_demo_user()
    user = authenticate("demo@clinic.local", "demo123")
    assert user is not None
    assert user["email"] == "demo@clinic.local"
    assert authenticate("demo@clinic.local", "wrong-password") is None


def test_session_token_roundtrip():
    token = create_session({"name": "Asha", "email": "asha@test.local"})
    user = user_from_token(token)
    assert user["name"] == "Asha"
    assert user_from_token("not-a-real-token") is None
