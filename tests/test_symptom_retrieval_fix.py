"""
Regression tests for body-map context, symptom retrieval, fallback, and
chest-pain emergency guidance. Synthetic inputs only — no real patient data.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from src.pipeline.rag_pipeline import (
    _evidence_is_strong,
    run_pipeline,
    synthesize_retrieval_query,
)
from src.retrieval.query_normalize import normalize_retrieval_query, parse_body_map
from src.retrieval.retriever import Evidence
from src.safety.followups import clarifying_questions
from src.safety.guardrails import check_emergency, has_chest_pain_signal

ABDOMEN_MAP = (
    "Body map context (user-described discomfort, not a diagnosis): locations = Abdomen."
)
HEADACHE_MAP = (
    "Body map context (user-described discomfort, not a diagnosis): "
    "locations = Head; symptoms = Headache."
)
CHEST_PAIN = "left side chest pain"
GENERIC_FALLBACK_SNIPPET = "fever, pain, or breathlessness"


def test_abdomen_body_map_reaches_normalized_retrieval_query():
    free, locations, symptoms = parse_body_map(ABDOMEN_MAP)
    assert locations == ["Abdomen"]
    assert symptoms == []
    normalized = normalize_retrieval_query(ABDOMEN_MAP)
    assert "abdomen" in normalized.lower()
    assert "body map context" not in normalized.lower()
    search = synthesize_retrieval_query(ABDOMEN_MAP)
    assert "abdomen" in search.lower()


def test_headache_body_map_preserves_location_and_symptom():
    free, locations, symptoms = parse_body_map(HEADACHE_MAP)
    assert locations == ["Head"]
    assert symptoms == ["Headache"]
    normalized = normalize_retrieval_query(HEADACHE_MAP)
    assert "headache" in normalized.lower()
    assert "head" in normalized.lower()


def test_left_sided_chest_pain_preserves_location_and_symptom():
    normalized = normalize_retrieval_query(CHEST_PAIN)
    assert "chest" in normalized.lower()
    assert "pain" in normalized.lower()
    assert has_chest_pain_signal(CHEST_PAIN)
    assert not check_emergency(CHEST_PAIN).triggered


def test_evidence_strength_accepts_strong_vector_even_if_rerank_low():
    weak_rerank = [
        Evidence(
            text="Tension-type headache is a common cause of head pain.",
            title="Mild Tension Headache",
            source="Sample",
            url="",
            condition="Tension Headache",
            triage_level="self_care",
            relevance_score=0.05,
            doc_id="tension_headache",
            vector_score=0.55,
        )
    ]
    assert _evidence_is_strong(weak_rerank) is True


def test_evidence_strength_rejects_truly_weak_hits():
    junk = [
        Evidence(
            text="unrelated furniture notes",
            title="Table",
            source="Sample",
            url="",
            condition="table",
            triage_level="self_care",
            relevance_score=0.01,
            doc_id="table",
            vector_score=0.12,
        )
    ]
    assert _evidence_is_strong(junk) is False


def test_relevant_retrieval_avoids_generic_fallback(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    hits = [
        Evidence(
            text="Tension-type headache often presents with bilateral head pressure. Self-care includes rest and hydration. See a doctor if sudden severe headache develops.",
            title="Mild Tension Headache",
            source="Sample KB",
            url="",
            condition="Tension Headache",
            triage_level="self_care",
            relevance_score=0.4,
            doc_id="tension_headache",
            vector_score=0.6,
        )
    ]

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: (hits, hits))
    result = run_pipeline(HEADACHE_MAP)
    assert result.citations
    assert result.possible_conditions
    assert GENERIC_FALLBACK_SNIPPET not in result.answer.lower()
    assert any("headache" in (c.get("condition") or "").lower() or "headache" in (c.get("title") or "").lower() for c in result.citations)


def test_insufficient_evidence_honest_fallback_without_invented_conditions(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    weak = [
        Evidence(
            text="unrelated furniture notes about oak tables",
            title="Table Care",
            source="Sample",
            url="",
            condition="table",
            triage_level="self_care",
            relevance_score=0.01,
            doc_id="table",
            vector_score=0.1,
        )
    ]
    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: (weak, weak))
    monkeypatch.setattr(rp, "can_use_llm_kb_fallback", lambda: False)
    result = run_pipeline("I have a mild cough that is hard to pin down further")
    assert result.citations == []
    assert result.possible_conditions == []
    assert result.triage is None
    assert "close enough match" in result.answer.lower() or "how long" in result.answer.lower()
    assert "(Source:" not in result.answer
    assert GENERIC_FALLBACK_SNIPPET not in result.answer.lower()


def test_citations_correspond_to_retrieved_sources(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    hits = [
        Evidence(
            text="Gastritis may cause upper abdominal discomfort. See a doctor for ongoing burning. Seek emergency care for vomiting blood.",
            title="Gastritis",
            source="Sample KB",
            url="https://example.test/gastritis",
            condition="Gastritis",
            triage_level="consult_doctor",
            relevance_score=0.5,
            doc_id="gastritis",
            vector_score=0.62,
        )
    ]
    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: (hits, hits))
    result = run_pipeline(ABDOMEN_MAP)
    assert result.citations
    assert result.citations[0]["title"] == "Gastritis"
    assert result.citations[0]["source"] == "Sample KB"
    assert result.citations[0]["url"] == "https://example.test/gastritis"


def test_emergency_fires_even_when_retrieval_is_empty(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: ([], []))
    result = run_pipeline("crushing chest pain spreading to my jaw with sweating")
    assert result.triage is not None
    assert result.triage.level == "emergency"
    assert "112" in (result.answer + " " + (result.triage.guidance or ""))
    assert "call 112" not in (result.answer or "").lower()
    assert GENERIC_FALLBACK_SNIPPET not in result.answer.lower()


def test_left_chest_pain_emergency_not_blocked_by_retrieval_failure(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    def boom(*_a, **_k):
        raise RuntimeError("vector store unavailable")

    monkeypatch.setattr(rp, "retrieve_candidates", boom)
    result = run_pipeline(CHEST_PAIN)
    assert result.triage is not None
    assert result.triage.level == "consult_doctor"
    assert "112" in (result.answer + " " + (result.triage.guidance or ""))
    assert "heart attack" not in result.answer.lower()


def test_followups_are_symptom_relevant():
    abdomen_qs = clarifying_questions(ABDOMEN_MAP)
    assert any("abdominal" in q.lower() or "abdomen" in q.lower() for q in abdomen_qs)
    assert not any("fever" in q.lower() and "breath" in q.lower() for q in abdomen_qs)

    head_qs = clarifying_questions(HEADACHE_MAP)
    assert any("headache" in q.lower() for q in head_qs)

    chest_qs = clarifying_questions(CHEST_PAIN)
    assert any("chest" in q.lower() or "breath" in q.lower() for q in chest_qs)


def test_followup_history_retained_in_retrieval_query():
    history = [
        {"role": "user", "content": HEADACHE_MAP},
        {"role": "assistant", "content": "Tell me more about the headache."},
    ]
    combined = synthesize_retrieval_query("Extra detail: lasting 1-2 days; age group 18-40; worse with Light or sound.", history)
    assert "headache" in combined.lower()


def test_retrieval_service_failure_handled_gracefully(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    def boom(*_a, **_k):
        raise RuntimeError("embedding timeout")

    monkeypatch.setattr(rp, "retrieve_candidates", boom)
    monkeypatch.setattr(rp, "can_use_llm_kb_fallback", lambda: False)
    result = run_pipeline("I have a mild sore throat")
    assert result.refused is False
    assert result.citations == []
    assert result.answer
    assert result.triage is None
