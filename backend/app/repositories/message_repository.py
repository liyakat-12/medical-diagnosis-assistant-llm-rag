from __future__ import annotations

from app.connection.mongodb import get_db, oid, utcnow
from app.models.message import MESSAGES, build_message, serialize_message


async def list_for_chat(chat_id: str, user_id: str) -> list[dict]:
    cursor = get_db()[MESSAGES].find({"chat_id": oid(chat_id), "user_id": oid(user_id)}).sort("created_at", 1)
    return [serialize_message(doc) async for doc in cursor]


async def list_recent_for_chat(chat_id: str, user_id: str, limit: int = 10) -> list[dict]:
    cursor = (
        get_db()[MESSAGES]
        .find({"chat_id": oid(chat_id), "user_id": oid(user_id)})
        .sort("created_at", -1)
        .limit(max(1, int(limit)))
    )
    rows = [serialize_message(doc) async for doc in cursor]
    rows.reverse()
    return rows


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
    doc = build_message(
        chat_id=chat_id,
        user_id=user_id,
        role=role,
        content=content,
        now=utcnow(),
        model=model,
        citations=citations,
        triage=triage,
        possible_conditions=possible_conditions,
        faithfulness=faithfulness,
        recommendations=recommendations,
        refused=refused,
        disclaimer=disclaimer,
        metadata=metadata,
    )
    result = await get_db()[MESSAGES].insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize_message(doc)


async def delete_for_chat(chat_id: str, user_id: str) -> None:
    await get_db()[MESSAGES].delete_many({"chat_id": oid(chat_id), "user_id": oid(user_id)})
