"""Explicit conversation state for retrieval and grounded generation.

The chat is not a bag of recent strings. Each turn is classified as a greeting,
non-medical request, new complaint, genuine symptom follow-up, or emergency.
Only a follow-up of the same active complaint may reuse earlier symptom text.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.retrieval.query_normalize import (
    apply_symptom_correction,
    clarification_for_prior_modifiers,
    is_ambiguous_symptom_restatement,
    is_symptom_correction,
    normalize_retrieval_query,
    related_history_texts,
    retrieval_topics,
    should_reuse_retrieval_history,
)
from src import config
from src.pipeline.question_type import classify_question_type, infer_personal_context
from src.safety.guardrails import (
    check_emergency,
    check_prescription_request,
    classify_intent,
    is_general_intent,
)


@dataclass(frozen=True)
class ConversationState:
    intent: str
    status: str
    active_complaint: str
    symptoms: list[str]
    followup_details: list[str]
    topics: frozenset[str]
    prior_topics: frozenset[str]
    reuse_history: bool
    search_query: str
    related_user_texts: list[str]
    generation_history: list[dict]
    question_type: str = "SYMPTOM_INFORMATION"
    personal_context: bool = False
    context_clarification: str = ""


def _is_medical_user_text(text: str, history: list[dict]) -> bool:
    lowered = text.lower()
    if "extra detail:" in lowered or "body map context" in lowered:
        return True
    return classify_intent(text, history) == "medical"


def medical_user_texts(history: list[dict] | None) -> list[str]:
    texts: list[str] = []
    for item in history or []:
        if item.get("role") != "user":
            continue
        text = str(item.get("content") or "").strip()
        if not text or not _is_medical_user_text(text, history or []):
            continue
        texts.append(normalize_retrieval_query(text))
    return texts


def _plain_recent_history(history: list[dict]) -> list[dict]:
    """Recent turns for general chat. Strip medical cards so they cannot leak."""
    window = max(2, int(getattr(config, "CHAT_HISTORY_WINDOW", 8)))
    kept: list[dict] = []
    for item in history[-window:]:
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        kept.append(
            {
                "role": item.get("role"),
                "content": content,
                "possible_conditions": [],
                "triage": None,
            }
        )
    return kept


def _generation_history(history: list[dict], related: list[str], reuse: bool) -> list[dict]:
    """Pass only same-complaint turns to the writer. Drop old match cards."""
    if not reuse or not history or not related:
        return []
    related_l = {item.lower() for item in related}
    related_topics: set[str] = set()
    for text in related:
        related_topics |= retrieval_topics(text)
    kept: list[dict] = []
    keep_assistant = False
    for item in history:
        role = item.get("role")
        content = str(item.get("content") or "")
        if role == "user":
            norm = normalize_retrieval_query(content).lower()
            topics = retrieval_topics(content)
            keep = norm in related_l or bool(topics and related_topics and topics & related_topics)
            if keep:
                kept.append(
                    {
                        "role": "user",
                        "content": content,
                        "possible_conditions": [],
                        "triage": item.get("triage"),
                    }
                )
                keep_assistant = True
            else:
                keep_assistant = False
        elif role == "assistant" and keep_assistant:
            kept.append(
                {
                    "role": "assistant",
                    "content": content,
                    "possible_conditions": [],
                    "triage": item.get("triage"),
                }
            )
            keep_assistant = False
    return kept[-6:]


def build_conversation_state(query: str, history: list[dict] | None = None) -> ConversationState:
    """Snapshot of the active complaint for this turn."""
    rows = history or []
    intent = classify_intent(query, rows)
    topics = frozenset(retrieval_topics(query))
    current = normalize_retrieval_query(query)
    prior_texts = medical_user_texts(rows)
    prior_topics = frozenset()
    for text in prior_texts:
        prior_topics |= retrieval_topics(text)

    gen_hist: list[dict] | None
    if check_prescription_request(query).triggered:
        status = "prescription"
        reuse = False
        gen_hist = []
    elif is_general_intent(intent):
        status = intent
        reuse = False
        gen_hist = _plain_recent_history(rows)
    elif intent != "medical":
        status = intent
        reuse = False
        gen_hist = []
    elif check_emergency(query, rows).triggered:
        status = "emergency"
        reuse = should_reuse_retrieval_history(query, prior_texts)
        gen_hist = None
    elif should_reuse_retrieval_history(query, prior_texts):
        status = "follow_up"
        reuse = True
        gen_hist = None
    else:
        # Same body area with dropped modifiers: do not merge prior fever/swelling/etc.
        if intent == "medical" and is_ambiguous_symptom_restatement(query, prior_texts):
            status = "ambiguous_follow_up"
        else:
            status = "new_complaint"
        reuse = False
        gen_hist = None

    related = related_history_texts(query, prior_texts) if reuse else []
    search_current = apply_symptom_correction(current, query) if is_symptom_correction(query) else current
    search = search_current
    if reuse and related:
        search = "\n".join([*related, search_current])[:2000]

    active = related[-1] if related else current
    followup_details = [current] if status == "follow_up" else []
    symptoms = sorted(topics) if topics else sorted(retrieval_topics(active))
    if gen_hist is None:
        gen_hist = _generation_history(rows, related, reuse)

    question_type = classify_question_type(query, intent=intent, status=status, history=rows)
    personal_context = infer_personal_context(query, related, reuse)
    clarification = ""
    if status == "ambiguous_follow_up":
        clarification = clarification_for_prior_modifiers(query, prior_texts)

    return ConversationState(
        intent=intent,
        status=status,
        active_complaint=active,
        symptoms=symptoms,
        followup_details=followup_details,
        topics=topics,
        prior_topics=frozenset(prior_topics),
        reuse_history=reuse,
        search_query=search,
        related_user_texts=related,
        generation_history=gen_hist,
        question_type=question_type,
        personal_context=personal_context,
        context_clarification=clarification,
    )
