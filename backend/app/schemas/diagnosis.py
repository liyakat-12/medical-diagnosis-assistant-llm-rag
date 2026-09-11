from __future__ import annotations

from pydantic import BaseModel, Field


class DiagnoseRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    top_k: int | None = Field(default=None, ge=1, le=8)
