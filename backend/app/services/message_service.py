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
        model=result.get("provider") or config.resolve_llm_provider(),
        citations=result.get("citations") or [],
        triage=result.get("triage"),
        possible_conditions=result.get("possible_conditions") or [],
        faithfulness=result.get("faithfulness"),
        recommendations=result.get("recommendations") or [],
        refused=bool(result.get("refused")),
        disclaimer=result.get("disclaimer") or config.DISCLAIMER,
        metadata={"query": result.get("query")},
    )
    await chat_repository.bump_after_message(chat_id)
    return message


def history_for_pipeline(messages: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for item in messages[-10:]:
        rows.append(
            {
                "role": item.get("role"),
                "content": item.get("content") or "",
                "possible_conditions": item.get("possible_conditions") or [],
                "triage": item.get("triage"),
            }
        )
    return rows


async def recent_history(user_id: str, chat_id: str, limit: int = 10) -> list[dict]:
    messages = await list_messages(user_id, chat_id)
    return history_for_pipeline(messages[-limit:])


def diagnose_sync(query: str, top_k: int | None = None, chat_history: list[dict] | None = None) -> dict:
    return result_to_dict(run_pipeline(query, top_k=top_k, chat_history=chat_history))


def stream_events(query: str, top_k: int | None = None, chat_history: list[dict] | None = None) -> Iterator[dict]:
    yield from iter_pipeline_stream(query, top_k=top_k, chat_history=chat_history)
