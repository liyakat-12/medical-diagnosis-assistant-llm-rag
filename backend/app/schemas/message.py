from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

BodyRegionId = Literal[
    "head",
    "neck",
    "chest",
    "abdomen",
    "upper_back",
    "lower_back",
    "shoulder",
    "arm",
    "elbow",
    "wrist_hand",
    "hip",
    "thigh",
    "knee",
    "lower_leg",
    "ankle_foot",
    "back",
    "leg",
]


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    top_k: int | None = Field(default=None, ge=1, le=8)
    body_regions: list[BodyRegionId] = Field(default_factory=list, max_length=17)

    @field_validator("body_regions")
    @classmethod
    def dedupe_regions(cls, regions: list[str]) -> list[str]:
        return list(dict.fromkeys(regions))


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
