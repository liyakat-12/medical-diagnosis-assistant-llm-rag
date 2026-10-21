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

import re
from dataclasses import dataclass, field

from src import config
from src.llm.generator import (
    generate_conversational_answer,
    generate_grounded_answer,
    generate_ungrounded_answer,
    stream_conversational_answer,
    stream_grounded_answer,
)
from src.retrieval.query_normalize import normalize_retrieval_query
from src.retrieval.retriever import Evidence, retrieve_candidates
from src.safety.citation_faithfulness import FaithfulnessAudit, audit_citation_faithfulness
from src.safety.followups import clarifying_questions, weak_match_answer
from src.safety.guardrails import (
    EMERGENCY_BANNER_MESSAGE,
    PRESCRIPTION_REFUSAL_MESSAGE,
    check_emergency,
    check_prescription_request,
    classify_intent,
    conversational_reply,
    has_chest_pain_signal,
)
from src.safety.triage import CHEST_PAIN_SAFETY_QUESTIONS, TriageResult, classify_triage

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
    return rows[-10:]


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
    lines = [EMERGENCY_BANNER_MESSAGE]
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


def _conversational_result(query: str, history: list[dict] | None = None) -> DiagnosisResponse:
    try:
        answer = generate_conversational_answer(query, history)
    except Exception:
        answer = conversational_reply(query)
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
    )


def synthesize_retrieval_query(query: str, history: list[dict] | None = None) -> str:
    """Keep follow-up retrieval anchored to earlier symptom text in this chat."""
    if not history:
        return normalize_retrieval_query(query)
    prior: list[str] = []
    for item in history:
        if item.get("role") != "user":
            continue
        text = str(item.get("content") or "").strip()
        if not text:
            continue
        if classify_intent(text, history) == "medical" or "extra detail:" in text.lower() or "body map context" in text.lower():
            prior.append(normalize_retrieval_query(text))
    if not prior:
        return normalize_retrieval_query(query)
    if classify_intent(query, history) != "medical":
        return normalize_retrieval_query(query)
    combined = "\n".join(prior[-3:] + [normalize_retrieval_query(query)])
    return combined[:2000]


