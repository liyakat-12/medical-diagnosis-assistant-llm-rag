from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from src import config

from app.core.dependencies import get_current_user
from app.schemas.message import MessageResponse, SendMessageRequest
from app.services import message_service

logger = logging.getLogger("mediassist.messages")
STREAM_FAILURE_ANSWER = "I could not finish this lookup. Please try again. This is not a diagnosis."

router = APIRouter(prefix="/chats", tags=["messages"])


@router.get("/{chat_id}/messages", response_model=list[MessageResponse])
async def list_messages(chat_id: str, user: dict = Depends(get_current_user)) -> list[MessageResponse]:
    return [MessageResponse(**item) for item in await message_service.list_messages(user["id"], chat_id)]


@router.post("/{chat_id}/messages", response_model=list[MessageResponse])
async def send_message(
    chat_id: str,
    payload: SendMessageRequest,
    user: dict = Depends(get_current_user),
) -> list[MessageResponse]:
    user_msg = await message_service.add_user_message(user["id"], chat_id, payload.content.strip())
    result = await asyncio.to_thread(message_service.diagnose_sync, payload.content.strip(), payload.top_k)
    assistant = await message_service.add_assistant_message(user["id"], chat_id, result)
    return [MessageResponse(**user_msg), MessageResponse(**assistant)]


@router.post("/{chat_id}/messages/stream")
async def stream_message(
    chat_id: str,
    payload: SendMessageRequest,
    user: dict = Depends(get_current_user),
):
    await message_service.add_user_message(user["id"], chat_id, payload.content.strip())

    async def event_source():
        iterator = message_service.stream_events(payload.content.strip(), payload.top_k)
        try:
            while True:
                try:
                    event = await asyncio.to_thread(next, iterator, None)
                except Exception:
                    logger.exception("RAG stream failed for chat %s", chat_id)
                    error_result = {
                        "query": payload.content.strip(),
                        "refused": False,
                        "answer": STREAM_FAILURE_ANSWER,
                        "citations": [],
                        "recommendations": ["Try sending the same question again."],
                        "disclaimer": config.DISCLAIMER,
                        "possible_conditions": [],
                        "triage": None,
                        "faithfulness": None,
                        "provider": config.resolve_llm_provider(),
                    }
                    assistant = await message_service.add_assistant_message(user["id"], chat_id, error_result)
                    yield f"data: {json.dumps({'type': 'token', 'content': STREAM_FAILURE_ANSWER}, default=str)}\n\n"
                    yield f"data: {json.dumps({'type': 'done', 'result': error_result, 'message': assistant}, default=str)}\n\n"
                    return
                if event is None:
                    break
                if event.get("type") == "done":
                    final = event.get("result") or {}
                    assistant = await message_service.add_assistant_message(user["id"], chat_id, final)
                    event = {**event, "message": assistant}
                yield f"data: {json.dumps(event, default=str)}\n\n"
        except Exception:
            logger.exception("SSE writer failed for chat %s", chat_id)

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
