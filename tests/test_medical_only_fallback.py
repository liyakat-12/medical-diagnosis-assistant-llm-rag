from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from src.llm.kb_miss import LOOKUP_FAILED_MESSAGE, MISSING_KEY_MESSAGE, parse_kb_miss_payload
from src.pipeline.rag_pipeline import result_to_dict, run_pipeline
from src.retrieval.retriever import Evidence
from src.safety.guardrails import (
    AMBIGUOUS_REPLY,
    GREETING_REPLY,
    THANKS_REPLY,
    classify_intent,
)

from chat_asserts import assert_general_reply

STRONG = [
    Evidence(
        text="A dry cough at night may follow a leftover cold. Rest and fluids help. See a doctor if it lasts three weeks.",
        title="Dry Cough at Night",
        source="Sample KB",
        url="https://example.test/cough",
        condition="Dry Cough",
        triage_level="self_care",
        relevance_score=0.6,
        doc_id="dry_cough_at_night",
        vector_score=0.7,
    )
]
WEAK = [
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
SAMPLE_JSON = json.dumps(
    {
        "answer": "This may be a common cold.",
        "triage": "self_care",
        "recommendations": ["Rest and drink fluids.", "See a doctor if breathing is hard."],
        "matches": [
            {"condition": "Common cold", "weight": 4},
            {"condition": "Allergic rhinitis", "weight": 2},
        ],
    }
)


def test_medical_question_covered_by_notes(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: (STRONG, STRONG))
    monkeypatch.setattr(rp, "generate_grounded_answer", lambda *_a, **_k: "Possible match: leftover cold (Source: Dry Cough at Night). Not a diagnosis — see a clinician if needed.")
    result = run_pipeline("I have a dry cough at night")
    assert result.evidence_origin == "knowledge_base"
    assert result.citations
    assert result.citations[0]["title"] == "Dry Cough at Night"
    assert result.possible_conditions
    payload = result_to_dict(result)
    assert set(payload) >= {"answer", "citations", "recommendations", "possible_conditions", "triage", "disclaimer"}


def test_medical_question_absent_from_notes_uses_groq(monkeypatch):
    from src.llm import kb_miss as kb
    from src.pipeline import rag_pipeline as rp

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: (WEAK, WEAK))
    monkeypatch.setattr(rp, "can_use_llm_kb_fallback", lambda: True)
    monkeypatch.setattr(kb, "medical_llm_status", lambda: "ready")
    monkeypatch.setattr(kb, "_call_llm", lambda *_a, **_k: SAMPLE_JSON)
    monkeypatch.setattr(rp, "generate_kb_miss_bundle", kb.generate_kb_miss_bundle)
    result = run_pipeline("itchy nose and sneezing after dusting")
    assert result.evidence_origin == "llm"
    assert "general" in result.answer.lower()
    assert any("not verified" in f"{row.get('title') or ''} {row.get('source') or ''}".lower() for row in result.citations)
    assert all(not (row.get("url") or "").startswith("http") for row in result.citations)


def test_partial_coverage_keeps_kb_citations_and_marks_general_ai(monkeypatch):
    from src.pipeline import rag_pipeline as rp
    from src.safety.citation_faithfulness import FaithfulnessAudit

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: (STRONG, STRONG))
    monkeypatch.setattr(rp, "generate_grounded_answer", lambda *_a, **_k: "Possible leftover cold (Source: Dry Cough at Night). It may also be asthma. Not a diagnosis — see a clinician if needed.")
    monkeypatch.setattr(
        rp,
        "audit_citation_faithfulness",
        lambda *_a, **_k: FaithfulnessAudit(
            coverage=0.5,
            claim_count=2,
            supported_count=1,
            unsupported_count=1,
            fabricated_count=0,
            verdict="partial",
            summary="one unsupported claim",
        ),
    )
    result = run_pipeline("I have a dry cough at night")
    assert result.evidence_origin == "mixed"
    assert any(row.get("title") == "Dry Cough at Night" for row in result.citations)
    assert any("not verified against the knowledge base" in (row.get("title") or "").lower() for row in result.citations)


def test_greeting_hi_does_not_retrieve(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no retrieve")))
    result = run_pipeline("Hi")
    assert classify_intent("Hi") == "greeting"
    assert result.answer == GREETING_REPLY
    assert result.possible_conditions == []
    assert result.citations == []
    assert result.triage is None


def test_thank_you_is_greeting():
    assert classify_intent("thank you") == "greeting"
    result = run_pipeline("thank you")
    assert result.answer == THANKS_REPLY
    assert result.possible_conditions == []


def test_travel_and_distance_are_non_medical(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no retrieve")))
    assert classify_intent("I want to travel from Bengaluru to Delhi.") == "non_medical"
    assert classify_intent("What is the distance from Bengaluru to Delhi?") == "non_medical"
    result = run_pipeline("What is the distance from Bengaluru to Delhi?")
    assert_general_reply(result, "travel")


def test_car_versus_bike_is_non_medical():
    assert classify_intent("Which is better, a car or a bike?") == "non_medical"
    result = run_pipeline("Which is better, a car or a bike?")
    assert_general_reply(result, "car", "bike")


def test_similar_choice_questions_are_non_medical():
    assert classify_intent("What's better, tea or a bike?") == "non_medical"
    assert classify_intent("Car vs bike") == "non_medical"
    assert classify_intent("Should I buy a car or a bike?") == "non_medical"
    result = run_pipeline("Which one is better, a phone or a laptop?")
    assert_general_reply(result)


def test_coding_and_weather_are_non_medical():
    assert classify_intent("Write Python code") == "non_medical"
    assert classify_intent("What is the weather today?") == "non_medical"
    result = run_pipeline("Tell me about a laptop.")
    assert_general_reply(result, "laptop")


def test_medical_symptoms_inside_travel_context_stay_medical():
    assert classify_intent("I have pain when riding my bike") == "medical"
    assert classify_intent("Which is better for knee pain, rest or ice?") == "medical"
    assert classify_intent("I feel dizzy while travelling") == "medical"
    assert classify_intent("I want to travel because my knee hurts") == "medical"
    assert classify_intent("Can you explain diabetes?") == "medical"
    assert classify_intent("What causes headaches?") == "medical"


def test_ambiguous_asks_for_clarification():
    assert classify_intent("something odd") == "ambiguous"
    result = run_pipeline("something odd")
    assert result.answer == AMBIGUOUS_REPLY
    assert result.possible_conditions == []


def test_chest_discomfort_without_notes_stays_urgent_not_emergency(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: ([], []))
    monkeypatch.setattr(rp, "can_use_llm_kb_fallback", lambda: True)
    monkeypatch.setattr(rp, "generate_kb_miss_bundle", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no groq")))
    result = run_pipeline("I have chest pain")
    assert result.triage is not None
    assert result.triage.level == "consult_doctor"
    assert "112" in (result.answer + " " + (result.triage.guidance or ""))
    assert "heart attack" not in result.answer.lower()


def test_groq_api_failure_does_not_use_mock_matches(monkeypatch):
    from src.llm import kb_miss as kb
    from src.pipeline import rag_pipeline as rp

    def boom(*_a, **_k):
        raise RuntimeError("429 rate limit exceeded")

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: (WEAK, WEAK))
    monkeypatch.setattr(rp, "can_use_llm_kb_fallback", lambda: True)
    monkeypatch.setattr(kb, "medical_llm_status", lambda: "ready")
    monkeypatch.setattr(kb, "_call_llm", boom)
    monkeypatch.setattr(rp, "generate_kb_miss_bundle", kb.generate_kb_miss_bundle)
    result = run_pipeline("itchy nose after dusting")
    assert LOOKUP_FAILED_MESSAGE in result.answer
    assert result.possible_conditions == []
    assert result.evidence_origin == "none"
    assert "Groq" not in result.answer


def test_missing_or_invalid_api_key_does_not_pretend_groq_answered(monkeypatch):
    from src.llm import kb_miss as kb
    from src.pipeline import rag_pipeline as rp

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: (WEAK, WEAK))
    monkeypatch.setattr(rp, "can_use_llm_kb_fallback", lambda: True)
    monkeypatch.setattr(kb, "medical_llm_status", lambda: "missing_key")
    monkeypatch.setattr(rp, "generate_kb_miss_bundle", kb.generate_kb_miss_bundle)
    missing = run_pipeline("itchy nose after dusting")
    assert missing.answer == MISSING_KEY_MESSAGE
    assert missing.possible_conditions == []

    def invalid_key(*_a, **_k):
        raise RuntimeError("401 invalid api key")

    monkeypatch.setattr(kb, "medical_llm_status", lambda: "ready")
    monkeypatch.setattr(kb, "_call_llm", invalid_key)
    invalid = run_pipeline("itchy nose after dusting")
    assert LOOKUP_FAILED_MESSAGE in invalid.answer
    assert invalid.possible_conditions == []
    assert "gsk_" not in invalid.answer


def test_fallback_sources_are_not_fabricated():
    bundle = parse_kb_miss_payload(SAMPLE_JSON, "itchy nose")
    assert bundle is not None
    titles = [row["title"] for row in bundle.citations]
    assert "No matching sources were found in the MediAssist knowledge base" in titles
    assert any("not verified against the knowledge base" in title.lower() for title in titles)
    assert all(not row.get("url") for row in bundle.citations)


def test_frontend_schema_preserved_for_scope_and_medical():
    greeting = result_to_dict(run_pipeline("Hello"))
    assert greeting["possible_conditions"] == []
    assert greeting["citations"] == []
    assert greeting["triage"] is None
    assert "health-related" in greeting["answer"]
