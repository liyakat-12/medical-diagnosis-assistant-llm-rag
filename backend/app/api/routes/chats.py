from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_user
from app.schemas.chat import ChatResponse, CreateChatRequest, UpdateChatRequest
from app.services import chat_service

router = APIRouter(prefix="/chats", tags=["chats"])


@router.get("", response_model=list[ChatResponse])
async def list_chats(
    q: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
) -> list[ChatResponse]:
    return [ChatResponse(**item) for item in await chat_service.list_chats(user["id"], q)]


@router.post("", response_model=ChatResponse)
async def create_chat(
    payload: CreateChatRequest | None = None,
    user: dict = Depends(get_current_user),
) -> ChatResponse:
    title = payload.title if payload else None
    return ChatResponse(**await chat_service.create_chat(user["id"], title))


@router.get("/{chat_id}", response_model=ChatResponse)
async def read_chat(chat_id: str, user: dict = Depends(get_current_user)) -> ChatResponse:
    return ChatResponse(**await chat_service.get_chat(user["id"], chat_id))


@router.patch("/{chat_id}", response_model=ChatResponse)
async def update_chat(
    chat_id: str,
    payload: UpdateChatRequest,
    user: dict = Depends(get_current_user),
) -> ChatResponse:
    return ChatResponse(**await chat_service.update_chat(user["id"], chat_id, payload.model_dump(exclude_unset=True)))


@router.delete("/{chat_id}")
async def delete_chat(chat_id: str, user: dict = Depends(get_current_user)) -> dict:
    await chat_service.delete_chat(user["id"], chat_id)
    return {"ok": True}
