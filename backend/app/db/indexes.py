from __future__ import annotations

from app.db.mongodb import get_db


async def ensure_indexes() -> None:
    db = get_db()
    await db.users.create_index("email", unique=True)
    await db.chats.create_index([("user_id", 1), ("updated_at", -1)])
    await db.chats.create_index([("user_id", 1), ("last_message_at", -1)])
    await db.chats.create_index("user_id")
    await db.messages.create_index([("chat_id", 1), ("created_at", 1)])
    await db.messages.create_index("user_id")
    await db.messages.create_index("chat_id")
