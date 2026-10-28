from __future__ import annotations

from datetime import datetime
from typing import Any

from app.connection.mongodb import as_id, oid

MESSAGES = "messages"


def build_message(
    *,
    chat_id: str,
    user_id: str,
    role: str,
    content: str,
    now: datetime,
    model: str | None = None,
    citations: list | None = None,
    triage: dict | None = None,
    possible_conditions: list | None = None,
    faithfulness: dict | None = None,
    recommendations: list | None = None,
    refused: bool = False,
    disclaimer: str | None = None,
    metadata: dict | None = None,
) -> dict[str, Any]:
    return {
        "chat_id": oid(chat_id),
        "user_id": oid(user_id),
        "role": role,
        "content": content,
        "created_at": now,
        "updated_at": now,
        "model": model,
        "citations": citations or [],
        "triage": triage,
        "possible_conditions": possible_conditions or [],
        "faithfulness": faithfulness,
        "recommendations": recommendations or [],
        "refused": refused,
        "disclaimer": disclaimer,
        "metadata": metadata or {},
    }


def serialize_message(doc: dict) -> dict:
    return {
        "id": as_id(doc["_id"]),
        "chat_id": as_id(doc["chat_id"]),
        "user_id": as_id(doc["user_id"]),
        "role": doc.get("role") or "assistant",
        "content": doc.get("content") or "",
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
        "model": None,
        "citations": doc.get("citations") or [],
        "triage": doc.get("triage"),
        "possible_conditions": doc.get("possible_conditions") or [],
        "faithfulness": doc.get("faithfulness"),
        "recommendations": doc.get("recommendations") or [],
        "refused": bool(doc.get("refused", False)),
        "disclaimer": doc.get("disclaimer"),
        "metadata": doc.get("metadata") or {},
    }
