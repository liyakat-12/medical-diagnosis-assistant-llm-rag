from __future__ import annotations

from app.core.security import hash_password, verify_password
from app.services.chat_service import make_title


def test_password_hash_roundtrip():
    digest = hash_password("demo1234")
    assert digest != "demo1234"
    assert verify_password("demo1234", digest)
    assert not verify_password("wrong", digest)


def test_make_title_shortens_symptom_text():
    title = make_title("I have been having a headache behind my eyes for two days.")
    assert "Headache" in title or "headache" in title.lower()
    assert len(title) <= 60
