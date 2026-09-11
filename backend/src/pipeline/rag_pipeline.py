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
from src.llm.generator import generate_grounded_answer, generate_ungrounded_answer
from src.retrieval.retriever import Evidence, retrieve
from src.safety.citation_faithfulness import FaithfulnessAudit, audit_citation_faithfulness
from src.safety.guardrails import (
    PRESCRIPTION_REFUSAL_MESSAGE,
    check_prescription_request,
)
from src.safety.triage import TriageResult, classify_triage


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

    citations = [
        {
            "title": ev.title,
            "source": ev.source,
            "url": ev.url,
            "condition": ev.condition,
            "relevance_score": round(ev.relevance_score, 4),
        }
        for ev in evidence
    ]

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
    )


def run_no_rag_baseline(query: str) -> str:
    """The same query answered with NO retrieval - used only for the
    hallucination-comparison evaluation (Objective 4), never in the real app."""
    return generate_ungrounded_answer(query)


if __name__ == "__main__":
    import json

    test_query = "I have a burning sensation when I pee and need to go often"
    result = run_pipeline(test_query)
    print(json.dumps(result.__dict__, default=lambda o: o.__dict__, indent=2))
