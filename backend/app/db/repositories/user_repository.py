from __future__ import annotations

from datetime import datetime

from app.db.mongodb import as_id, get_db, oid, utcnow


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


async def find_by_email(email: str) -> dict | None:
    return await get_db().users.find_one({"email": email})


async def find_by_id(user_id: str) -> dict | None:
    try:
        return await get_db().users.find_one({"_id": oid(user_id)})
    except ValueError:
        return None


async def create_user(name: str, email: str, password_hash: str) -> dict:
    now = utcnow()
    doc = {
        "name": name,
        "email": email,
        "password_hash": password_hash,
        "created_at": now,
        "updated_at": now,
        "last_login": None,
        "is_active": True,
        "medical_disclaimer_accepted": False,
    }
    result = await get_db().users.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def touch_login(user_id: str) -> None:
    await get_db().users.update_one(
        {"_id": oid(user_id)},
        {"$set": {"last_login": utcnow(), "updated_at": utcnow()}},
    )


async def update_user(user_id: str, fields: dict) -> dict | None:
    fields = {k: v for k, v in fields.items() if v is not None}
    if not fields:
        return await find_by_id(user_id)
    fields["updated_at"] = utcnow()
    await get_db().users.update_one({"_id": oid(user_id)}, {"$set": fields})
    return await find_by_id(user_id)
