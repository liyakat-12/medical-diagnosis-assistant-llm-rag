"""
LLM generation wrapper.

Provides one function, generate(), that hides whether we're calling the
OpenAI API or a local Ollama server, so the pipeline code never branches
on provider.
"""
from __future__ import annotations

from src import config

SYSTEM_PROMPT = """You are a careful medical information assistant. You help users \
understand possible causes of symptoms they describe, using ONLY the reference \
context provided to you below. You are not a doctor and must never claim to be one.

Rules you must follow strictly:
1. Only state a possible condition if it is supported by the provided context. \
Every condition you mention must be followed by a citation in the form (Source: <title>).
2. If the context does not support a confident answer, say so plainly instead of guessing.
3. Never provide a specific drug name, dose, or prescription. If asked, refuse and \
recommend consulting a doctor or pharmacist.
4. Never claim certainty. Use language like "may be", "is commonly associated with", \
"one possible explanation is".
5. Always keep your answer concise: a short list of 2-4 possible conditions maximum, \
each with a one-sentence rationale and its citation.
6. End every answer with a one-line reminder that this is not a diagnosis and a \
professional should be consulted.
"""

NO_RAG_SYSTEM_PROMPT = """You are a medical assistant chatbot. Answer the user's \
question about their symptoms as helpfully as you can, in a short, clear list of \
possible conditions.
"""


def _build_user_prompt(query: str, context_blocks: list[str]) -> str:
    if not context_blocks:
        return f"User symptom description: {query}\n\n(No reference context was retrieved.)"
    context = "\n\n".join(context_blocks)
    return (
        f"Reference context (each block is a passage from a cited medical document):\n"
        f"{context}\n\n"
        f"User symptom description: {query}\n\n"
        f"Using ONLY the context above, list the possible conditions with citations."
    )


def _call_openai(system_prompt: str, user_prompt: str, model: str | None = None) -> str:
    from openai import OpenAI

    if not config.OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to your .env file, or set "
            "LLM_PROVIDER=groq (free) or LLM_PROVIDER=ollama (local) instead."
        )
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=model or config.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()


def _call_groq(system_prompt: str, user_prompt: str, model: str | None = None) -> str:
    """Groq's API is OpenAI-compatible, so we reuse the OpenAI SDK with a
    different base_url and key. Free tier, no credit card required -
    see https://console.groq.com/keys"""
    from openai import OpenAI

    if not config.GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Get a free key at https://console.groq.com/keys "
            "and add it to your .env file."
        )
    client = OpenAI(api_key=config.GROQ_API_KEY, base_url=config.GROQ_BASE_URL)
    response = client.chat.completions.create(
        model=model or config.GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()


def _call_ollama(system_prompt: str, user_prompt: str, model: str | None = None) -> str:
    import requests

    payload = {
        "model": model or config.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
    }
    resp = requests.post(f"{config.OLLAMA_BASE_URL}/api/chat", json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


def _call_llm(system_prompt: str, user_prompt: str, provider: str | None = None, model: str | None = None) -> str:
    provider = (provider or config.LLM_PROVIDER).strip().lower()
    if provider == "openai":
        return _call_openai(system_prompt, user_prompt, model)
    if provider == "groq":
        return _call_groq(system_prompt, user_prompt, model)
    if provider == "ollama":
        return _call_ollama(system_prompt, user_prompt, model)
    raise ValueError(f"Unknown LLM_PROVIDER '{provider}'. Use 'openai', 'groq', or 'ollama'.")


def generate_grounded_answer(query: str, context_blocks: list[str]) -> str:
    """RAG-grounded generation: the LLM must cite the given context blocks."""
    user_prompt = _build_user_prompt(query, context_blocks)
    return _call_llm(SYSTEM_PROMPT, user_prompt)


def generate_ungrounded_answer(query: str) -> str:
    """No retrieval at all - used as the baseline for Objective 4 (hallucination comparison)."""
    user_prompt = f"User symptom description: {query}"
    return _call_llm(NO_RAG_SYSTEM_PROMPT, user_prompt)
