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
  5. Package everything (answer, triage, citations, disclaimer) into one
     response object for the API/UI layer.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src import config
from src.llm.generator import generate_grounded_answer, generate_ungrounded_answer
from src.retrieval.retriever import Evidence, retrieve
from src.safety.guardrails import (
    PRESCRIPTION_REFUSAL_MESSAGE,
    check_prescription_request,
)
from src.safety.triage import TriageResult, classify_triage


@dataclass
class DiagnosisResponse:
    query: str
    refused: bool
    refusal_reason: str | None
    triage: TriageResult | None
    answer: str
    citations: list[dict] = field(default_factory=list)
    disclaimer: str = config.DISCLAIMER


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

    return DiagnosisResponse(
        query=query,
        refused=False,
        refusal_reason=None,
        triage=triage,
        answer=answer,
        citations=citations,
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
