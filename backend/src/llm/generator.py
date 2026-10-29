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
Every medically substantive claim must be followed by a citation in the form (Source: <title>).
2. If the context does not support a confident answer, say so plainly and ask one \
follow-up question instead of guessing.
3. Never provide a specific drug name, dose, or prescription. If asked, refuse and \
recommend consulting a doctor or pharmacist.
4. Never claim the user has a disease. Use "may be" or "one possible explanation is". \
Do not give probabilities or percentages.
5. Use plain English. Explain a familiar idea before an unfamiliar medical term.
6. Prefer a small set, at most 4 explanations from the notes. Put everyday explanations \
that fit the reported symptoms first, then other relevant possibilities, then a serious \
condition only when the notes or the user's warning signs make it relevant. Do not open \
with a rare or severe disease only because it can cause headache, cough, stomach pain, \
fever, or arm pain. Say in one short line why each possibility fits. Do not treat a \
note's assumed trigger (alcohol, anxiety, skipped meals, and similar) as a fact about \
the user unless they reported it.
7. Keep the answer under 160 words. Add at most 2 short next-step lines grounded in the \
context. Do not repeat an urgency warning that is already stated.
8. Previous conversation, if provided, is the same active complaint only. \
Use it to interpret follow-up detail. If none is provided, ignore any earlier illness \
and do not mention leftover conditions, cards, or sources.
9. If one needed detail is missing, you may ask one targeted question. If you add one \
cautious general-knowledge sentence, say it is not from the retrieved notes. \
Do not invent a (Source: ...) citation for that sentence.
10. End with this exact line: Not a diagnosis — see a clinician if needed.
"""

EDUCATION_SYSTEM_PROMPT = """You are a careful medical information assistant answering a \
general educational question. The user is asking what something is, not reporting that \
they have it. Do not assume they have the condition. Do not assign personal urgency or \
tell them to book an appointment unless the notes list warning signs that belong in \
general education.

Use ONLY the reference context below.

Structure, keeping to facts in the notes:
1. A clear plain-language definition.
2. How it works or what causes it, when the notes support that.
3. Common symptoms or triggers when relevant to the question.
4. General management only if the question asks for it or the notes make it essential.
5. Important warning signs if the notes include them, as general information.
Cite claims as (Source: <title>). Do not list possible diagnoses for this user.
Do not invent facts, URLs, or dosages. If the notes are thin, say so.
If the user asked for simple language, keep the same facts in shorter words.
End with: Not a diagnosis — this is general information from reference notes.
"""

SYMPTOM_EDUCATION_PROMPT = """You are a careful medical information assistant. The user \
asked what symptoms a named condition can cause. They did not report that they have it.

Use ONLY the reference context. Describe common symptoms and warning signs from the notes. \
Cite (Source: <title>). Do not diagnose the user or assign personal urgency.
End with: Not a diagnosis — this is general information from reference notes.
"""

CAUSES_SYSTEM_PROMPT = """You are a careful medical information assistant. Explain \
plausible causes supported by the reference notes. Distinguish common causes from \
serious possibilities when the notes do. Do not assign numerical probabilities. \
Do not claim a diagnosis. Cite (Source: <title>).
End with: Not a diagnosis — this is general information from reference notes.
"""

TREATMENT_SYSTEM_PROMPT = """You are a careful medical information assistant. Explain \
general treatment and management options supported by the reference notes. Do not \
prescribe a personalized plan, name a dose, or tell the user which medicine to take. \
Cite (Source: <title>). If the notes are limited, say so.
End with: Not a diagnosis — this is general information from reference notes.
"""

WEAK_MATCH_PROMPT = """You are a careful medical information assistant. Retrieved notes \
were a weak match for this query. Do not name specific diseases or invent match lists. \
Ask exactly two short clarifying questions that are relevant to the user's reported \
symptom and body location (duration, severity, associated warning signs for THAT symptom). \
Do not ask about fever by default unless fever or infection is already suggested. \
Never give a drug dose. End with: Not a diagnosis — see a clinician if needed.
"""

CONVERSATIONAL_SYSTEM_PROMPT = """You are MediAssist, a helpful conversational assistant.

