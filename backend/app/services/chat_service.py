from __future__ import annotations

import re

from app.core.exceptions import not_found
from app.repositories import chat_repository, message_repository


def make_title(text: str) -> str:
    cleaned = " ".join((text or "").split())
    lowered = cleaned.lower()
    for prefix in ("i have been having ", "i have been ", "i've been ", "i have a ", "i have ", "i'm ", "i am ", "my "):
        if lowered.startswith(prefix):
            cleaned = cleaned[len(prefix) :].strip()
            break
    if not cleaned:
        return "New chat"
    cleaned = cleaned[0].upper() + cleaned[1:]
    cleaned = re.sub(r"[.?!]+$", "", cleaned)
    if len(cleaned) > 52:
        cleaned = cleaned[:52].rsplit(" ", 1)[0] + "…"
    return cleaned or "New chat"


async def list_chats(user_id: str, query: str | None = None) -> list[dict]:
    return await chat_repository.list_for_user(user_id, query)


async def create_chat(user_id: str, title: str | None = None) -> dict:
    return await chat_repository.create(user_id, title or "New chat")


async def get_chat(user_id: str, chat_id: str) -> dict:
    chat = await chat_repository.get_owned(chat_id, user_id)
    if not chat:
        raise not_found("Chat not found.")
    return chat


async def update_chat(user_id: str, chat_id: str, fields: dict) -> dict:
    chat = await chat_repository.update_owned(chat_id, user_id, fields)
    if not chat:
        raise not_found("Chat not found.")
    return chat


async def delete_chat(user_id: str, chat_id: str) -> None:
    owned = await chat_repository.get_owned(chat_id, user_id)
    if not owned:
        raise not_found("Chat not found.")
    await message_repository.delete_for_chat(chat_id, user_id)
    await chat_repository.delete_owned(chat_id, user_id)
