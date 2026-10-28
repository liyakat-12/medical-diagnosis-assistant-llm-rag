from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from src import config
from src.safety.public_text import PUBLIC_LOOKUP_FAILURE, public_chat_payload, sanitize_status

from app.core.dependencies import get_current_user
from app.schemas.message import MessageResponse, SendMessageRequest
from app.services import message_service

logger = logging.getLogger("mediassist.messages")
STREAM_FAILURE_ANSWER = PUBLIC_LOOKUP_FAILURE

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
    history = await message_service.recent_history(user["id"], chat_id)
    user_msg = await message_service.add_user_message(user["id"], chat_id, payload.content.strip())
    result = await asyncio.to_thread(
        message_service.diagnose_sync,
        payload.content.strip(),
        payload.top_k,
        chat_history=history,
    )
    assistant = await message_service.add_assistant_message(user["id"], chat_id, result)
    return [MessageResponse(**user_msg), MessageResponse(**assistant)]


@router.post("/{chat_id}/messages/stream")
async def stream_message(
    chat_id: str,
    payload: SendMessageRequest,
    user: dict = Depends(get_current_user),
):
    history = await message_service.recent_history(user["id"], chat_id)
    await message_service.add_user_message(user["id"], chat_id, payload.content.strip())

    async def event_source():
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        done_marker = object()

        def produce() -> None:
            try:
                for event in message_service.stream_events(
                    payload.content.strip(), payload.top_k, chat_history=history
                ):
                    asyncio.run_coroutine_threadsafe(queue.put(event), loop).result()
                asyncio.run_coroutine_threadsafe(queue.put(done_marker), loop).result()
            except Exception as exc:
                asyncio.run_coroutine_threadsafe(queue.put(exc), loop).result()

        producer = asyncio.create_task(asyncio.to_thread(produce))
        try:
            while True:
                item = await queue.get()
                if item is done_marker:
                    break
                if isinstance(item, Exception):
                    logger.error("Chat stream failed for chat %s: %s", chat_id, type(item).__name__, exc_info=item)
                    error_result = public_chat_payload(
                        {
                            "query": payload.content.strip(),
                            "refused": False,
                            "answer": STREAM_FAILURE_ANSWER,
                            "citations": [],
                            "recommendations": ["Try sending the same question again."],
                            "disclaimer": config.DISCLAIMER,
                            "possible_conditions": [],
                            "triage": None,
                            "faithfulness": None,
                        }
                    )
                    assistant = await message_service.add_assistant_message(user["id"], chat_id, error_result)
                    yield f"data: {json.dumps({'type': 'token', 'content': STREAM_FAILURE_ANSWER}, default=str)}\n\n"
                    yield f"data: {json.dumps({'type': 'done', 'result': error_result, 'message': assistant}, default=str)}\n\n"
                    return
                event = item
                if event.get("type") == "status":
                    event = {**event, "content": sanitize_status(event.get("content"))}
                if event.get("type") == "done":
                    final = public_chat_payload(event.get("result") or {})
                    assistant = await message_service.add_assistant_message(user["id"], chat_id, final)
                    event = {**event, "result": final, "message": assistant}
                yield f"data: {json.dumps(event, default=str)}\n\n"
        except Exception:
            logger.exception("SSE writer failed for chat %s", chat_id)
        finally:
            if not producer.done():
                producer.cancel()
            try:
                await producer
            except (asyncio.CancelledError, Exception):
                pass

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
