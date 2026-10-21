"""
LLM generation wrapper.

Providers are resolved through src.ai.registry so new models can be added
without changing the RAG pipeline.
"""
from __future__ import annotations

import re
from collections.abc import Iterator

from src import config
from src.ai.registry import get_provider

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
7. If a previous conversation is provided, address the NEW user message in that context \
(for example how a new symptom supports, weakens, or narrows earlier possible matches).
8. End with this exact line: Not a diagnosis — see a clinician if needed.
"""

WEAK_MATCH_PROMPT = """You are a careful medical information assistant. Retrieved notes \
were a weak match for this query. Do not name specific diseases or invent match lists. \
Ask exactly two short clarifying questions that are relevant to the user's reported \
symptom and body location (duration, severity, associated warning signs for THAT symptom). \
Do not ask about fever by default unless fever or infection is already suggested. \
Never give a drug dose. End with: Not a diagnosis — see a clinician if needed.
"""

CONVERSATIONAL_SYSTEM_PROMPT = """You are MediAssist, a friendly medical information helper. \
Reply in one or two short sentences. Do not diagnose, retrieve diseases, or assign urgency. \
Invite the user to describe symptoms or tap the body map when they want medical information. \
You are not a doctor.
"""

NO_RAG_SYSTEM_PROMPT = """You are a medical assistant chatbot. Answer the user's \
question about their symptoms as helpfully as you can, in a short, clear list of \
possible conditions.
"""


def _history_block(history: list[dict] | None) -> str:
    if not history:
        return ""
    lines: list[str] = []
    for item in history[-8:]:
        role = "User" if item.get("role") == "user" else "Assistant"
        content = re.sub(r"\s+", " ", str(item.get("content") or "")).strip()[:400]
        if not content:
            continue
        conditions = item.get("possible_conditions") or []
        extra = ""
        if conditions:
            names = ", ".join(str(row.get("condition") or "") for row in conditions[:4] if row.get("condition"))
            if names:
                extra = f" [earlier matches: {names}]"
        lines.append(f"{role}: {content}{extra}")
    if not lines:
        return ""
    return "Previous conversation:\n" + "\n".join(lines) + "\n\n"


def _build_user_prompt(query: str, context_blocks: list[str], history: list[dict] | None = None) -> str:
    prefix = _history_block(history)
    if not context_blocks:
        return f"{prefix}User symptom description: {query}\n\n(No reference context was retrieved.)"
    context = "\n\n".join(context_blocks)
    return (
        f"{prefix}"
        f"Reference context (each block is a passage from a cited medical document):\n"
        f"{context}\n\n"
        f"User symptom description: {query}\n\n"
        f"Using ONLY the context above, write a SHORT list of possible conditions with citations, "
        f"then 2 short next-step recommendations from that context. "
        f"If this is a follow-up, explain how the new detail relates to earlier possible matches."
    )


def _call_llm(
    system_prompt: str,
    user_prompt: str,
    provider: str | None = None,
    model: str | None = None,
    grounded: bool = True,
) -> str:
    return get_provider(provider).generate(
        system_prompt, user_prompt, grounded=grounded, model=model
    )


def stream_llm(
    system_prompt: str,
    user_prompt: str,
    provider: str | None = None,
    model: str | None = None,
    grounded: bool = True,
) -> Iterator[str]:
    yield from get_provider(provider).stream(
        system_prompt, user_prompt, grounded=grounded, model=model
    )


def generate_grounded_answer(
    query: str,
    context_blocks: list[str],
    history: list[dict] | None = None,
    *,
    weak_match: bool = False,
) -> str:
    """RAG-grounded generation: the LLM must cite the given context blocks."""
    user_prompt = _build_user_prompt(query, context_blocks, history)
    prompt = WEAK_MATCH_PROMPT if weak_match else SYSTEM_PROMPT
    return _call_llm(prompt, user_prompt, grounded=True)


def stream_grounded_answer(
    query: str,
    context_blocks: list[str],
    history: list[dict] | None = None,
    *,
    weak_match: bool = False,
) -> Iterator[str]:
    user_prompt = _build_user_prompt(query, context_blocks, history)
    prompt = WEAK_MATCH_PROMPT if weak_match else SYSTEM_PROMPT
    yield from stream_llm(prompt, user_prompt, grounded=True)


def generate_conversational_answer(query: str, history: list[dict] | None = None) -> str:
    prefix = _history_block(history)
    user_prompt = f"[CONVERSATIONAL]\n{prefix}User message: {query}"
    return _call_llm(CONVERSATIONAL_SYSTEM_PROMPT, user_prompt, grounded=True)


def stream_conversational_answer(query: str, history: list[dict] | None = None) -> Iterator[str]:
    prefix = _history_block(history)
    user_prompt = f"[CONVERSATIONAL]\n{prefix}User message: {query}"
    yield from stream_llm(CONVERSATIONAL_SYSTEM_PROMPT, user_prompt, grounded=True)


def generate_ungrounded_answer(query: str) -> str:
    """No retrieval at all - used as the baseline for Objective 4 (hallucination comparison)."""
    user_prompt = f"User symptom description: {query}"
    return _call_llm(NO_RAG_SYSTEM_PROMPT, user_prompt, grounded=False)
