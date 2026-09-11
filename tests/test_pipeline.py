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
sys.path.insert(0, str(ROOT_DIR))

from src.ingestion.loader import build_chunks, chunk_text, load_documents
from src.safety.citation_faithfulness import audit_citation_faithfulness
from src.safety.guardrails import check_emergency, check_prescription_request


def test_load_documents_finds_all_sample_docs():
    docs = load_documents()
    assert len(docs) == 40
    ids = {d.id for d in docs}
    assert "heart_attack" in ids
    assert "common_cold" in ids


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


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
