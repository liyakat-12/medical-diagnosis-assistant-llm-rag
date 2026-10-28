from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol


class BaseAIProvider(Protocol):
    name: str

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        grounded: bool = True,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> str: ...

    def stream(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        grounded: bool = True,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str] | None: ...
