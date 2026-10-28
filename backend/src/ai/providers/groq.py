from __future__ import annotations

import logging
from collections.abc import Iterator

from src import config
from src.ai.base import BaseAIProvider

logger = logging.getLogger("mediassist.groq")


class GroqProvider:
    name = "groq"

    def __init__(self) -> None:
        self._cached_client = None

    def _client(self):
        from openai import OpenAI

        if config._looks_like_placeholder(config.GROQ_API_KEY):
            raise RuntimeError("GROQ_API_KEY is not set.")
        if self._cached_client is None:
            self._cached_client = OpenAI(
                api_key=config.GROQ_API_KEY,
                base_url=config.GROQ_BASE_URL,
                timeout=config.LLM_TIMEOUT_SECONDS,
                max_retries=1,
            )
        return self._cached_client

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        grounded: bool = True,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> str:
        del grounded
        try:
            response = self._client().chat.completions.create(
                model=model or config.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=max_tokens or config.LLM_MEDICAL_MAX_TOKENS,
            )
        except Exception as exc:
            logger.warning("LLM generate failed: %s", type(exc).__name__)
            raise
        return (response.choices[0].message.content or "").strip()

    def stream(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        grounded: bool = True,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> Iterator[str]:
        del grounded
        try:
            stream = self._client().chat.completions.create(
                model=model or config.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=max_tokens or config.LLM_MEDICAL_MAX_TOKENS,
                stream=True,
            )
        except Exception as exc:
            logger.warning("LLM stream failed: %s", type(exc).__name__)
            raise
        for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta
