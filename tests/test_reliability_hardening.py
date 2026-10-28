"""Regression tests for conversation-state, leftover cards, and safety."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from src.pipeline.conversation_state import build_conversation_state
from src.pipeline.rag_pipeline import (
    _retain_relevant_evidence,
    citations_from_evidence,
    result_to_dict,
    run_pipeline,
    synthesize_retrieval_query,
)
from src.retrieval.retriever import Evidence
from src.safety.guardrails import classify_intent

from chat_asserts import assert_general_reply
from src.safety.citation_faithfulness import audit_citation_faithfulness as audit_claims


KNEE_HISTORY = [
    {
        "role": "user",
        "content": "I have pain in my knee",
        "possible_conditions": [{"condition": "Knee Pain", "match_percent": 54}],
    },
    {
        "role": "assistant",
        "content": "Pain is usually in the front or inner knee.",
        "possible_conditions": [{"condition": "Knee Pain"}],
        "triage": {"level": "self_care"},
    },
]
HEADACHE_HISTORY = [
    {
        "role": "user",
        "content": "What causes headaches?",
        "possible_conditions": [{"condition": "Headache Possibilities"}],
    },
    {
        "role": "assistant",
        "content": "See a doctor for a new pattern of headaches.",
        "possible_conditions": [{"condition": "Tension Headache"}],
        "triage": {"level": "self_care"},
    },
]
COUGH = Evidence(
    text="A humidifier can help in a dry room. See a doctor if you have chest pain.",
    title="Dry Cough at Night",
    source="NHS - Cough",
    url="https://example.test/cough",
    condition="Dry Cough",
    triage_level="self_care",
    relevance_score=0.8,
    doc_id="dry_cough_at_night",
    vector_score=0.7,
)
KNEE = Evidence(
    text="Knee pain when walking often eases with rest and supportive shoes.",
    title="Knee Pain When Walking",
    source="NHS - Knee pain",
    url="https://example.test/knee",
    condition="Knee Pain",
    triage_level="self_care",
    relevance_score=0.75,
    doc_id="knee_pain_walking",
    vector_score=0.65,
)
WEAK = Evidence(
    text="unrelated furniture notes",
    title="Table Care",
    source="Sample",
    url="",
    condition="table",
    triage_level="self_care",
    relevance_score=0.02,
    doc_id="table",
    vector_score=0.05,
)


def test_conversation_state_labels_follow_up_and_new_complaint():
    follow = build_conversation_state("it is worse on the left side", KNEE_HISTORY)
    assert follow.status == "follow_up"
    assert follow.reuse_history is True
    assert "knee" in follow.search_query.lower()

    fresh = build_conversation_state("I have a dry cough at night", KNEE_HISTORY)
    assert fresh.status == "new_complaint"
    assert fresh.reuse_history is False
    assert "knee" not in fresh.search_query.lower()
    assert fresh.generation_history == []

    off = build_conversation_state("Which is better, a car or a bike?", HEADACHE_HISTORY)
    assert off.status == "non_medical"
    assert off.reuse_history is False
    assert all(not item.get("possible_conditions") for item in off.generation_history)
    assert all(not item.get("triage") for item in off.generation_history)


def test_car_versus_bike_after_medical_chat_has_no_cards():
    result = run_pipeline("Which is better, a car or a bike?", chat_history=HEADACHE_HISTORY)
    assert_general_reply(result, "car", "bike")
    assert "headache" not in result.answer.lower()


def test_code_input_is_non_medical():
    assert classify_intent('print("my name is abd")') == "non_medical"
    result = run_pipeline('print("my name is abd")', chat_history=KNEE_HISTORY)
    assert_general_reply(result, "print")
    assert "knee" not in result.answer.lower()


def test_advice_followup_keeps_active_complaint():
    history = [
        {
            "role": "user",
            "content": "I have a headache after a long day at the screen",
            "possible_conditions": [{"condition": "Headache"}],
        }
    ]
    state = build_conversation_state("What should I do?", history)
    assert state.status == "follow_up"
    assert state.reuse_history is True
    assert "headache" in state.search_query.lower()


def test_new_complaint_shape_in_same_topic_does_not_reuse_cough():
    history = [{"role": "user", "content": "I have a dry cough at night"}]
    state = build_conversation_state("I have chest pain", history)
    assert state.reuse_history is False
    assert "cough" not in state.search_query.lower()


def test_symptom_followup_keeps_active_complaint(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    monkeypatch.setattr(rp, "retrieve_candidates", lambda query, *_a, **_k: ( [KNEE], [KNEE] ))
    monkeypatch.setattr(
        rp,
        "generate_grounded_answer",
        lambda *_a, **_k: "Possible leftover knee strain (Source: Knee Pain When Walking). Not a diagnosis — see a clinician if needed.",
    )
    combined = synthesize_retrieval_query("worse on the left side", KNEE_HISTORY)
    assert "knee" in combined.lower()
    result = run_pipeline("worse on the left side", chat_history=KNEE_HISTORY)
    assert result.possible_conditions
    assert "knee" in result.possible_conditions[0]["condition"].lower()


def test_new_complaint_does_not_search_or_keep_old_cards(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    def fake_retrieve(query, *_a, **_k):
        assert "knee" not in query.lower()
        return [COUGH], [COUGH, KNEE]

    monkeypatch.setattr(rp, "retrieve_candidates", fake_retrieve)
    monkeypatch.setattr(
        rp,
        "generate_grounded_answer",
        lambda *_a, **_k: "A leftover viral cough may linger (Source: Dry Cough at Night). Not a diagnosis — see a clinician if needed.",
    )
    result = run_pipeline("I have a dry cough at night", chat_history=KNEE_HISTORY)
    titles = " ".join(row.get("title") or "" for row in result.citations).lower()
    conditions = " ".join(row.get("condition") or "" for row in result.possible_conditions).lower()
    assert "knee" not in titles
    assert "knee" not in conditions
    assert "cough" in titles or "cough" in conditions


def test_unrelated_notes_are_dropped_instead_of_reused():
    kept = _retain_relevant_evidence("i have pain in my knee", [COUGH, WEAK])
    assert kept == []


def test_chest_pain_emergency_independent_of_retrieval(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    def boom(*_a, **_k):
        raise AssertionError("emergency must not call Groq")

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("store down")))
    monkeypatch.setattr(rp, "can_use_llm_kb_fallback", lambda: True)
    monkeypatch.setattr(rp, "generate_kb_miss_bundle", boom)
    result = run_pipeline("I have chest pain", chat_history=[{"role": "user", "content": "I have a dry cough at night"}])
    assert result.triage is not None
    assert result.triage.level == "emergency"
    assert "112" in result.answer
    assert result.possible_conditions == []
    assert result.citations == []
    assert "humidifier" not in " ".join(result.recommendations).lower()


def test_empty_retrieval_asks_clarifying_questions(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: ([], []))
    monkeypatch.setattr(rp, "can_use_llm_kb_fallback", lambda: False)
    result = run_pipeline("I have a sore throat after a cold")
    assert result.possible_conditions == []
    assert result.citations == []
    assert result.evidence_origin == "none"
    assert result.recommendations
    assert "how long" in result.answer.lower() or "close enough match" in result.answer.lower()


def test_groq_failure_after_notes_still_explains_from_notes(monkeypatch):
    from src.llm import generator as gen
    from src.llm.kb_miss import LOOKUP_FAILED_MESSAGE
    from src.pipeline import rag_pipeline as rp

    sciatica = Evidence(
        text="Leg pain from the back when sitting may be sciatica. See a doctor if it lasts weeks or the foot is weak.",
        title="Leg Pain From the Back When Sitting",
        source="NHS - Sciatica",
        url="https://example.test/sciatica",
        condition="Sciatica When Sitting",
        triage_level="consult_doctor",
        relevance_score=0.7,
        doc_id="sciatica_sitting",
        vector_score=0.6,
    )

    def fail(*_a, **_k):
        raise RuntimeError("429 rate limit")

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: ([sciatica], [sciatica]))
    monkeypatch.setattr(gen, "_call_llm", fail)
    result = run_pipeline("I have leg pain when sitting")
    assert LOOKUP_FAILED_MESSAGE not in result.answer
    assert "could not finish this medical lookup" not in result.answer.lower()
    assert result.citations
    assert "leg pain from the back when sitting" in result.answer.lower()
    assert result.evidence_origin == "knowledge_base"
    assert result.possible_conditions


def test_stream_uses_notes_when_groq_stream_fails(monkeypatch):
    from src.llm.kb_miss import LOOKUP_FAILED_MESSAGE
    from src.pipeline import rag_pipeline as rp
    from src.pipeline.rag_pipeline import iter_pipeline_stream

    def fail(*_a, **_k):
        raise RuntimeError("stream reset")

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: ([KNEE], [KNEE]))
    monkeypatch.setattr(rp, "stream_grounded_answer", fail)
    tokens = []
    final = None
    for event in iter_pipeline_stream("I have pain in my knee"):
        if event.get("type") == "token":
            tokens.append(event.get("content") or "")
        if event.get("type") == "done":
            final = event.get("result") or {}
    answer = "".join(tokens)
    assert LOOKUP_FAILED_MESSAGE not in answer
    assert final is not None
    assert LOOKUP_FAILED_MESSAGE not in (final.get("answer") or "")
    assert final.get("citations")
    assert final.get("evidence_origin") == "knowledge_base"


def test_groq_failure_does_not_invent_matches(monkeypatch):
    from src.llm import kb_miss as kb
    from src.pipeline import rag_pipeline as rp

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: ([WEAK], [WEAK]))
    monkeypatch.setattr(rp, "can_use_llm_kb_fallback", lambda: True)
    monkeypatch.setattr(kb, "can_use_llm_kb_fallback", lambda: True)
    monkeypatch.setattr(kb, "medical_llm_status", lambda: "ready")

    def fail(*_a, **_k):
        raise RuntimeError("429 rate limit")

    monkeypatch.setattr(kb, "_call_llm", fail)
    monkeypatch.setattr(rp, "generate_kb_miss_bundle", kb.generate_kb_miss_bundle)
    result = run_pipeline("itchy nose after dust")
    assert result.possible_conditions == []
    assert result.evidence_origin == "none"
    assert not any((row.get("url") or "").startswith("http") for row in result.citations)


def test_citation_audit_rejects_invented_source():
    citations = citations_from_evidence([KNEE])
    audit = audit_claims(
        "This may be a leftover viral cough (Source: Made-Up Hospital Note).",
        citations,
    )
    assert audit.fabricated_count >= 1
    assert audit.verdict in {"fail", "partial"}

    supported = audit_claims(
        "This may be leftover knee strain (Source: Knee Pain When Walking). Not a diagnosis — see a clinician if needed.",
        citations,
    )
    assert supported.supported_count >= 1
    assert supported.fabricated_count == 0


def test_match_percent_is_retrieval_share_not_diagnosis():
    from src.pipeline.rag_pipeline import match_percents

    percents = match_percents([0.8, 0.2])
    assert percents == [80, 20]
    assert sum(percents) == 100


def test_pipeline_records_stage_timings(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: ([KNEE], [KNEE]))
    monkeypatch.setattr(
        rp,
        "generate_grounded_answer",
        lambda *_a, **_k: "Possible leftover knee strain (Source: Knee Pain When Walking). Not a diagnosis — see a clinician if needed.",
    )
    result = run_pipeline("I have pain in my knee")
    payload = result_to_dict(result)
    for key in ("classify_ms", "retrieve_ms", "generate_ms", "total_ms"):
        assert key in result.timings
        assert result.timings[key] >= 0
        assert key in payload["timings"]
    assert result.timings["total_ms"] >= result.timings["classify_ms"]
