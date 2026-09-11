from __future__ import annotations

from app.connection.mongodb import get_db, oid, utcnow
from app.models.user import USERS, build_user, serialize_user


async def find_by_email(email: str) -> dict | None:
    return await get_db()[USERS].find_one({"email": email})


async def find_by_id(user_id: str) -> dict | None:
    try:
        return await get_db()[USERS].find_one({"_id": oid(user_id)})
    except ValueError:
        return None


async def create_user(name: str, email: str, password_hash: str) -> dict:
    doc = build_user(name, email, password_hash, utcnow())
    result = await get_db()[USERS].insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def touch_login(user_id: str) -> None:
    await get_db()[USERS].update_one(
        {"_id": oid(user_id)},
        {"$set": {"last_login": utcnow(), "updated_at": utcnow()}},
    )


async def update_user(user_id: str, fields: dict) -> dict | None:
    fields = {k: v for k, v in fields.items() if v is not None}
    if not fields:
        return await find_by_id(user_id)
    fields["updated_at"] = utcnow()
    await get_db()[USERS].update_one({"_id": oid(user_id)}, {"$set": fields})
    return await find_by_id(user_id)