You can answer general knowledge, education, mathematics, programming, travel, transport, \
vehicle comparisons, and everyday questions in clear language. Use markdown: lists, tables, \
and fenced code blocks when they help.

You can also help with medical information questions. You are not a doctor and must never \
diagnose, prescribe, or give a drug dose.

Rules:
- For coding, return working examples and a brief explanation.
- For comparisons, give a balanced, practical answer.
- Use recent conversation only when the new message is a genuine follow-up. If the topic \
changed, ignore leftover medical conditions, triage, citations, and match cards.
- Never attach medical urgency, condition cards, or citations to a non-medical answer.
- Never invent URLs or medical sources.
- If the user describes symptoms, say you can look them up in the medical notes.
"""

NO_RAG_SYSTEM_PROMPT = """You are a medical assistant chatbot. Answer the user's \
question about their symptoms as helpfully as you can, in a short, clear list of \
possible conditions.
"""


def _strip_medical_cards(history: list[dict] | None) -> list[dict]:
    rows: list[dict] = []
    for item in history or []:
        rows.append(
            {
                "role": item.get("role"),
                "content": item.get("content") or "",
                "possible_conditions": [],
                "triage": None,
            }
        )
    return rows


def _history_block(history: list[dict] | None, *, include_matches: bool = True) -> str:
    if not history:
        return ""
    window = max(2, int(getattr(config, "CHAT_HISTORY_WINDOW", 8)))
    lines: list[str] = []
    for item in history[-window:]:
        role = "User" if item.get("role") == "user" else "Assistant"
        content = re.sub(r"\s+", " ", str(item.get("content") or "")).strip()[:400]
        if not content:
            continue
        conditions = item.get("possible_conditions") or []
        extra = ""
        if include_matches and conditions:
            names = ", ".join(str(row.get("condition") or "") for row in conditions[:4] if row.get("condition"))
            if names:
                extra = f" [earlier matches: {names}]"
        lines.append(f"{role}: {content}{extra}")
    if not lines:
        return ""
    return "Previous conversation:\n" + "\n".join(lines) + "\n\n"


def _prompt_for_mode(mode: str, *, weak_match: bool = False) -> str:
    if weak_match:
        return WEAK_MATCH_PROMPT
    if mode == "education":
        return EDUCATION_SYSTEM_PROMPT
    if mode == "symptom_education":
        return SYMPTOM_EDUCATION_PROMPT
    if mode == "causes":
        return CAUSES_SYSTEM_PROMPT
    if mode == "treatment":
        return TREATMENT_SYSTEM_PROMPT
    return SYSTEM_PROMPT


def _build_user_prompt(
    query: str,
    context_blocks: list[str],
    history: list[dict] | None = None,
    *,
    mode: str = "symptom",
) -> str:
    prefix = _history_block(history)
    if not context_blocks:
        label = "User question" if mode != "symptom" else "User symptom description"
        return f"{prefix}{label}: {query}\n\n(No reference context was retrieved.)"
    context = "\n\n".join(context_blocks)
    if mode == "symptom":
        instruction = (
            "Using ONLY the context above, write a SHORT list of possible conditions with citations, "
            "then 2 short next-step recommendations from that context. "
            "If this is a follow-up, explain how the new detail relates to earlier possible matches."
        )
        label = "User symptom description"
    elif mode == "treatment":
        instruction = (
            "Using ONLY the context above, explain general treatment and management options. "
            "Do not prescribe a dose or a personalized plan."
        )
        label = "User question"
    elif mode == "causes":
        instruction = (
            "Using ONLY the context above, explain plausible causes supported by the notes. "
            "Do not assign probabilities or diagnose the user."
        )
        label = "User question"
    elif mode == "symptom_education":
        instruction = (
            "Using ONLY the context above, describe typical symptoms and warning signs of the "
            "named condition. Do not assume the user has it."
        )
        label = "User question"
    else:
        instruction = (
            "Using ONLY the context above, answer the educational question with a plain-language "
            "definition and the supporting facts from the notes. Do not assume the user has the "
            "condition and do not give a personalized urgency label."
        )
        label = "User question"
    return (
        f"{prefix}"
        f"Reference context (each block is a passage from a cited medical document):\n"
        f"{context}\n\n"
        f"{label}: {query}\n\n"
        f"{instruction}"
    )


def _call_llm(
    system_prompt: str,
    user_prompt: str,
    provider: str | None = None,
    model: str | None = None,
    grounded: bool = True,
    max_tokens: int | None = None,
) -> str:
    return get_provider(provider).generate(
        system_prompt,
        user_prompt,
        grounded=grounded,
        model=model,
        max_tokens=max_tokens,
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


def generate_notes_fallback_answer(
    query: str,
    context_blocks: list[str],
    history: list[dict] | None = None,
    *,
    mode: str = "symptom",
) -> str:
    """Write from retrieved notes when the configured assistant model fails."""
    from src.ai.providers.mock import MockProvider

    user_prompt = _build_user_prompt(query, context_blocks, history, mode=mode)
    return MockProvider().generate(_prompt_for_mode(mode), user_prompt, grounded=True)


def generate_grounded_answer(
    query: str,
    context_blocks: list[str],
    history: list[dict] | None = None,
    *,
    weak_match: bool = False,
    mode: str = "symptom",
) -> str:
    """RAG-grounded generation: the LLM must cite the given context blocks."""
    user_prompt = _build_user_prompt(query, context_blocks, history, mode=mode)
    prompt = _prompt_for_mode(mode, weak_match=weak_match)
    try:
        answer = (_call_llm(prompt, user_prompt, grounded=True) or "").strip()
        if answer:
            return answer
    except Exception:
        if weak_match or not context_blocks:
            raise
        return generate_notes_fallback_answer(query, context_blocks, history, mode=mode)
    if weak_match or not context_blocks:
        return ""
    return generate_notes_fallback_answer(query, context_blocks, history, mode=mode)


def stream_grounded_answer(
    query: str,
    context_blocks: list[str],
    history: list[dict] | None = None,
    *,
    weak_match: bool = False,
    mode: str = "symptom",
) -> Iterator[str]:
    user_prompt = _build_user_prompt(query, context_blocks, history, mode=mode)
    prompt = _prompt_for_mode(mode, weak_match=weak_match)
    yield from stream_llm(prompt, user_prompt, grounded=True)


def generate_conversational_answer(query: str, history: list[dict] | None = None) -> str:
    from src.llm.markdown_format import polish_assistant_markdown

    prefix = _history_block(_strip_medical_cards(history), include_matches=False)
    user_prompt = f"[CONVERSATIONAL]\n{prefix}User message: {query}"
    answer = _call_llm(
        CONVERSATIONAL_SYSTEM_PROMPT,
        user_prompt,
        grounded=True,
        max_tokens=config.LLM_GENERAL_MAX_TOKENS,
    )
    return polish_assistant_markdown(answer or "", query)


def stream_conversational_answer(query: str, history: list[dict] | None = None) -> Iterator[str]:
    prefix = _history_block(_strip_medical_cards(history), include_matches=False)
    user_prompt = f"[CONVERSATIONAL]\n{prefix}User message: {query}"
    yield from get_provider().stream(
        CONVERSATIONAL_SYSTEM_PROMPT,
        user_prompt,
        grounded=True,
        max_tokens=config.LLM_GENERAL_MAX_TOKENS,
    )


def generate_ungrounded_answer(query: str) -> str:
    """No retrieval at all - used as the baseline for Objective 4 (hallucination comparison)."""
    user_prompt = f"User symptom description: {query}"
    return _call_llm(NO_RAG_SYSTEM_PROMPT, user_prompt, grounded=False)
