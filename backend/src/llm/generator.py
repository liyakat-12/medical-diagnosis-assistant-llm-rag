"""
LLM generation wrapper.

Supports four providers via LLM_PROVIDER in .env:
  - mock   : offline answers built from retrieved passages (no API key)
  - groq   : free cloud API (OpenAI-compatible)
  - openai : paid OpenAI API
  - ollama : local model server
"""
from __future__ import annotations

import re

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
4. Never claim certainty. Use language like "may be" or "one possible match is".
5. Keep the whole answer under 80 words. List at most 3 conditions. One short line each.
6. Then add 2 short recommendation lines on what to do next, grounded in the context \
(rest, fluids, when to see a doctor). Never give a drug dose.
7. End with this exact line: Not a diagnosis — see a clinician if needed.
"""

NO_RAG_SYSTEM_PROMPT = """You are a medical assistant chatbot. Answer the user's \
question about their symptoms as helpfully as you can, in a short, clear list of \
possible conditions.
"""

SOURCE_TITLE_RE = re.compile(r"Source:\s*(.+?)(?:\s*\(|$)", re.IGNORECASE)


def _build_user_prompt(query: str, context_blocks: list[str]) -> str:
    if not context_blocks:
        return f"User symptom description: {query}\n\n(No reference context was retrieved.)"
    context = "\n\n".join(context_blocks)
    return (
        f"Reference context (each block is a passage from a cited medical document):\n"
        f"{context}\n\n"
        f"User symptom description: {query}\n\n"
        f"Using ONLY the context above, write a SHORT list of possible conditions with citations, "
        f"then 2 short next-step recommendations from that context."
    )


def _extract_title(block: str) -> str:
    match = SOURCE_TITLE_RE.search(block)
    if match:
        return match.group(1).strip()
    return "Retrieved medical document"


def _call_mock(system_prompt: str, user_prompt: str, grounded: bool = True) -> str:
    """Build a citation-style answer from retrieved context without calling an API.

    Used for demos and submission when no API key is configured. Grounded mode
    only lists conditions that appear in the retrieved context blocks.
    """
    if not grounded:
        return (
            "No documents were retrieved, so this answer cannot be cited.\n"
            "Not a diagnosis — see a clinician if needed."
        )

    # Pull titles from context blocks that look like: [n] Source: Title (...)
    titles: list[str] = []
    for block in user_prompt.split("\n\n"):
        if "Source:" in block:
            title = _extract_title(block)
            if title and title not in titles:
                titles.append(title)

    if not titles:
        return (
            "Not enough matching documents for a confident answer. "
            "Please rephrase, or see a doctor.\n"
            "Not a diagnosis — see a clinician if needed."
        )

    lines = ["Possible matches:"]
    for i, title in enumerate(titles[:3], start=1):
        lines.append(f"{i}. {title} (Source: {title}).")

    recs: list[str] = []
    for sent in re.split(r"(?<=[.!?])\s+", user_prompt):
        text = sent.strip()
        if len(text) < 35 or len(text) > 220:
            continue
        if not re.search(r"\b(self-care|rest|fluid|see a doctor|seek|consult|monitor)\b", text, re.I):
            continue
        if text not in recs:
            recs.append(text)
        if len(recs) == 2:
            break
    if recs:
        lines.append("Recommendations:")
        for rec in recs:
            lines.append(f"- {rec}")
    lines.append("Not a diagnosis — see a clinician if needed.")
    return "\n".join(lines)


def _call_openai(system_prompt: str, user_prompt: str, model: str | None = None) -> str:
    from openai import OpenAI

    if config._looks_like_placeholder(config.OPENAI_API_KEY):
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to your .env file, or set "
            "LLM_PROVIDER=mock (offline) or LLM_PROVIDER=groq (free)."
        )
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=model or config.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=280,
    )
    return response.choices[0].message.content.strip()


def _call_groq(system_prompt: str, user_prompt: str, model: str | None = None) -> str:
    """Groq's API is OpenAI-compatible, so we reuse the OpenAI SDK with a
    different base_url and key. Free tier, no credit card required -
    see https://console.groq.com/keys"""
    from openai import OpenAI

    if config._looks_like_placeholder(config.GROQ_API_KEY):
        raise RuntimeError(
            "GROQ_API_KEY is not set. Get a free key at https://console.groq.com/keys "
            "and add it to your .env file, or set LLM_PROVIDER=mock for offline demos."
        )
    client = OpenAI(api_key=config.GROQ_API_KEY, base_url=config.GROQ_BASE_URL)
    response = client.chat.completions.create(
        model=model or config.GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=280,
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


def _call_llm(
    system_prompt: str,
    user_prompt: str,
    provider: str | None = None,
    model: str | None = None,
    grounded: bool = True,
) -> str:
    provider = (provider or config.resolve_llm_provider()).strip().lower()
    if provider == "mock":
        return _call_mock(system_prompt, user_prompt, grounded=grounded)
    if provider == "openai":
        return _call_openai(system_prompt, user_prompt, model)
    if provider == "groq":
        return _call_groq(system_prompt, user_prompt, model)
    if provider == "ollama":
        return _call_ollama(system_prompt, user_prompt, model)
    raise ValueError(
        f"Unknown LLM_PROVIDER '{provider}'. Use 'mock', 'openai', 'groq', or 'ollama'."
    )


def generate_grounded_answer(query: str, context_blocks: list[str]) -> str:
    """RAG-grounded generation: the LLM must cite the given context blocks."""
    user_prompt = _build_user_prompt(query, context_blocks)
    return _call_llm(SYSTEM_PROMPT, user_prompt, grounded=True)


def generate_ungrounded_answer(query: str) -> str:
    """No retrieval at all - used as the baseline for Objective 4 (hallucination comparison)."""
    user_prompt = f"User symptom description: {query}"
    return _call_llm(NO_RAG_SYSTEM_PROMPT, user_prompt, grounded=False)
