from __future__ import annotations

import re
from collections.abc import Iterator

from src import config
from src.pipeline.rag_pipeline import iter_pipeline_stream, result_to_dict, run_pipeline

from app.repositories import chat_repository, message_repository
from app.services.chat_service import get_chat, make_title

_REGION_WORDS = {
    "head": "head",
    "neck": "neck",
    "chest": "chest",
    "abdomen": "abdomen",
    "upper_back": "upper back",
    "lower_back": "lower back",
    "shoulder": "shoulder",
    "arm": "arm",
    "elbow": "elbow",
    "wrist_hand": "wrist",
    "hip": "hip",
    "thigh": "thigh",
    "knee": "knee",
    "lower_leg": "lower leg",
    "ankle_foot": "ankle",
    "back": "back",
    "leg": "leg",
}


def retrieval_query(content: str, body_regions: list[str] | None = None) -> str:
    """Add a body-map location only when the typed message does not already name it."""
    text = (content or "").strip()
    missing: list[str] = []
    for region in body_regions or []:
        phrase = _REGION_WORDS.get(str(region))
        if not phrase or re.search(rf"\b{re.escape(phrase)}\b", text, re.IGNORECASE):
            continue
        missing.append(phrase)
    if not missing:
        return text
    return f"{text}\nBody map location: {', '.join(missing)} discomfort."


async def list_messages(user_id: str, chat_id: str) -> list[dict]:
    await get_chat(user_id, chat_id)
    return await message_repository.list_for_chat(chat_id, user_id)


async def add_user_message(user_id: str, chat_id: str, content: str, body_regions: list[str] | None = None) -> dict:
    chat = await get_chat(user_id, chat_id)
    message = await message_repository.create_message(
        chat_id=chat_id,
        user_id=user_id,
        role="user",
        content=content,
        metadata={"body_regions": list(body_regions)} if body_regions else None,
    )
    title = None
    if chat["title"] in {"New chat", ""} and chat["message_count"] == 0:
        title = make_title(content)
    await chat_repository.bump_after_message(chat_id, title)
    return message


async def add_assistant_message(user_id: str, chat_id: str, result: dict) -> dict:
    message = await message_repository.create_message(
        chat_id=chat_id,
        user_id=user_id,
        role="assistant",
        content=result.get("answer") or "",
        model=None,
        citations=result.get("citations") or [],
        triage=result.get("triage"),
        possible_conditions=result.get("possible_conditions") or [],
        faithfulness=result.get("faithfulness"),
        recommendations=result.get("recommendations") or [],
        refused=bool(result.get("refused")),
        disclaimer=result.get("disclaimer") or config.DISCLAIMER,
        metadata={
            "query": result.get("query"),
            "evidence_origin": result.get("evidence_origin") or "none",
            "question_type": result.get("question_type") or "",
            "personal_context": bool(result.get("personal_context")),
        },
    )
    await chat_repository.bump_after_message(chat_id)
    return message


def history_for_pipeline(messages: list[dict]) -> list[dict]:
    rows: list[dict] = []
    window = max(2, int(config.CHAT_HISTORY_WINDOW))
    for item in messages[-window:]:
        rows.append(
            {
                "role": item.get("role"),
                "content": item.get("content") or "",
                "possible_conditions": item.get("possible_conditions") or [],
                "triage": item.get("triage"),
            }
        )
    return rows


async def recent_history(user_id: str, chat_id: str, limit: int | None = None) -> list[dict]:
    if limit is None:
        limit = max(2, int(config.CHAT_HISTORY_WINDOW))
    await get_chat(user_id, chat_id)
    messages = await message_repository.list_recent_for_chat(chat_id, user_id, limit)
    return history_for_pipeline(messages)


def diagnose_sync(
    query: str,
    top_k: int | None = None,
    chat_history: list[dict] | None = None,
    body_regions: list[str] | None = None,
) -> dict:
    return result_to_dict(run_pipeline(retrieval_query(query, body_regions), top_k=top_k, chat_history=chat_history))


def stream_events(
    query: str,
    top_k: int | None = None,
    chat_history: list[dict] | None = None,
    body_regions: list[str] | None = None,
) -> Iterator[dict]:
    yield from iter_pipeline_stream(retrieval_query(query, body_regions), top_k=top_k, chat_history=chat_history)
