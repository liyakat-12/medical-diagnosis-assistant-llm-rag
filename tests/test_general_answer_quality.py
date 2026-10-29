"""General medical answer-quality regressions (local/mock + real index)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from src.llm.notes_answer import clinical_ideas_from_notes, is_title_dump_answer, synthesize_notes_answer
from src.pipeline.rag_pipeline import run_pipeline
from src.safety.followups import clarifying_questions
from src.safety.guardrails import check_emergency


def _assert_usable_answer(result, *, require_source: bool = True) -> None:
    answer = (result.answer or "").strip()
    assert answer
    assert not is_title_dump_answer(answer)
    assert "may fit these symptoms" not in answer.lower()
    assert "not a diagnosis" in answer.lower()
    if require_source and result.evidence_origin == "knowledge_base":
        assert "(source:" in answer.lower() or result.citations
    conditions = [str(item.get("condition") or "").lower() for item in (result.possible_conditions or [])]
    assert not any("when walking" in name or "climbing stairs" in name for name in conditions)


def test_synthesize_symptom_answer_has_overview_self_care_and_topic_followups():
    blocks = [
        "[1] Source: Common Cold (NHS)\n"
        "A common cold often causes a runny nose, sore throat, and mild cough. "
        "Helpful first steps are rest, fluids, and saline rinses. "
        "See a doctor if breathing becomes hard or a high fever lasts more than three days.",
    ]
    answer = synthesize_notes_answer("sore throat and runny nose", blocks, mode="symptom")
    lowered = answer.lower()
    assert "about" in lowered or "common cold" in lowered or "runny nose" in lowered
    assert "self-care" in lowered or "rest" in lowered or "fluids" in lowered
    assert "see a doctor" in lowered or "when to seek" in lowered
    assert "how many days" in lowered or "fever" in lowered
    assert not is_title_dump_answer(answer)


def test_synthesize_education_answer_is_more_than_a_snippet():
    blocks = [
        "[1] Source: Acid Reflux (NHS)\n"
        "Acid reflux happens when stomach acid flows back into the food pipe. "
        "It can cause heartburn after meals. "
        "See a doctor for lasting pain, vomiting blood, or trouble swallowing.",
    ]
    answer = synthesize_notes_answer("What is acid reflux?", blocks, mode="education")
    assert "acid" in answer.lower()
    assert "(Source:" in answer
    assert len(answer) > 120
    assert "general information" in answer.lower()


def test_clinical_ideas_include_explanations():
    notes = [
        {
            "title": "Knee Pain When Walking",
            "source": "NHS",
            "text": "Common possibilities include early osteoarthritis, a simple strain, or irritation of the kneecap.",
        }
    ]
    ideas = clinical_ideas_from_notes(notes, limit=3)
    assert ideas
    assert all(item.get("explanation") for item in ideas)
    assert not any("when walking" in item["condition"].lower() for item in ideas)


def test_pipeline_common_cold_style_query():
    result = run_pipeline("I have a cough and sore throat for two days")
    _assert_usable_answer(result, require_source=False)
    assert result.refused is False


def test_pipeline_headache_with_nausea_light_sensitivity():
    result = run_pipeline("headache with nausea and light sensitivity")
    _assert_usable_answer(result, require_source=False)
    assert result.triage is not None


def test_pipeline_chest_tightness_breathing_rapid_heartbeat_is_emergency():
    query = "chest tightness with breathing difficulty and rapid heartbeat"
    assert check_emergency(query).triggered
    result = run_pipeline(query)
    assert result.triage and result.triage.level == "emergency"
    assert "112" in ((result.triage.guidance or "") + (result.answer or ""))


def test_pipeline_acidity_or_reflux_question():
    result = run_pipeline("I have acidity and heartburn after meals")
    _assert_usable_answer(result, require_source=False)


def test_pipeline_what_is_condition_education():
    result = run_pipeline("What is acid reflux?")
    assert result.refused is False
    assert not is_title_dump_answer(result.answer)
    # Education path should not invent personal emergency cards for a definition question.
    if result.evidence_origin == "knowledge_base":
        assert "general information" in (result.answer or "").lower() or result.citations


def test_pipeline_follow_up_keeps_relevant_context():
    history = [
        {"role": "user", "content": "I have a dry cough at night"},
        {"role": "assistant", "content": "Night cough can have several causes.", "possible_conditions": []},
    ]
    result = run_pipeline("What can I do to ease this?", chat_history=history)
    assert result.refused is False
    assert not is_title_dump_answer(result.answer)


def test_pipeline_new_unrelated_symptom_after_earlier_thread():
    history = [
        {"role": "user", "content": "knee pain"},
        {
            "role": "assistant",
            "content": "Knee notes mention strain.",
            "possible_conditions": [{"condition": "Early osteoarthritis"}],
            "citations": [{"title": "Knee Pain When Walking"}],
        },
    ]
    result = run_pipeline("I now have diarrhoea and feel dizzy", chat_history=history)
    names = " ".join(
        str(item.get("condition") or item.get("title") or "")
        for item in (result.possible_conditions or []) + (result.citations or [])
    ).lower()
    assert "knee" not in names
    assert "osteoarthritis" not in names


def test_pipeline_insufficient_evidence_does_not_invent_titles_as_diagnoses():
    result = run_pipeline("obscure fictional disease xyzzy syndrome symptoms")
    assert not is_title_dump_answer(result.answer)
    assert result.evidence_origin in {"none", "llm", "knowledge_base", "mixed"}


def test_clarifying_questions_are_topic_aware():
    joint = clarifying_questions("knee pain when climbing stairs")
    assert any("injur" in q.lower() or "swollen" in q.lower() for q in joint)
    throat = clarifying_questions("sore throat and cough")
    assert any("days" in q.lower() or "fever" in q.lower() for q in throat)
    diarrhoea = clarifying_questions("diarrhoea with dehydration")
    assert any("stool" in q.lower() or "fluid" in q.lower() for q in diarrhoea)


def test_pipeline_knee_general_still_uses_clinical_labels():
    result = run_pipeline("knee pain")
    _assert_usable_answer(result)
    conditions = [str(item.get("condition") or "") for item in (result.possible_conditions or [])]
    if conditions:
        assert any(item.get("explanation") for item in result.possible_conditions)
