from __future__ import annotations

from collections.abc import Iterator

from src import config
from src.pipeline.rag_pipeline import iter_pipeline_stream, result_to_dict, run_pipeline

from app.repositories import chat_repository, message_repository
from app.services.chat_service import get_chat, make_title


async def list_messages(user_id: str, chat_id: str) -> list[dict]:
    await get_chat(user_id, chat_id)
    return await message_repository.list_for_chat(chat_id, user_id)


async def add_user_message(user_id: str, chat_id: str, content: str) -> dict:
    chat = await get_chat(user_id, chat_id)
    message = await message_repository.create_message(
        chat_id=chat_id,
        user_id=user_id,
        role="user",
        content=content,
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


def diagnose_sync(query: str, top_k: int | None = None, chat_history: list[dict] | None = None) -> dict:
    return result_to_dict(run_pipeline(query, top_k=top_k, chat_history=chat_history))


def stream_events(query: str, top_k: int | None = None, chat_history: list[dict] | None = None) -> Iterator[dict]:
    yield from iter_pipeline_stream(query, top_k=top_k, chat_history=chat_history)