def run_pipeline(
    query: str,
    top_k: int | None = None,
    embedding_mode: str | None = None,
    chat_history: list[dict] | None = None,
) -> DiagnosisResponse:
    query = query.strip()
    history = _history_payload(chat_history)

    # --- Safety pre-check: prescription/dosage requests are refused outright ---
    prescription_check = check_prescription_request(query)
    if prescription_check.triggered:
        return DiagnosisResponse(
            query=query,
            refused=True,
            refusal_reason="prescription_or_dosage_request",
            triage=None,
            answer=PRESCRIPTION_REFUSAL_MESSAGE,
            citations=[],
            faithfulness=None,
            recommendations=["Ask a doctor or pharmacist instead of requesting a specific dose here."],
        )

    intent = classify_intent(query, history)
    if intent != "medical":
        return _conversational_result(query, history)

    # Deterministic emergency triage BEFORE retrieval so chest-pain / red-flag
    # guidance is never delayed by embeddings, reranking, or the LLM.
    early_emergency = check_emergency(query)
    early_triage = classify_triage(query, []) if early_emergency.triggered else None

    search_query = synthesize_retrieval_query(query, history)
    try:
        evidence, pool = retrieve_candidates(search_query, top_k=top_k, mode=embedding_mode)
    except Exception:
        evidence, pool = [], []
    strong = _evidence_is_strong(evidence)
    # Emergency always; evidence-based triage only when retrieval is strong.
    if early_triage and early_triage.level == "emergency":
        triage = early_triage
    elif strong:
        triage = classify_triage(query, evidence)
    else:
        triage = None

    if triage and triage.level == "emergency" and not strong:
        answer = _emergency_answer(query, with_retrieval_note=True)
        return DiagnosisResponse(
            query=query,
            refused=False,
            refusal_reason=None,
            triage=triage,
            answer=answer,
            citations=[],
            faithfulness=None,
            recommendations=[triage.guidance, *clarifying_questions(query, limit=2)],
            possible_conditions=[],
        )

    context_blocks = [_format_context_block(ev, i + 1) for i, ev in enumerate(evidence)] if strong else []
    if strong:
        answer = generate_grounded_answer(query, context_blocks, history, weak_match=False)
    else:
        answer = _weak_or_emergency_answer(query, triage)
    citations = citations_from_evidence(evidence) if strong else []
    faithfulness = audit_citation_faithfulness(answer, citations) if strong else None
    matches = (
        outcomes_for_query(query, citations, embedding_mode, citations_from_evidence(pool))
        if strong
        else []
    )
    recs = _recommendations(triage, evidence) if strong else clarifying_questions(query, limit=2)

    return DiagnosisResponse(
        query=query,
        refused=False,
        refusal_reason=None,
        triage=triage,
        answer=answer,
        citations=citations,
        faithfulness=faithfulness,
        recommendations=recs,
        possible_conditions=matches,
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
        "provider": config.resolve_llm_provider(),
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
    return payload


def iter_pipeline_stream(
    query: str,
    top_k: int | None = None,
    embedding_mode: str | None = None,
    chat_history: list[dict] | None = None,
):
    """Yield SSE-friendly events while running the same RAG + safety flow."""
    query = query.strip()
    history = _history_payload(chat_history)
    yield {"type": "status", "content": "Understanding your message..."}

    prescription_check = check_prescription_request(query)
    if prescription_check.triggered:
        result = DiagnosisResponse(
            query=query,
            refused=True,
            refusal_reason="prescription_or_dosage_request",
            triage=None,
            answer=PRESCRIPTION_REFUSAL_MESSAGE,
            citations=[],
            faithfulness=None,
            recommendations=["Ask a doctor or pharmacist instead of requesting a specific dose here."],
        )
        yield {"type": "token", "content": PRESCRIPTION_REFUSAL_MESSAGE}
        yield {"type": "done", "result": result_to_dict(result)}
        return

    intent = classify_intent(query, history)
    if intent != "medical":
        yield {"type": "status", "content": "Formulating response..."}
        chunks: list[str] = []
        try:
            for chunk in stream_conversational_answer(query, history):
                chunks.append(chunk)
                yield {"type": "token", "content": chunk}
        except Exception:
            reply = conversational_reply(query)
            yield {"type": "token", "content": reply}
            chunks = [reply]
        result = DiagnosisResponse(
            query=query,
            refused=False,
            refusal_reason=None,
            triage=None,
            answer="".join(chunks).strip() or conversational_reply(query),
            citations=[],
            faithfulness=None,
            recommendations=[],
            possible_conditions=[],
        )
        yield {"type": "done", "result": result_to_dict(result)}
        return

    # Emit emergency triage immediately — do not wait on retrieval or the LLM.
    early_emergency = check_emergency(query)
    early_triage = classify_triage(query, []) if early_emergency.triggered else None
    if early_triage:
        yield {
            "type": "triage",
            "level": early_triage.level,
            "label": early_triage.label,
            "guidance": early_triage.guidance,
            "reason": early_triage.reason,
        }

    yield {"type": "status", "content": "Searching medical knowledge base..."}
    search_query = synthesize_retrieval_query(query, history)
    try:
        evidence, pool = retrieve_candidates(search_query, top_k=top_k, mode=embedding_mode)
    except Exception:
        evidence, pool = [], []
    strong = _evidence_is_strong(evidence)
    if early_triage and early_triage.level == "emergency":
        triage = early_triage
    elif strong:
        triage = classify_triage(query, evidence)
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
        result = DiagnosisResponse(
            query=query,
            refused=False,
            refusal_reason=None,
            triage=triage,
            answer=answer,
            citations=[],
            faithfulness=None,
            recommendations=[triage.guidance, *clarifying_questions(query, limit=2)],
            possible_conditions=[],
        )
        payload = result_to_dict(result)
        yield {"type": "metadata", "recommendations": payload["recommendations"], "faithfulness": None}
        yield {"type": "done", "result": payload}
        return

    citations = citations_from_evidence(evidence) if strong else []
    possible_conditions = (
        outcomes_for_query(query, citations, embedding_mode, citations_from_evidence(pool)) if strong else []
    )
    if citations or possible_conditions:
        yield {"type": "citation", "citations": citations, "possible_conditions": possible_conditions}

    yield {"type": "status", "content": "Formulating response..."}
    chunks: list[str] = []
    if strong:
        context_blocks = [_format_context_block(ev, i + 1) for i, ev in enumerate(evidence)]
        try:
            for chunk in stream_grounded_answer(query, context_blocks, history, weak_match=False):
                chunks.append(chunk)
                yield {"type": "token", "content": chunk}
        except Exception:
            fallback = _weak_or_emergency_answer(query, triage)
            yield {"type": "token", "content": fallback}
            chunks = [fallback]
        answer = "".join(chunks).strip()
        faithfulness = audit_citation_faithfulness(answer, citations)
        recs = _recommendations(triage, evidence)
    else:
        answer = _weak_or_emergency_answer(query, triage)
        yield {"type": "token", "content": answer}
        faithfulness = None
        recs = clarifying_questions(query, limit=2)
    result = DiagnosisResponse(
        query=query,
        refused=False,
        refusal_reason=None,
        triage=triage,
        answer=answer,
        citations=citations,
        faithfulness=faithfulness,
        recommendations=recs,
        possible_conditions=possible_conditions,
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
