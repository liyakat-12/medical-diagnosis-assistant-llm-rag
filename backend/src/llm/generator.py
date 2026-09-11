"""
LLM generation wrapper.

Providers are resolved through src.ai.registry so new models can be added
without changing the RAG pipeline.
"""
from __future__ import annotations

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
7. End with this exact line: Not a diagnosis — see a clinician if needed.
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
        f"Using ONLY the context above, write a SHORT list of possible conditions with citations, "
        f"then 2 short next-step recommendations from that context."
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


def generate_grounded_answer(query: str, context_blocks: list[str]) -> str:
    """RAG-grounded generation: the LLM must cite the given context blocks."""
    user_prompt = _build_user_prompt(query, context_blocks)
    return _call_llm(SYSTEM_PROMPT, user_prompt, grounded=True)


def stream_grounded_answer(query: str, context_blocks: list[str]) -> Iterator[str]:
    user_prompt = _build_user_prompt(query, context_blocks)
    yield from stream_llm(SYSTEM_PROMPT, user_prompt, grounded=True)


def generate_ungrounded_answer(query: str) -> str:
    """No retrieval at all - used as the baseline for Objective 4 (hallucination comparison)."""
    user_prompt = f"User symptom description: {query}"
    return _call_llm(NO_RAG_SYSTEM_PROMPT, user_prompt, grounded=False)
