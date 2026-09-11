from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    top_k: int | None = Field(default=None, ge=1, le=8)


class MessageResponse(BaseModel):
    id: str
    chat_id: str
    user_id: str
    role: str
    content: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model: str | None = None
    citations: list[dict[str, Any]] = []
    triage: dict[str, Any] | None = None
    possible_conditions: list[dict[str, Any]] = []
    faithfulness: dict[str, Any] | None = None
    recommendations: list[str] = []
    refused: bool = False
    disclaimer: str | None = None
    metadata: dict[str, Any] = {}
