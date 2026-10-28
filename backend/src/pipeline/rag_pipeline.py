"""
End-to-end RAG pipeline (Objective 1 + Objective 2).

Flow for a single user query:

  1. Safety pre-checks (guardrails) run first, on the raw query:
       - prescription/dosage request -> refuse immediately, skip RAG.
       - emergency red flags -> still run RAG for informational context,
         but the triage banner is forced to "emergency".
  2. Retrieve top-k cited passages from the vector store.
  3. Classify triage level (emergency override, else worst-case among
     retrieved evidence).
  4. Ask the LLM to generate a grounded answer, citing only the retrieved
     passages.
  5. Citation faithfulness audit: every claim is checked against retrieved
     titles. Uncited or fabricated citations are flagged.
  6. Package everything (answer, triage, citations, audit, disclaimer)
     into one response object for the API/UI layer.
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field

from src import config
from src.pipeline.conversation_state import ConversationState, build_conversation_state
from src.pipeline.question_type import (
    GENERAL_KNOWLEDGE,
    MEDICATION_SAFETY,
    generation_mode,
    uses_condition_cards,
    uses_personalized_triage,
)
from src.llm.generator import (
    generate_conversational_answer,
    generate_grounded_answer,
    generate_notes_fallback_answer,
    generate_ungrounded_answer,
    stream_conversational_answer,
    stream_grounded_answer,
)
from src.llm.kb_miss import (
    KbMissBundle,
    can_use_llm_kb_fallback,
    general_ai_citation,
    generate_kb_miss_bundle,
    is_broad_unnamed_medical_query,
)
from src.retrieval.query_normalize import (
    evidence_supports_named_disease,
    is_underspecified_medical_query,
    retrieval_topics,
)
from src.retrieval.retriever import Evidence, retrieve_candidates
from src.safety.citation_faithfulness import FaithfulnessAudit, audit_citation_faithfulness
from src.safety.public_text import KB_MISS_STATUS, public_chat_payload, sanitize_status
from src.safety.followups import clarifying_questions, weak_match_answer
from src.safety.guardrails import (
    PRESCRIPTION_REFUSAL_MESSAGE,
    check_emergency,
    check_prescription_request,
    conversational_reply,
    emergency_banner_message,
    has_chest_pain_signal,
    is_general_intent,
)

GENERAL_CHAT_FAILURE = "I could not finish this reply. Please try again in a moment."
from src.safety.triage import CHEST_PAIN_SAFETY_QUESTIONS, TriageResult, classify_triage

logger = logging.getLogger("mediassist.pipeline")
OUTCOME_LIMIT = 4


_REC_HINT = re.compile(
    r"\b(self-care|rest|fluid|see a doctor|seek|consult|emergency|monitor|"
    r"stay home|humidifier|saline|ice|do not|book|call)\b",
    re.I,
)


@dataclass
class DiagnosisResponse:
    query: str
    refused: bool
    refusal_reason: str | None
    triage: TriageResult | None
    answer: str
    citations: list[dict] = field(default_factory=list)
    faithfulness: FaithfulnessAudit | None = None
    disclaimer: str = config.DISCLAIMER
    recommendations: list[str] = field(default_factory=list)
    possible_conditions: list[dict] = field(default_factory=list)
    evidence_origin: str = "none"
    timings: dict[str, float] = field(default_factory=dict)
    question_type: str = ""
    personal_context: bool = False


_REFERENCE_NOTE = "This is general information from reference notes, not personal medical advice."


def _attach_state(result: DiagnosisResponse, state: ConversationState | None) -> DiagnosisResponse:
    if state is None:
        return result
    result.question_type = state.question_type
    result.personal_context = bool(state.personal_context)
    return result


def _apply_question_policy(
    state: ConversationState,
    *,
    triage: TriageResult | None,
    matches: list[dict],
    recs: list[str],
    strong: bool,
) -> tuple[TriageResult | None, list[dict], list[str]]:
    if triage and triage.level == "emergency":
        return triage, matches if uses_condition_cards(state.question_type, True) else matches, recs
    if not uses_personalized_triage(state.question_type, state.personal_context):
        triage = None
        if strong:
            recs = [_REFERENCE_NOTE]
        elif recs:
            recs = [item for item in recs if "see a doctor" not in item.lower() and "book" not in item.lower()]
    if not uses_condition_cards(state.question_type, state.personal_context):
        matches = []
    return triage, matches, recs


def _recommendations(triage: TriageResult | None, evidence: list[Evidence]) -> list[str]:
    items: list[str] = []
    if triage and triage.guidance:
        items.append(triage.guidance)
    for ev in evidence[:2]:
        for sent in re.split(r"(?<=[.!?])\s+", ev.text or ""):
            text = sent.strip()
            if len(text) < 35 or len(text) > 320:
                continue
            if not _REC_HINT.search(text):
                continue
            if text not in items:
                items.append(text)
            if len(items) >= 4:
                return items
    return items


def _format_context_block(ev: Evidence, index: int) -> str:
    return f"[{index}] Source: {ev.title} ({ev.source})\n{ev.text}"


def _pretty_condition(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return "Possible match"
    if "_" in text and " " not in text:
        text = text.replace("_", " ")
    return text


def match_percents(scores: list[float]) -> list[int]:
    """Turn retrieval scores into whole percentages that add up to 100."""
    if not scores:
        return []
    cleaned = [max(0.0, float(score)) for score in scores]
    total = sum(cleaned)
    if total <= 0:
        n = len(cleaned)
        base = [100 // n] * n
        for i in range(100 % n):
            base[i] += 1
        return base
    raw = [score / total * 100 for score in cleaned]
    floors = [int(value) for value in raw]
    leftover = 100 - sum(floors)
    if leftover > 0:
        order = sorted(range(len(raw)), key=lambda i: (raw[i] - floors[i], raw[i]), reverse=True)
        for i in order[:leftover]:
            floors[i] += 1
    elif leftover < 0:
        order = sorted(range(len(raw)), key=lambda i: (raw[i] - floors[i], raw[i]))
        for i in order[: -leftover]:
            if floors[i] > 0:
                floors[i] -= 1
    return floors


def citations_from_evidence(evidence: list[Evidence]) -> list[dict]:
    return [
        {
            "title": ev.title,
            "source": ev.source,
            "url": ev.url,
            "condition": ev.condition,
            "relevance_score": round(ev.relevance_score, 4),
        }
        for ev in evidence
    ]


def build_possible_conditions(citations: list[dict], limit: int = OUTCOME_LIMIT) -> list[dict]:
    seen: set[str] = set()
    rows: list[dict] = []
    for item in citations:
        key = (item.get("condition") or item.get("title") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "condition": _pretty_condition(str(item.get("condition") or item.get("title") or "Condition")),
                "title": item.get("title") or "",
                "source": item.get("source") or "",
                "url": item.get("url") or "",
                "relevance_score": item.get("relevance_score") or 0.0,
            }
        )
        if len(rows) >= limit:
            break
    percents = match_percents([float(row.get("relevance_score") or 0) for row in rows])
    for row, percent in zip(rows, percents):
        row["match_percent"] = percent
    return rows


def outcomes_for_query(
    query: str,
    citations: list[dict],
    embedding_mode: str | None = None,
    pool: list[dict] | None = None,
) -> list[dict]:
    """Build match rows from the retrieval already done for this query."""
    del query, embedding_mode
    return build_possible_conditions(pool or citations)


def _history_payload(history: list[dict] | None) -> list[dict]:
    rows: list[dict] = []
    for item in history or []:
        rows.append(
            {
                "role": item.get("role"),
                "content": item.get("content") or "",
                "possible_conditions": item.get("possible_conditions") or [],
                "triage": item.get("triage"),
            }
        )
    window = max(2, int(getattr(config, "CHAT_HISTORY_WINDOW", 8)))
    return rows[-window:]


def _evidence_is_strong(evidence: list[Evidence]) -> bool:
    """Relevant hits must not be discarded solely because rerank sigmoid is low."""
    if not evidence:
        return False
    best_rerank = max(float(ev.relevance_score) for ev in evidence)
    best_vector = max(float(ev.vector_score) for ev in evidence)
    if best_rerank >= config.MIN_RELEVANCE_SCORE:
        return True
    if best_vector >= config.MIN_VECTOR_SCORE:
        return True
    return False


def _emergency_answer(query: str, *, with_retrieval_note: bool = False) -> str:
    lines = [emergency_banner_message()]
    if has_chest_pain_signal(query):
        lines.append(
            "Chest pain can be serious. If it is severe, persistent, or comes with "
            "breathlessness, sweating, fainting, nausea, or pain spreading to an arm, "
            "jaw, back, or shoulder, seek emergency care now."
        )
        lines.extend(CHEST_PAIN_SAFETY_QUESTIONS)
    if with_retrieval_note:
        lines.append(
            "I could not rely on matching knowledge-base notes for this urgency assessment; "
            "emergency guidance does not wait on retrieval."
        )
    lines.append("Not a diagnosis — see a clinician if needed.")
    return "\n".join(lines)


def _weak_or_emergency_answer(query: str, triage: TriageResult | None) -> str:
    if triage and triage.level == "emergency":
        return _emergency_answer(query, with_retrieval_note=True)
    return weak_match_answer(query)


def _scope_result(query: str, intent: str, history: list[dict] | None = None) -> DiagnosisResponse:
    """Greetings stay canned. General questions use the configured LLM without medical RAG."""
    if is_general_intent(intent):
        try:
            answer = (generate_conversational_answer(query, history) or "").strip()
        except Exception:
            logger.exception("General chat provider failed")
            answer = ""
        if not answer:
            answer = GENERAL_CHAT_FAILURE
        return DiagnosisResponse(
            query=query,
            refused=False,
            refusal_reason=None,
            triage=None,
            answer=answer,
            citations=[],
            faithfulness=None,
            recommendations=[],
            possible_conditions=[],
            evidence_origin="general",
            question_type=GENERAL_KNOWLEDGE,
        )
    return DiagnosisResponse(
        query=query,
        refused=False,
        refusal_reason=None,
        triage=None,
        answer=conversational_reply(query, intent),
        citations=[],
        faithfulness=None,
        recommendations=[],
        possible_conditions=[],
        evidence_origin="none",
        question_type=GENERAL_KNOWLEDGE,
    )


def _result_from_kb_miss(query: str, bundle: KbMissBundle) -> DiagnosisResponse:
    return DiagnosisResponse(
        query=query,
        refused=False,
        refusal_reason=None,
        triage=bundle.triage,
        answer=bundle.answer,
        citations=bundle.citations,
        faithfulness=None,
        disclaimer=bundle.disclaimer,
        recommendations=bundle.recommendations,
        possible_conditions=bundle.possible_conditions,
        evidence_origin="none" if bundle.failed else "llm",
    )


_EMERGENCY_NOTE = re.compile(
    r"\b(chest|heart|cardiac|stroke|bleed|breath|anaphyla|seizure|suicid|poison|overdose)\b",
    re.I,
)


def _evidence_matches_query_topics(query: str, evidence: list[Evidence]) -> list[Evidence]:
    """Keep notes for the current complaint only. Empty is safer than leftover cards."""
    topics = retrieval_topics(query)
    if not topics or not evidence:
        filtered = list(evidence)
    else:
        filtered = [
            ev
            for ev in evidence
            if retrieval_topics(f"{ev.title} {ev.condition} {ev.text[:500]}") & topics
        ]
    if not check_emergency(query).triggered:
        return filtered
    return [
        ev
        for ev in filtered
        if _EMERGENCY_NOTE.search(f"{ev.title} {ev.condition} {ev.doc_id}")
    ]


def _retain_relevant_evidence(query: str, evidence: list[Evidence]) -> list[Evidence]:
    """Topic filter, then drop individually weak hits so junk 0–2% cards disappear."""
    if is_underspecified_medical_query(query) or is_broad_unnamed_medical_query(query):
        return []
    filtered = _evidence_matches_query_topics(query, evidence)
    texts = [f"{ev.title} {ev.condition} {ev.doc_id} {ev.text[:500]}" for ev in filtered]
    if filtered and not evidence_supports_named_disease(query, texts):
        return []
    return [
        ev
        for ev in filtered
        if float(ev.relevance_score) >= config.MIN_RELEVANCE_SCORE
        or float(ev.vector_score) >= config.MIN_VECTOR_SCORE
    ]


_REC_CONTINUATION = re.compile(
    r"^(if|or|and|when|recurring)\b|seek emergency|see a doctor|consult a doctor",
    re.I,
)


def _needs_general_knowledge_disclosure(audit: FaithfulnessAudit | None) -> bool:
    """Mark mixed origin only for invented sources or extra uncited condition claims."""
    if audit is None:
        return False
    if audit.fabricated_count:
        return True
    if not audit.claims:
        return bool(audit.unsupported_count)
    return any(
        claim.status == "unsupported" and not _REC_CONTINUATION.search(claim.text or "")
        for claim in audit.claims
    )


def _with_emergency_banner(query: str, answer: str, triage: TriageResult | None) -> str:
    """Keep emergency guidance in the answer body even when notes also matched."""
    if not triage or triage.level != "emergency":
        return answer
    banner = emergency_banner_message()
    number = str(getattr(config, "EMERGENCY_NUMBER", "112"))
    if number in (answer or "") and re.search(r"\bemergency\b", answer or "", re.I):
        return answer
    extra = ""
    if has_chest_pain_signal(query) and "Chest pain can be serious" not in (answer or ""):
        extra = (
            "\nChest pain can be serious. If it is severe, persistent, or comes with "
            "breathlessness, sweating, fainting, nausea, or pain spreading to an arm, "
            "jaw, back, or shoulder, seek emergency care now.\n"
            + "\n".join(CHEST_PAIN_SAFETY_QUESTIONS)
        )
    return f"{banner}{extra}\n\n{answer}".strip()


def synthesize_retrieval_query(query: str, history: list[dict] | None = None) -> str:
    """Keep follow-up retrieval anchored to the active complaint only."""
    return build_conversation_state(query, history).search_query


def _empty_timings() -> dict[str, float]:
    return {"classify_ms": 0.0, "retrieve_ms": 0.0, "generate_ms": 0.0, "total_ms": 0.0}


def _with_timings(result: DiagnosisResponse, timings: dict[str, float]) -> DiagnosisResponse:
    result.timings = timings
    return result


def run_pipeline(
    query: str,
    top_k: int | None = None,
    embedding_mode: str | None = None,
    chat_history: list[dict] | None = None,
) -> DiagnosisResponse:
    started = time.perf_counter()
    timings = _empty_timings()
    query = query.strip()
    history = _history_payload(chat_history)

    # --- Safety pre-check: prescription/dosage requests are refused outright ---
    prescription_check = check_prescription_request(query)
    if prescription_check.triggered:
        timings["total_ms"] = round((time.perf_counter() - started) * 1000, 2)
        return _with_timings(
            DiagnosisResponse(
                query=query,
                refused=True,
                refusal_reason="prescription_or_dosage_request",
                triage=None,
                answer=PRESCRIPTION_REFUSAL_MESSAGE,
                citations=[],
                faithfulness=None,
                recommendations=["Ask a doctor or pharmacist instead of requesting a specific dose here."],
                question_type=MEDICATION_SAFETY,
                personal_context=False,
            ),
            timings,
        )

    classify_started = time.perf_counter()
    state = build_conversation_state(query, history)
    timings["classify_ms"] = round((time.perf_counter() - classify_started) * 1000, 2)
    if state.intent != "medical":
        generate_started = time.perf_counter()
        result = _scope_result(query, state.intent, state.generation_history)
        timings["generate_ms"] = round((time.perf_counter() - generate_started) * 1000, 2)
        timings["total_ms"] = round((time.perf_counter() - started) * 1000, 2)
        logger.info("pipeline timings %s", timings)
        return _with_timings(_attach_state(result, state), timings)

    # Deterministic emergency triage BEFORE retrieval so chest-pain / red-flag
    # guidance is never delayed by embeddings, reranking, or the LLM.
    early_emergency = check_emergency(query, history)
    early_triage = classify_triage(query, [], history) if early_emergency.triggered else None

    retrieve_started = time.perf_counter()
    try:
        evidence, pool = retrieve_candidates(state.search_query, top_k=top_k, mode=embedding_mode)
    except Exception:
        evidence, pool = [], []
    retain_query = state.search_query or query
    evidence = _retain_relevant_evidence(retain_query, evidence)
    pool = _retain_relevant_evidence(retain_query, pool)
    timings["retrieve_ms"] = round((time.perf_counter() - retrieve_started) * 1000, 2)
    strong = _evidence_is_strong(evidence)
    # Emergency always; evidence-based triage only when retrieval is strong.
    if early_triage and early_triage.level == "emergency":
        triage = early_triage
    elif strong and uses_personalized_triage(state.question_type, state.personal_context):
        triage = classify_triage(query, evidence, history)
    else:
        triage = None

    if triage and triage.level == "emergency" and not strong:
        answer = _emergency_answer(query, with_retrieval_note=True)
        timings["total_ms"] = round((time.perf_counter() - started) * 1000, 2)
        logger.info("pipeline timings %s", timings)
        return _with_timings(
            _attach_state(
                DiagnosisResponse(
                    query=query,
                    refused=False,
                    refusal_reason=None,
                    triage=triage,
                    answer=answer,
                    citations=[],
                    faithfulness=None,
                    recommendations=[triage.guidance, *clarifying_questions(query, limit=2)],
                    possible_conditions=[],
                    evidence_origin="none",
                ),
                state,
            ),
            timings,
        )

    generate_started = time.perf_counter()
    if not strong and can_use_llm_kb_fallback():
        bundle = generate_kb_miss_bundle(query, state.generation_history)
        timings["generate_ms"] = round((time.perf_counter() - generate_started) * 1000, 2)
        if bundle:
            timings["total_ms"] = round((time.perf_counter() - started) * 1000, 2)
            logger.info("pipeline timings %s", timings)
            miss = _result_from_kb_miss(query, bundle)
            miss.triage, miss.possible_conditions, miss.recommendations = _apply_question_policy(
                state,
                triage=miss.triage,
                matches=miss.possible_conditions,
                recs=miss.recommendations,
                strong=False,
            )
            return _with_timings(_attach_state(miss, state), timings)

    mode = generation_mode(state.question_type, state.personal_context)
    context_blocks = [_format_context_block(ev, i + 1) for i, ev in enumerate(evidence)] if strong else []
    if strong:
        answer = generate_grounded_answer(
            query, context_blocks, state.generation_history, weak_match=False, mode=mode
        )
        answer = _with_emergency_banner(query, answer, triage)
    else:
        answer = _weak_or_emergency_answer(query, triage)
    timings["generate_ms"] = round((time.perf_counter() - generate_started) * 1000, 2)
    citations = citations_from_evidence(evidence) if strong else []
    faithfulness = audit_citation_faithfulness(answer, citations) if strong else None
    origin = "knowledge_base" if strong else "none"
    if strong and _needs_general_knowledge_disclosure(faithfulness):
        citations = [*citations, general_ai_citation()]
        origin = "mixed"
    matches = (
        outcomes_for_query(query, citations, embedding_mode, citations_from_evidence(pool))
        if strong
        else []
    )
    recs = _recommendations(triage, evidence) if strong else clarifying_questions(query, limit=2)
    triage, matches, recs = _apply_question_policy(
        state, triage=triage, matches=matches, recs=recs, strong=strong
    )
    timings["total_ms"] = round((time.perf_counter() - started) * 1000, 2)
    logger.info("pipeline timings %s", timings)

    return _with_timings(
        _attach_state(
            DiagnosisResponse(
                query=query,
                refused=False,
                refusal_reason=None,
                triage=triage,
                answer=answer,
                citations=citations,
                faithfulness=faithfulness,
                recommendations=recs,
                possible_conditions=matches,
                evidence_origin=origin,
            ),
            state,
        ),
        timings,
    )


def result_to_dict(result: DiagnosisResponse) -> dict:
    payload = {
        "query": result.query,
        "refused": result.refused,
        "refusal_reason": result.refusal_reason,
        "answer": result.answer,
        "citations": result.citations,
        "recommendations": result.recommendations,
        "disclaimer": result.disclaimer,
        "possible_conditions": result.possible_conditions or [],
        "triage": None,
        "faithfulness": None,
        "evidence_origin": result.evidence_origin,
        "timings": result.timings or {},
        "question_type": result.question_type or "",
        "personal_context": bool(result.personal_context),
    }
    if result.triage:
        payload["triage"] = {
            "level": result.triage.level,
            "label": result.triage.label,
            "guidance": result.triage.guidance,
            "reason": result.triage.reason,
        }
    if result.faithfulness is not None:
        payload["faithfulness"] = result.faithfulness.to_dict()
    return public_chat_payload(payload)


def iter_pipeline_stream(
    query: str,
    top_k: int | None = None,
    embedding_mode: str | None = None,
    chat_history: list[dict] | None = None,
):
    """Yield SSE-friendly events while running the same RAG + safety flow."""
    started = time.perf_counter()
    timings = _empty_timings()
    query = query.strip()
    history = _history_payload(chat_history)
    yield {"type": "status", "content": "Understanding your message..."}

    prescription_check = check_prescription_request(query)
    if prescription_check.triggered:
        timings["total_ms"] = round((time.perf_counter() - started) * 1000, 2)
        result = _with_timings(
            DiagnosisResponse(
                query=query,
                refused=True,
                refusal_reason="prescription_or_dosage_request",
                triage=None,
                answer=PRESCRIPTION_REFUSAL_MESSAGE,
                citations=[],
                faithfulness=None,
                recommendations=["Ask a doctor or pharmacist instead of requesting a specific dose here."],
                question_type=MEDICATION_SAFETY,
                personal_context=False,
            ),
            timings,
        )
        yield {"type": "token", "content": PRESCRIPTION_REFUSAL_MESSAGE}
        yield {"type": "done", "result": result_to_dict(result)}
        return

    classify_started = time.perf_counter()
    state = build_conversation_state(query, history)
    timings["classify_ms"] = round((time.perf_counter() - classify_started) * 1000, 2)
    if state.intent != "medical":
        yield {"type": "status", "content": "Formulating response..."}
        generate_started = time.perf_counter()
        if is_general_intent(state.intent):
            chunks: list[str] = []
            try:
                for chunk in stream_conversational_answer(query, state.generation_history):
                    chunks.append(chunk)
                    yield {"type": "token", "content": chunk}
                answer = "".join(chunks).strip()
                if not answer:
                    raise RuntimeError("empty general stream")
            except Exception:
                logger.exception("General chat stream failed")
                answer = GENERAL_CHAT_FAILURE
                yield {"type": "token", "content": answer}
            result = DiagnosisResponse(
                query=query,
                refused=False,
                refusal_reason=None,
                triage=None,
                answer=answer,
                citations=[],
                faithfulness=None,
                recommendations=[],
                possible_conditions=[],
                evidence_origin="general",
                question_type=GENERAL_KNOWLEDGE,
            )
        else:
            result = _scope_result(query, state.intent, state.generation_history)
            yield {"type": "token", "content": result.answer}
        timings["generate_ms"] = round((time.perf_counter() - generate_started) * 1000, 2)
        timings["total_ms"] = round((time.perf_counter() - started) * 1000, 2)
        logger.info("pipeline timings %s", timings)
        yield {"type": "done", "result": result_to_dict(_with_timings(_attach_state(result, state), timings))}
        return

    # Emit emergency triage immediately — do not wait on retrieval or the LLM.
    early_emergency = check_emergency(query, history)
    early_triage = classify_triage(query, [], history) if early_emergency.triggered else None
    if early_triage:
        yield {
            "type": "triage",
            "level": early_triage.level,
            "label": early_triage.label,
            "guidance": early_triage.guidance,
            "reason": early_triage.reason,
        }

    yield {"type": "status", "content": "Searching medical knowledge base..."}
    retrieve_started = time.perf_counter()
    try:
        evidence, pool = retrieve_candidates(state.search_query, top_k=top_k, mode=embedding_mode)
    except Exception:
        evidence, pool = [], []
    retain_query = state.search_query or query
    evidence = _retain_relevant_evidence(retain_query, evidence)
    pool = _retain_relevant_evidence(retain_query, pool)
    timings["retrieve_ms"] = round((time.perf_counter() - retrieve_started) * 1000, 2)
    strong = _evidence_is_strong(evidence)
    if early_triage and early_triage.level == "emergency":
        triage = early_triage
    elif strong and uses_personalized_triage(state.question_type, state.personal_context):
        triage = classify_triage(query, evidence, history)
        if not early_triage:
            yield {
                "type": "triage",
                "level": triage.level,
                "label": triage.label,
                "guidance": triage.guidance,
                "reason": triage.reason,
            }
    else:
        triage = None

    if triage and triage.level == "emergency" and not strong:
        answer = _emergency_answer(query, with_retrieval_note=True)
        yield {"type": "token", "content": answer}
        timings["total_ms"] = round((time.perf_counter() - started) * 1000, 2)
        logger.info("pipeline timings %s", timings)
        result = _with_timings(
            _attach_state(
                DiagnosisResponse(
                    query=query,
                    refused=False,
                    refusal_reason=None,
                    triage=triage,
                    answer=answer,
                    citations=[],
                    faithfulness=None,
                    recommendations=[triage.guidance, *clarifying_questions(query, limit=2)],
                    possible_conditions=[],
                    evidence_origin="none",
                ),
                state,
            ),
            timings,
        )
        payload = result_to_dict(result)
        yield {"type": "metadata", "recommendations": payload["recommendations"], "faithfulness": None}
        yield {"type": "done", "result": payload}
        return

    generate_started = time.perf_counter()
    if not strong and can_use_llm_kb_fallback():
        yield {"type": "status", "content": sanitize_status(KB_MISS_STATUS)}
        bundle = generate_kb_miss_bundle(query, state.generation_history)
        timings["generate_ms"] = round((time.perf_counter() - generate_started) * 1000, 2)
        if bundle:
            timings["total_ms"] = round((time.perf_counter() - started) * 1000, 2)
            logger.info("pipeline timings %s", timings)
            miss = _result_from_kb_miss(query, bundle)
            miss.triage, miss.possible_conditions, miss.recommendations = _apply_question_policy(
                state,
                triage=miss.triage,
                matches=miss.possible_conditions,
                recs=miss.recommendations,
                strong=False,
            )
            result = _with_timings(_attach_state(miss, state), timings)
            payload = result_to_dict(result)
            yield {"type": "status", "content": "Formulating response..."}
            if bundle.answer:
                yield {"type": "token", "content": bundle.answer}
            if result.triage:
                yield {
                    "type": "triage",
                    "level": result.triage.level,
                    "label": result.triage.label,
                    "guidance": result.triage.guidance,
                    "reason": result.triage.reason,
                }
            yield {
                "type": "citation",
                "citations": result.citations,
                "possible_conditions": result.possible_conditions,
            }
            yield {"type": "metadata", "recommendations": payload["recommendations"], "faithfulness": None}
            yield {"type": "done", "result": payload}
            return

    mode = generation_mode(state.question_type, state.personal_context)
    citations = citations_from_evidence(evidence) if strong else []
    possible_conditions = (
        outcomes_for_query(query, citations, embedding_mode, citations_from_evidence(pool)) if strong else []
    )
    if not uses_condition_cards(state.question_type, state.personal_context):
        possible_conditions = []
    if citations or possible_conditions:
        yield {"type": "citation", "citations": citations, "possible_conditions": possible_conditions}

    yield {"type": "status", "content": "Formulating response..."}
    chunks: list[str] = []
    generate_started = time.perf_counter()
    if strong:
        context_blocks = [_format_context_block(ev, i + 1) for i, ev in enumerate(evidence)]
        banner = _with_emergency_banner(query, "", triage)
        if banner:
            yield {"type": "token", "content": banner + "\n\n"}
            chunks.append(banner + "\n\n")
        try:
            for chunk in stream_grounded_answer(
                query, context_blocks, state.generation_history, weak_match=False, mode=mode
            ):
                chunks.append(chunk)
                yield {"type": "token", "content": chunk}
            answer = "".join(chunks).strip()
            if not answer or answer == banner:
                raise RuntimeError("empty grounded stream")
        except Exception:
            logger.exception("Assistant generation failed after notes were found; answering from retrieved notes")
            fallback = generate_notes_fallback_answer(
                query, context_blocks, state.generation_history, mode=mode
            )
            fallback = _with_emergency_banner(query, fallback, triage) if not banner else fallback
            yield {"type": "token", "content": fallback}
            chunks = [banner + "\n\n" + fallback if banner else fallback]
            answer = "".join(chunks).strip()
        faithfulness = audit_citation_faithfulness(answer, citations)
        if _needs_general_knowledge_disclosure(faithfulness):
            citations = [*citations, general_ai_citation()]
        recs = _recommendations(triage, evidence)
    else:
        answer = _weak_or_emergency_answer(query, triage)
        yield {"type": "token", "content": answer}
        faithfulness = None
        recs = clarifying_questions(query, limit=2)
    timings["generate_ms"] = round((time.perf_counter() - generate_started) * 1000, 2)
    origin = "knowledge_base" if strong else "none"
    if strong and any((item.get("title") or "").startswith("General AI") for item in citations):
        origin = "mixed"
    triage, possible_conditions, recs = _apply_question_policy(
        state, triage=triage, matches=possible_conditions, recs=recs, strong=strong
    )
    timings["total_ms"] = round((time.perf_counter() - started) * 1000, 2)
    logger.info("pipeline timings %s", timings)
    result = _with_timings(
        _attach_state(
            DiagnosisResponse(
                query=query,
                refused=False,
                refusal_reason=None,
                triage=triage,
                answer=answer,
                citations=citations,
                faithfulness=faithfulness,
                recommendations=recs,
                possible_conditions=possible_conditions,
                evidence_origin=origin,
            ),
            state,
        ),
        timings,
    )
    payload = result_to_dict(result)
    yield {"type": "metadata", "recommendations": payload["recommendations"], "faithfulness": payload["faithfulness"]}
    yield {"type": "done", "result": payload}


def run_no_rag_baseline(query: str) -> str:
    """The same query answered with NO retrieval - used only for the
    hallucination-comparison evaluation (Objective 4), never in the real app."""
    return generate_ungrounded_answer(query)


if __name__ == "__main__":
    import json

    test_query = "I have a burning sensation when I pee and need to go often"
    result = run_pipeline(test_query)
    print(json.dumps(result.__dict__, default=lambda o: o.__dict__, indent=2))
