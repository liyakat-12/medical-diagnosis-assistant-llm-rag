from __future__ import annotations

from collections.abc import Iterator

from src import config
from src.ai.base import BaseAIProvider


class OpenAIProvider:
    name = "openai"

    def _client(self):
        from openai import OpenAI

        if config._looks_like_placeholder(config.OPENAI_API_KEY):
            raise RuntimeError("OPENAI_API_KEY is not set.")
        return OpenAI(api_key=config.OPENAI_API_KEY)

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        grounded: bool = True,
        model: str | None = None,
    ) -> str:
        del grounded
        response = self._client().chat.completions.create(
            model=model or config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=280,
        )
        return (response.choices[0].message.content or "").strip()

    def stream(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        grounded: bool = True,
        model: str | None = None,
    ) -> Iterator[str]:
        del grounded
        stream = self._client().chat.completions.create(
            model=model or config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=280,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta
