from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from src.safety.guardrails import classify_intent
from src.pipeline.rag_pipeline import run_pipeline, synthesize_retrieval_query


def test_classify_intent_skips_greetings_and_objects():
    assert classify_intent("hello") == "conversational"
    assert classify_intent("I am good") == "conversational"
    assert classify_intent("thank you") == "conversational"
    assert classify_intent("this is a table") == "off_topic"


def test_classify_intent_keeps_symptoms_and_followups():
    assert classify_intent("I have a cough and mild fever") == "medical"
    history = [
        {"role": "user", "content": "I have a cough", "possible_conditions": [{"condition": "cold"}]},
        {"role": "assistant", "content": "Possible match: common cold", "possible_conditions": [{"condition": "cold"}]},
    ]
    assert classify_intent("I also have a mild fever with that", history) == "medical"
    assert classify_intent("ok", history) == "conversational"


def test_synthesize_retrieval_query_anchors_followup():
    history = [{"role": "user", "content": "I have a cough"}]
    combined = synthesize_retrieval_query("I also have a mild fever with that", history)
    assert "cough" in combined.lower()
    assert "fever" in combined.lower()


def test_non_medical_pipeline_skips_retrieval(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    def boom(*_args, **_kwargs):
        raise AssertionError("non-medical queries must not retrieve")

    monkeypatch.setattr(rp, "retrieve_candidates", boom)
    result = run_pipeline("hello")
    assert result.triage is None
    assert result.citations == []
    assert result.possible_conditions == []
    assert result.answer


def test_weak_evidence_does_not_invent_matches(monkeypatch):
    from src.pipeline import rag_pipeline as rp
    from src.retrieval.retriever import Evidence

    weak = [
        Evidence(
            text="unrelated furniture notes",
            title="Table",
            source="Sample",
            url="",
            condition="table",
            triage_level="self_care",
            relevance_score=0.02,
            doc_id="table",
            vector_score=0.05,
        )
    ]

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_args, **_kwargs: (weak, weak))
    monkeypatch.setattr(rp, "generate_grounded_answer", lambda *_args, **_kwargs: "Please describe the symptoms more clearly.")
    result = run_pipeline("I have a cough")
    assert result.possible_conditions == []
    assert result.citations == []
    assert result.triage is None
