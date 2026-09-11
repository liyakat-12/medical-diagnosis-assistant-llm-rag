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
from src.llm.generator import generate_grounded_answer, generate_ungrounded_answer, stream_grounded_answer
from src.retrieval.retriever import Evidence, retrieve
from src.safety.citation_faithfulness import FaithfulnessAudit, audit_citation_faithfulness
from src.safety.guardrails import (
    PRESCRIPTION_REFUSAL_MESSAGE,
    check_prescription_request,
)
from src.safety.triage import TriageResult, classify_triage

OUTCOME_LIMIT = 4
OUTCOME_SEARCH_K = 12


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


def outcomes_for_query(query: str, citations: list[dict], embedding_mode: str | None = None) -> list[dict]:
    rows = build_possible_conditions(citations)
    if len(rows) >= OUTCOME_LIMIT:
        return rows
    extra = retrieve(query, top_k=OUTCOME_SEARCH_K, mode=embedding_mode)
    return build_possible_conditions(citations_from_evidence(extra))


def run_pipeline(query: str, top_k: int | None = None, embedding_mode: str | None = None) -> DiagnosisResponse:
    query = query.strip()

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

    # --- Retrieval ---
    evidence = retrieve(query, top_k=top_k, mode=embedding_mode)

    # --- Triage classification (emergency override happens here) ---
    triage = classify_triage(query, evidence)

    # --- Generation, grounded in retrieved evidence ---
    context_blocks = [_format_context_block(ev, i + 1) for i, ev in enumerate(evidence)]
    answer = generate_grounded_answer(query, context_blocks)

    citations = citations_from_evidence(evidence)
    faithfulness = audit_citation_faithfulness(answer, citations)

    return DiagnosisResponse(
        query=query,
        refused=False,
        refusal_reason=None,
        triage=triage,
        answer=answer,
        citations=citations,
        faithfulness=faithfulness,
        recommendations=_recommendations(triage, evidence),
        possible_conditions=outcomes_for_query(query, citations, embedding_mode),
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
        "possible_conditions": result.possible_conditions or build_possible_conditions(result.citations),
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


def iter_pipeline_stream(query: str, top_k: int | None = None, embedding_mode: str | None = None):
    """Yield SSE-friendly events while running the same RAG + safety flow."""
    query = query.strip()
    yield {"type": "status", "content": "Analyzing your symptoms..."}

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

    yield {"type": "status", "content": "Retrieving medical references..."}
    evidence = retrieve(query, top_k=top_k, mode=embedding_mode)
    triage = classify_triage(query, evidence)
    if triage:
        yield {
            "type": "triage",
            "level": triage.level,
            "label": triage.label,
            "guidance": triage.guidance,
        }

    citations = citations_from_evidence(evidence)
    possible_conditions = outcomes_for_query(query, citations, embedding_mode)
    yield {"type": "citation", "citations": citations, "possible_conditions": possible_conditions}

    context_blocks = [_format_context_block(ev, i + 1) for i, ev in enumerate(evidence)]
    chunks: list[str] = []
    for chunk in stream_grounded_answer(query, context_blocks):
        chunks.append(chunk)
        yield {"type": "token", "content": chunk}
    answer = "".join(chunks).strip()
    faithfulness = audit_citation_faithfulness(answer, citations)
    result = DiagnosisResponse(
        query=query,
        refused=False,
        refusal_reason=None,
        triage=triage,
        answer=answer,
        citations=citations,
        faithfulness=faithfulness,
        recommendations=_recommendations(triage, evidence),
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
