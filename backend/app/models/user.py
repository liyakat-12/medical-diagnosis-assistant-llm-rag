from __future__ import annotations

from datetime import datetime

from app.connection.mongodb import as_id

USERS = "users"


def build_user(name: str, email: str, password_hash: str, now: datetime) -> dict:
    return {
        "name": name,
        "email": email,
        "password_hash": password_hash,
        "created_at": now,
        "updated_at": now,
        "last_login": None,
        "is_active": True,
        "medical_disclaimer_accepted": False,
    }


def serialize_user(doc: dict) -> dict:
    return {
        "id": as_id(doc["_id"]),
        "name": doc.get("name") or "",
        "email": doc.get("email") or "",
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
        "last_login": doc.get("last_login"),
        "is_active": bool(doc.get("is_active", True)),
        "medical_disclaimer_accepted": bool(doc.get("medical_disclaimer_accepted", False)),
    }
