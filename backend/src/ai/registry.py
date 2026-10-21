from __future__ import annotations

from functools import lru_cache

from src import config
from src.ai.providers.groq import GroqProvider
from src.ai.providers.mock import MockProvider
from src.ai.providers.ollama import OllamaProvider
from src.ai.providers.openai import OpenAIProvider

_PROVIDERS = {
    "mock": MockProvider,
    "openai": OpenAIProvider,
    "groq": GroqProvider,
    "ollama": OllamaProvider,
}


def available_providers() -> list[str]:
    return sorted(_PROVIDERS)


@lru_cache(maxsize=8)
def get_provider(name: str | None = None):
    resolved = (name or config.resolve_llm_provider()).strip().lower()
    if resolved not in _PROVIDERS:
        raise ValueError(
            f"Unknown LLM_PROVIDER '{resolved}'. Use {', '.join(available_providers())}."
        )
    return _PROVIDERS[resolved]()
