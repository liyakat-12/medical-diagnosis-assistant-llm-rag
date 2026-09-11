"""Persist per-user chat history for the website."""
from __future__ import annotations

import json
import secrets
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, status

from src import config

_LOCK = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _path() -> Path:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    return config.CHATS_PATH


def _load() -> dict:
    path = _path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: dict) -> None:
    _path().write_text(json.dumps(data, indent=2), encoding="utf-8")


def _user_chats(data: dict, email: str) -> list[dict]:
    chats = data.setdefault(email, [])
    if not isinstance(chats, list):
        chats = []
        data[email] = chats
    return chats


def _summary(chat: dict) -> dict:
    return {
        "id": chat["id"],
        "title": chat.get("title") or "New chat",
        "created_at": chat.get("created_at") or "",
        "updated_at": chat.get("updated_at") or "",
    }


def list_chats(email: str) -> list[dict]:
    with _LOCK:
        chats = list(_load().get(email, []))
    chats.sort(key=lambda item: item.get("updated_at") or "", reverse=True)
    return [_summary(item) for item in chats]


def create_chat(email: str) -> dict:
    chat = {
        "id": secrets.token_hex(8),
        "title": "New chat",
        "created_at": _now(),
        "updated_at": _now(),
        "messages": [],
    }
    with _LOCK:
        data = _load()
        _user_chats(data, email).insert(0, chat)
        _save(data)
    return chat


def get_chat(email: str, chat_id: str) -> dict:
    with _LOCK:
        for chat in _load().get(email, []):
            if chat.get("id") == chat_id:
                return chat
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat not found.")


def append_turn(email: str, chat_id: str, query: str, result: dict) -> dict:
    with _LOCK:
        data = _load()
        chats = _user_chats(data, email)
        chat = next((item for item in chats if item.get("id") == chat_id), None)
        if not chat:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat not found.")
        stamp = _now()
        chat.setdefault("messages", []).append(
            {"role": "user", "content": query, "created_at": stamp, "result": None}
        )
        chat["messages"].append(
            {
                "role": "assistant",
                "content": result.get("answer") or "",
                "created_at": stamp,
                "result": result,
            }
        )
        if (chat.get("title") or "New chat") == "New chat":
            title = " ".join(query.split())
            chat["title"] = title[:48] + ("…" if len(title) > 48 else "")
        chat["updated_at"] = stamp
        _save(data)
        return chat
