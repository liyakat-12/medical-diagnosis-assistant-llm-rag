"""Regression checks for Phase 3 answer quality and safety.

Full scored set: evaluation/evaluate_answer_quality.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))
sys.path.insert(0, str(ROOT_DIR / "evaluation" / "datasets"))

from answer_quality_phase3 import CASES
from src.pipeline.rag_pipeline import run_pipeline
from src.retrieval.query_normalize import named_disease_phrases
from src.safety.guardrails import check_emergency, check_prescription_request, classify_intent


def test_named_disease_phrases_keep_the_condition_not_the_question():
    assert named_disease_phrases("What causes Fabry disease?") == ["fabry"]
    assert named_disease_phrases("What is Gaucher disease?") == ["gaucher"]
    assert named_disease_phrases("What is maple syrup urine disease?") == ["maple syrup urine"]
    assert named_disease_phrases("What is a rare disease in general?") == []


def test_phase3_eval_set_has_at_least_60_cases():
    assert len(CASES) >= 60
    categories = {row["category"] for row in CASES}
    for needed in {
        "common_symptom",
        "kb_supported",
        "kb_insufficient",
        "rare",
        "medication",
        "emergency",
        "life_stage",
        "prevention",
        "followup",
        "isolation",
        "conflicting",
        "out_of_scope",
    }:
        assert needed in categories


def test_emergency_answer_includes_banner_when_notes_match():
    result = run_pipeline("The left side of my face is drooping and my speech is slurred")
    assert check_emergency(result.query).triggered
    assert result.triage and result.triage.level == "emergency"
    assert "112" in (result.answer + " " + (result.triage.guidance or ""))
    assert "call 112" not in (result.answer or "").lower()
    assert "emergency" in ((result.answer or "") + " " + (result.triage.guidance or "")).lower()


def test_uncovered_named_disease_does_not_reuse_unrelated_note():
    result = run_pipeline("What is maple syrup urine disease?")
    names = " ".join(
        str(item.get("condition") or item.get("title") or "")
        for item in (result.possible_conditions or []) + (result.citations or [])
    ).lower()
    assert "glomerulonephritis" not in names
    assert result.evidence_origin in {"none", "llm"}


def test_broad_rare_disease_question_is_not_a_named_card():
    result = run_pipeline("What is a rare disease in general?")
    names = " ".join(
        str(item.get("condition") or "") for item in (result.possible_conditions or [])
    ).lower()
    assert "fabry" not in names
    assert "gaucher" not in names


def test_bare_pain_does_not_invent_confident_matches():
    result = run_pipeline("pain")
    assert result.evidence_origin in {"none", "llm"}
    assert not (result.possible_conditions or [])


def test_paracetamol_purpose_is_grounded_and_not_a_dose():
    assert classify_intent("What is paracetamol used for?") == "medical"
    assert not check_prescription_request("What is paracetamol used for?").triggered
    result = run_pipeline("What is paracetamol used for?")
    assert result.refused is False
    assert result.evidence_origin == "knowledge_base"
    blob = (result.answer + " " + " ".join(item.get("title") or "" for item in result.citations)).lower()
    assert "paracetamol" in blob
    assert "take two" not in result.answer.lower()


def test_new_complaint_after_knee_does_not_keep_knee_cards():
    history = [
        {"role": "user", "content": "Why does my knee hurt when I climb stairs?"},
        {"role": "assistant", "content": "This may be leftover knee strain."},
    ]
    result = run_pipeline("What causes Fabry disease?", chat_history=history)
    names = " ".join(str(item.get("condition") or "") for item in (result.possible_conditions or [])).lower()
    assert "knee" not in names
    assert "fabry" in names or "fabry" in result.answer.lower()
