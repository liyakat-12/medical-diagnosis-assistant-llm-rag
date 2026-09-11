from __future__ import annotations

from datetime import datetime

from app.connection.mongodb import as_id, oid

CHATS = "chats"


def build_chat(user_id: str, title: str, now: datetime) -> dict:
    return {
        "user_id": oid(user_id),
        "title": title,
        "created_at": now,
        "updated_at": now,
        "last_message_at": None,
        "message_count": 0,
        "archived": False,
        "metadata": {},
    }


def serialize_chat(doc: dict) -> dict:
    return {
        "id": as_id(doc["_id"]),
        "user_id": as_id(doc["user_id"]),
        "title": doc.get("title") or "New chat",
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
        "last_message_at": doc.get("last_message_at"),
        "message_count": int(doc.get("message_count") or 0),
        "archived": bool(doc.get("archived", False)),
    }
