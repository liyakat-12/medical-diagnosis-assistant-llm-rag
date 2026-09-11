from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CreateChatRequest(BaseModel):
    title: str | None = Field(default=None, max_length=80)


class UpdateChatRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=80)
    archived: bool | None = None


class ChatResponse(BaseModel):
    id: str
    user_id: str
    title: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_message_at: datetime | None = None
    message_count: int = 0
    archived: bool = False
