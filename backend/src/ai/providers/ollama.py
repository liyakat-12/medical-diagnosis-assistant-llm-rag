from __future__ import annotations

from collections.abc import Iterator

import requests

from src import config
from src.ai.base import BaseAIProvider


class OllamaProvider:
    name = "ollama"

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        grounded: bool = True,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> str:
        del grounded, max_tokens
        payload = {
            "model": model or config.OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
        }
        resp = requests.post(
            f"{config.OLLAMA_BASE_URL}/api/chat",
            json=payload,
            timeout=max(45.0, float(config.LLM_TIMEOUT_SECONDS)),
        )
        resp.raise_for_status()
        return (resp.json().get("message") or {}).get("content", "").strip()

    def stream(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        grounded: bool = True,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> Iterator[str]:
        del grounded, max_tokens
        payload = {
            "model": model or config.OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": True,
        }
        with requests.post(
            f"{config.OLLAMA_BASE_URL}/api/chat",
            json=payload,
            timeout=45,
            stream=True,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                import json

                data = json.loads(line)
                content = (data.get("message") or {}).get("content") or ""
                if content:
                    yield content
