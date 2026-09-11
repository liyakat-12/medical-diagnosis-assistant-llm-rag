from __future__ import annotations

from app.connection.mongodb import get_db
from app.models.chat import CHATS
from app.models.message import MESSAGES
from app.models.user import USERS


async def ensure_indexes() -> None:
    db = get_db()
    await db[USERS].create_index("email", unique=True)
    await db[CHATS].create_index([("user_id", 1), ("updated_at", -1)])
    await db[CHATS].create_index([("user_id", 1), ("last_message_at", -1)])
    await db[CHATS].create_index("user_id")
    await db[MESSAGES].create_index([("chat_id", 1), ("created_at", 1)])
    await db[MESSAGES].create_index("user_id")
    await db[MESSAGES].create_index("chat_id")
