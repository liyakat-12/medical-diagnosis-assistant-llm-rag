from __future__ import annotations

from app.db.mongodb import as_id, get_db, oid, utcnow


def serialize_message(doc: dict) -> dict:
    return {
        "id": as_id(doc["_id"]),
        "chat_id": as_id(doc["chat_id"]),
        "user_id": as_id(doc["user_id"]),
        "role": doc.get("role") or "assistant",
        "content": doc.get("content") or "",
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
        "model": doc.get("model"),
        "citations": doc.get("citations") or [],
        "triage": doc.get("triage"),
        "possible_conditions": doc.get("possible_conditions") or [],
        "faithfulness": doc.get("faithfulness"),
        "recommendations": doc.get("recommendations") or [],
        "refused": bool(doc.get("refused", False)),
        "disclaimer": doc.get("disclaimer"),
        "metadata": doc.get("metadata") or {},
    }


async def list_for_chat(chat_id: str, user_id: str) -> list[dict]:
    cursor = get_db().messages.find({"chat_id": oid(chat_id), "user_id": oid(user_id)}).sort("created_at", 1)
    return [serialize_message(doc) async for doc in cursor]


async def create_message(
    *,
    chat_id: str,
    user_id: str,
    role: str,
    content: str,
    model: str | None = None,
    citations: list | None = None,
    triage: dict | None = None,
    possible_conditions: list | None = None,
    faithfulness: dict | None = None,
    recommendations: list | None = None,
    refused: bool = False,
    disclaimer: str | None = None,
    metadata: dict | None = None,
) -> dict:
    now = utcnow()
    doc = {
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
    result = await get_db().messages.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize_message(doc)


async def delete_for_chat(chat_id: str, user_id: str) -> None:
    await get_db().messages.delete_many({"chat_id": oid(chat_id), "user_id": oid(user_id)})
