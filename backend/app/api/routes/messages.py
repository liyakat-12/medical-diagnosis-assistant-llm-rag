from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.core.dependencies import get_current_user
from app.schemas.message import MessageResponse, SendMessageRequest
from app.services import message_service

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
        final = None
        iterator = message_service.stream_events(payload.content.strip(), payload.top_k)
        while True:
            event = await asyncio.to_thread(next, iterator, None)
            if event is None:
                break
            if event.get("type") == "done":
                final = event.get("result") or {}
                assistant = await message_service.add_assistant_message(user["id"], chat_id, final)
                event = {**event, "message": assistant}
            yield f"data: {json.dumps(event, default=str)}\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")
