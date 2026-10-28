"""Question-type and educational search-normalization checks."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from src.pipeline.conversation_state import build_conversation_state
from src.pipeline.question_type import (
    EMERGENCY,
    FOLLOW_UP,
    GENERAL_KNOWLEDGE,
    MEDICAL_EDUCATION,
    MEDICATION_SAFETY,
    POSSIBLE_CAUSES,
    SYMPTOM_INFORMATION,
    TREATMENT_INFORMATION,
    classify_question_type,
    rewrite_educational_search,
)
from src.safety.guardrails import check_emergency, check_prescription_request


def test_educational_paraphrases_share_definition_type():
    queries = [
        "What is asthma?",
        "What asthma is.",
        "Explain asthma in simple words.",
        "Tell me about asthma.",
        "Can you explain asthma to a beginner?",
        "I want to understand asthma.",
    ]
    for query in queries:
        assert classify_question_type(query) == MEDICAL_EDUCATION, query
        state = build_conversation_state(query)
        assert state.personal_context is False, query
        assert "asthma" in state.search_query.lower(), query


def test_educational_search_rewrite_is_canonical():
    assert "What is asthma?" in rewrite_educational_search("what asthma is")
    rewritten = rewrite_educational_search("explain asthma simply")
    assert "What is asthma?" in rewritten
    assert "simple" in rewritten.lower()
    assert rewrite_educational_search("asthma symptoms?") == "What are the symptoms of asthma?"
    assert "treatment and management options for asthma" in rewrite_educational_search(
        "how can asthma be treated?"
    ).lower()


def test_symptom_and_treatment_types_differ_from_definition():
    assert classify_question_type("What are the symptoms of asthma?") == SYMPTOM_INFORMATION
    assert classify_question_type("How is asthma treated?") == TREATMENT_INFORMATION
    assert classify_question_type("What causes asthma?") == POSSIBLE_CAUSES
    assert classify_question_type("I have a dry cough at night") == SYMPTOM_INFORMATION


def test_personal_report_is_not_rewritten_into_education():
    raw = "I have asthma symptoms and a tight chest"
    assert rewrite_educational_search(raw) == raw
    assert classify_question_type(raw) == SYMPTOM_INFORMATION


def test_emergency_and_prescription_stay_independent():
    query = "I have asthma and cannot breathe"
    assert check_emergency(query).triggered
    assert classify_question_type(query) == EMERGENCY
    dose = "How many 500 mg paracetamol tablets should I take?"
    assert check_prescription_request(dose).triggered
    assert classify_question_type(dose) == MEDICATION_SAFETY
    assert classify_question_type("Which is better, a car or a bike?") == GENERAL_KNOWLEDGE


def test_follow_up_keeps_asthma_context():
    history = [
        {"role": "user", "content": "What is asthma?"},
        {"role": "assistant", "content": "Asthma tightens the airways."},
    ]
    state = build_conversation_state("What causes it?", history)
    assert "asthma" in state.search_query.lower()
    assert state.reuse_history is True
    simple = build_conversation_state("Explain that more simply.", history)
    assert simple.reuse_history is True
    assert simple.question_type == FOLLOW_UP
    assert "asthma" in simple.search_query.lower()
