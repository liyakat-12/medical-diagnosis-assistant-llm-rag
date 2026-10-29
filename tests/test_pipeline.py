"""
Lightweight unit tests that don't require any LLM API key - they cover
ingestion, chunking, and the safety/guardrail rule layer.

Run with:
    python -m pytest tests/ -v
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from src.ingestion.loader import build_chunks, chunk_text, load_documents
from src.safety.citation_faithfulness import audit_citation_faithfulness
from src.safety.guardrails import check_emergency, check_prescription_request


def test_load_documents_finds_all_sample_docs():
    docs = load_documents()
    assert len(docs) == 1017
    ids = {d.id for d in docs}
    assert "heart_attack" in ids
    assert "common_cold" in ids
    assert "norovirus" in ids
    assert "fabry_disease" in ids


def test_every_document_has_required_metadata():
    for doc in load_documents():
        assert doc.title
        assert doc.source
        assert doc.triage_level in {"self_care", "consult_doctor", "emergency"}
        assert doc.body


def test_chunk_text_splits_long_text():
    long_text = " ".join(["word"] * 500)
    chunks = chunk_text(long_text, chunk_size=100, overlap=20)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c.split()) <= 100


def test_chunk_text_keeps_short_text_whole():
    short_text = "This is a short passage."
    chunks = chunk_text(short_text, chunk_size=100, overlap=20)
    assert chunks == [short_text]


def test_build_chunks_preserves_citation_metadata():
    chunks = build_chunks()
    assert len(chunks) > 0
    for c in chunks[:5]:
        assert c.source
        assert c.title
        assert c.metadata["doc_id"] == c.doc_id


def test_emergency_guardrail_catches_heart_attack_description():
    result = check_emergency("I have crushing chest pain spreading to my arm and I'm sweating")
    assert result.triggered


def test_emergency_guardrail_does_not_flag_common_cold():
    result = check_emergency("I have a runny nose and mild sore throat since yesterday")
    assert not result.triggered


def test_prescription_guardrail_catches_dosage_question():
    result = check_prescription_request("How many mg of ibuprofen should I take for this?")
    assert result.triggered


def test_prescription_guardrail_ignores_normal_symptom_question():
    result = check_prescription_request("I have a headache and feel nauseous, what could this be?")
    assert not result.triggered


def test_prescription_guardrail_ignores_benign_medication_info():
    assert not check_prescription_request("What is paracetamol used for?").triggered
    assert not check_prescription_request("Can you explain what ibuprofen is?").triggered


def test_faithfulness_marks_cited_retrieved_claim_supported():
    answer = (
        "1. One possible condition may be related to Common Cold (Source: Common Cold).\n\n"
        "This is not a diagnosis — please consult a qualified healthcare professional."
    )
    retrieved = [{"title": "Common Cold", "condition": "Common Cold", "source": "CDC"}]
    audit = audit_citation_faithfulness(answer, retrieved)
    assert audit.verdict == "pass"
    assert audit.supported_count == 1
    assert audit.unsupported_count == 0
    assert audit.coverage == 1.0


def test_faithfulness_flags_uncited_claim():
    answer = "This may be related to pneumonia and you should worry."
    retrieved = [{"title": "Common Cold", "condition": "Common Cold", "source": "CDC"}]
    audit = audit_citation_faithfulness(answer, retrieved)
    assert audit.unsupported_count == 1
    assert audit.verdict == "fail"


def test_faithfulness_flags_citation_not_in_retrieval():
    answer = "This may be related to Pneumonia (Source: Pneumonia)."
    retrieved = [{"title": "Common Cold", "condition": "Common Cold", "source": "CDC"}]
    audit = audit_citation_faithfulness(answer, retrieved)
    assert audit.fabricated_count == 1
    assert audit.verdict == "fail"


def test_match_percents_sum_to_100():
    from src.pipeline.rag_pipeline import match_percents

    percents = match_percents([0.82, 0.61, 0.44, 0.29])
    assert sum(percents) == 100
    assert len(percents) == 4
    assert percents[0] >= percents[-1]


def test_rerank_puts_best_chunk_first(monkeypatch):
    from src.retrieval.reranker import rerank_chunks
    from src.retrieval.vector_store import RetrievedChunk

    chunks = [
        RetrievedChunk("a", "wrong passage", 0.1, {"doc_id": "a"}),
        RetrievedChunk("b", "correct passage", 0.4, {"doc_id": "b"}),
        RetrievedChunk("c", "other passage", 0.2, {"doc_id": "c"}),
    ]

    class FakeModel:
        def predict(self, pairs, show_progress_bar=False, **_kwargs):
            return [0.1, 4.0, 0.2]

    monkeypatch.setattr("src.retrieval.reranker._load_model", lambda: FakeModel())
    ranked = rerank_chunks("symptoms", chunks, top_k=2)
    assert ranked[0].chunk_id == "b"
    assert len(ranked) == 2


def test_outcomes_for_query_reuses_pool_without_second_retrieve(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    def boom(*_args, **_kwargs):
        raise AssertionError("should not run a second retrieve")

    monkeypatch.setattr(rp, "retrieve", boom, raising=False)
    rows = rp.outcomes_for_query(
        "I have a cough",
        [{"condition": "cold", "title": "Cold", "source": "CDC", "url": "", "relevance_score": 0.9}],
        pool=[
            {"condition": "cold", "title": "Cold", "source": "CDC", "url": "", "relevance_score": 0.9},
            {"condition": "flu", "title": "Flu", "source": "CDC", "url": "", "relevance_score": 0.5},
        ],
    )
    assert [row["condition"] for row in rows] == ["Cold", "Flu"]
    assert "match_percent" not in rows[0]


def test_build_possible_conditions_returns_four_unique():
    from src.pipeline.rag_pipeline import build_possible_conditions

    citations = [
        {"condition": f"Condition {i}", "title": f"Title {i}", "source": "CDC", "url": "", "relevance_score": 0.9 - (i * 0.1)}
        for i in range(6)
    ]
    rows = build_possible_conditions(citations)
    assert len(rows) == 4
    assert "match_percent" not in rows[0]
    assert rows[0]["condition"] == "Condition 0"
    assert rows[0]["evidence_match_label"] == "Closest evidence match"
    assert rows[1]["evidence_match_label"] == "Related evidence match"
    assert "match_percent" not in rows[0]


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
