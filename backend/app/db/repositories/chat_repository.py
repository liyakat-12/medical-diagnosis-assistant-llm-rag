from __future__ import annotations

from datetime import datetime

from bson import ObjectId

from app.db.mongodb import as_id, get_db, oid, utcnow


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


async def list_for_user(user_id: str, query: str | None = None) -> list[dict]:
    filt: dict = {"user_id": oid(user_id), "archived": {"$ne": True}}
    if query:
        filt["title"] = {"$regex": query, "$options": "i"}
    cursor = get_db().chats.find(filt).sort("updated_at", -1)
    return [serialize_chat(doc) async for doc in cursor]


async def create(user_id: str, title: str = "New chat") -> dict:
    now = utcnow()
    doc = {
        "user_id": oid(user_id),
        "title": title,
        "created_at": now,
        "updated_at": now,
        "last_message_at": None,
        "message_count": 0,
        "archived": False,
        "metadata": {},
    }
    result = await get_db().chats.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize_chat(doc)


async def get_owned(chat_id: str, user_id: str) -> dict | None:
    try:
        doc = await get_db().chats.find_one({"_id": oid(chat_id), "user_id": oid(user_id)})
    except ValueError:
        return None
    return serialize_chat(doc) if doc else None


async def update_owned(chat_id: str, user_id: str, fields: dict) -> dict | None:
    fields = {k: v for k, v in fields.items() if v is not None}
    if fields:
        fields["updated_at"] = utcnow()
        await get_db().chats.update_one(
            {"_id": oid(chat_id), "user_id": oid(user_id)},
            {"$set": fields},
        )
    return await get_owned(chat_id, user_id)


async def bump_after_message(chat_id: str, title: str | None = None) -> None:
    now = utcnow()
    update: dict = {
        "$set": {"updated_at": now, "last_message_at": now},
        "$inc": {"message_count": 1},
    }
    if title:
        update["$set"]["title"] = title
    await get_db().chats.update_one({"_id": oid(chat_id)}, update)


async def delete_owned(chat_id: str, user_id: str) -> bool:
    result = await get_db().chats.delete_one({"_id": oid(chat_id), "user_id": oid(user_id)})
    return result.deleted_count == 1
