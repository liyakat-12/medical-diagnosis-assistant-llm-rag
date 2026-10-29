from __future__ import annotations

from pydantic import BaseModel, Field


class LiveRetrievalRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    top_k: int | None = Field(default=None, ge=1, le=8)
