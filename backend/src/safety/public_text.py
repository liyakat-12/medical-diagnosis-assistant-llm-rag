"""Strip vendor/model details from anything that can reach a browser."""
from __future__ import annotations

import re

PUBLIC_ASSISTANT_FAILURE = "I could not finish this reply. Please try again in a moment."
PUBLIC_LOOKUP_FAILURE = "I could not finish this lookup. Please try again. This is not a diagnosis."
KB_MISS_STATUS = "Local notes had no close match. Checking additional medical information..."

_VENDOR_RE = re.compile(
    r"(?<![a-z0-9])(groq|openai|ollama|chatgpt|anthropic|gemini|huggingface|"
    r"gpt-oss(?:-\d+b)?|gpt-4o(?:-mini)?|llama[\w.-]*|mixtral|"
    r"console\.groq\.com|api\.groq\.com|api\.openai\.com)(?![a-z0-9])",
    re.IGNORECASE,
)
_TRACE_RE = re.compile(r"traceback \(most recent call last\)|file \".+\.py\", line \d+", re.IGNORECASE)
_INTERNAL_KEYS = {"provider", "llm_provider", "effective_llm_provider", "providers"}


def contains_provider_leak(text: str | None) -> bool:
    raw = text or ""
    return bool(_VENDOR_RE.search(raw) or _TRACE_RE.search(raw))


def sanitize_status(text: str | None) -> str:
    value = (text or "").strip()
    if not value or contains_provider_leak(value):
        return "MediAssist is preparing a reply..."
    return value


def sanitize_error(text: str | None, fallback: str = PUBLIC_ASSISTANT_FAILURE) -> str:
    value = (text or "").strip()
    if not value or contains_provider_leak(value):
        return fallback
    return value


def public_chat_payload(payload: dict) -> dict:
    """Drop vendor fields from SSE/API result objects."""
    cleaned = {key: value for key, value in (payload or {}).items() if key not in _INTERNAL_KEYS}
    if "model" in cleaned:
        cleaned["model"] = None
    answer = cleaned.get("answer")
    if isinstance(answer, str) and contains_provider_leak(answer):
        cleaned["answer"] = PUBLIC_ASSISTANT_FAILURE
    status = cleaned.get("content")
    if cleaned.get("type") == "status" and isinstance(status, str):
        cleaned["content"] = sanitize_status(status)
    return cleaned
