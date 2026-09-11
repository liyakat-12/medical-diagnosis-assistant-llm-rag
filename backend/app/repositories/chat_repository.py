from __future__ import annotations

from app.connection.mongodb import get_db, oid, utcnow
from app.models.chat import CHATS, build_chat, serialize_chat


async def list_for_user(user_id: str, query: str | None = None) -> list[dict]:
    filt: dict = {"user_id": oid(user_id), "archived": {"$ne": True}}
    if query:
        filt["title"] = {"$regex": query, "$options": "i"}
    cursor = get_db()[CHATS].find(filt).sort("updated_at", -1)
    return [serialize_chat(doc) async for doc in cursor]


async def create(user_id: str, title: str = "New chat") -> dict:
    doc = build_chat(user_id, title, utcnow())
    result = await get_db()[CHATS].insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize_chat(doc)


async def get_owned(chat_id: str, user_id: str) -> dict | None:
    try:
        doc = await get_db()[CHATS].find_one({"_id": oid(chat_id), "user_id": oid(user_id)})
    except ValueError:
        return None
    return serialize_chat(doc) if doc else None


async def update_owned(chat_id: str, user_id: str, fields: dict) -> dict | None:
    fields = {k: v for k, v in fields.items() if v is not None}
    if fields:
        fields["updated_at"] = utcnow()
        await get_db()[CHATS].update_one(
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
    await get_db()[CHATS].update_one({"_id": oid(chat_id)}, update)


async def delete_owned(chat_id: str, user_id: str) -> bool:
    result = await get_db()[CHATS].delete_one({"_id": oid(chat_id), "user_id": oid(user_id)})
    return result.deleted_count == 1
