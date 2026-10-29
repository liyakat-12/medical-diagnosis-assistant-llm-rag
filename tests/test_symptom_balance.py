"""Everyday symptoms stay understandable, and real emergencies still escalate."""
from __future__ import annotations

from src.llm.generator import SYSTEM_PROMPT
from src.retrieval.retriever import Evidence
from src.safety.guardrails import (
    check_emergency,
    check_prescription_request,
    hemoptysis_is_emergency,
    hemoptysis_needs_prompt_care,
)


def _note(title: str, condition: str, level: str, text: str, score: float = 0.84) -> Evidence:
    return Evidence(
        text=text,
        title=title,
        source="Sample note",
        url="",
        condition=condition,
        triage_level=level,
        relevance_score=score,
        doc_id=condition,
        vector_score=0.7,
    )


def _run(monkeypatch, query: str, notes: list[Evidence]):
    from src.pipeline import rag_pipeline as rp

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: (notes, list(notes)))
    monkeypatch.setattr(rp, "can_use_llm_kb_fallback", lambda: True)
    monkeypatch.setattr(
        rp,
        "generate_kb_miss_bundle",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("fallback model")),
    )
    return rp.run_pipeline(query)


def test_prompt_prefers_fitting_explanations_over_rare_diseases():
    assert "everyday explanations" in SYSTEM_PROMPT.lower()
    assert "do not open" in SYSTEM_PROMPT.lower()
    assert "probabilities" in SYSTEM_PROMPT.lower()
    assert "not a diagnosis" in SYSTEM_PROMPT.lower()


def test_isolated_chest_pain_keeps_non_cardiac_notes(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    heart = _note("Heart attack", "heart_attack", "emergency", "Sudden chest pain can be a heart attack.", score=0.90)
    wall = _note("Chest wall pain", "costochondritis", "consult_doctor", "Chest pain from the chest wall is often tender.", score=0.87)
    lung = _note("Pleurisy", "pleurisy", "consult_doctor", "Chest pain that is worse with a cough can be pleurisy.", score=0.80)
    anxiety = _note(
        "Physical Feelings of Mild Anxiety",
        "mild_anxiety_symptoms",
        "self_care",
        "Anxiety can cause a tight chest.",
        score=0.88,
    )
    extra = _note("Hot flush", "hot_flush", "self_care", "A hot flush can make the chest feel warm.", score=0.05)
    extra.vector_score = 0.1
    monkeypatch.setattr(
        rp,
        "retrieve_candidates",
        lambda *_a, **_k: ([heart, anxiety, wall, lung], [extra, heart, anxiety, wall, lung]),
    )
    monkeypatch.setattr(rp, "generate_kb_miss_bundle", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no model")))
    result = rp.run_pipeline("I have chest pain.")
    names = [row["condition"].lower() for row in result.possible_conditions]
    assert "pleurisy" in names
    assert "costochondritis" in names
    assert names.index("pleurisy") < names.index("heart attack")
    assert "hot flush" not in names
    assert "anxiety" not in " ".join(names)
    labels = {row["condition"].lower(): row["evidence_match_label"] for row in result.possible_conditions}
    assert labels["heart attack"] == "Closest evidence match"
    assert labels["costochondritis"] == "Related evidence match"
    assert "percent" not in " ".join(labels.values()).lower()
    assert all("match_percent" not in row for row in result.possible_conditions)
    assert result.triage is not None
    assert result.triage.level != "emergency"
    assert "112" in result.triage.guidance
    assert "you have a heart attack" not in result.answer.lower()
    assert result.citations
    assert result.citations[0]["source"]


def test_sleep_headache_does_not_assume_alcohol(monkeypatch):
    from src.pipeline import rag_pipeline as rp
    from src.retrieval.query_normalize import note_claims_unreported_context

    alcohol = _note(
        "Headache After Drinking Alcohol",
        "hangover_headache",
        "self_care",
        "A headache the morning after alcohol is common.",
        score=0.90,
    )
    tension = _note(
        "Mild Tension Headache",
        "tension_headache",
        "self_care",
        "Poor sleep and stress can trigger a tension headache.",
        score=0.20,
    )
    common = _note(
        "Common Reasons for a Headache",
        "headache_possibilities",
        "self_care",
        "A diary of sleep, screens, and meals helps.",
        score=0.15,
    )
    assert note_claims_unreported_context(
        "I have a mild headache after sleeping poorly.",
        alcohol.title,
        alcohol.condition,
        alcohol.doc_id,
    )
    monkeypatch.setattr(
        rp,
        "retrieve_candidates",
        lambda *_a, **_k: ([alcohol, tension, common], [alcohol, tension, common]),
    )
    result = rp.run_pipeline("I have a mild headache after sleeping poorly.")
    names = [row["condition"].lower() for row in result.possible_conditions]
    assert "hangover" not in " ".join(names)
    assert "alcohol" not in " ".join(names)
    assert "tension headache" in names
    assert names.index("tension headache") == 0


def test_alcohol_headache_keeps_alcohol_note_when_reported(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    alcohol = _note(
        "Headache After Drinking Alcohol",
        "hangover_headache",
        "self_care",
        "A headache the morning after alcohol is common.",
        score=0.40,
    )
    tension = _note(
        "Mild Tension Headache",
        "tension_headache",
        "self_care",
        "Stress can trigger a tension headache.",
        score=0.80,
    )
    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: ([tension, alcohol], [tension, alcohol]))
    result = rp.run_pipeline("I have a headache after drinking alcohol.")
    names = [row["condition"].lower() for row in result.possible_conditions]
    assert names[0] == "hangover headache"
    assert "tension headache" in names


def test_cough_related_chest_ache_keeps_cough_evidence(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    heart = _note("Heart attack", "heart_attack", "emergency", "Chest pressure can be cardiac.")
    cough = _note("Viral cough", "viral_cough", "self_care", "A cough can make the chest ache.")
    wall = _note(
        "Chest wall pain",
        "costochondritis",
        "consult_doctor",
        "Chest discomfort that is worse with coughing can come from the chest wall.",
        score=0.50,
    )
    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: ([heart, cough, wall], [heart, cough, wall]))
    result = rp.run_pipeline("I have a cough and chest discomfort only when coughing.")
    names = [row["condition"].lower() for row in result.possible_conditions]
    assert names[0] == "viral cough"
    assert "costochondritis" in names or "chest wall" in " ".join(names)
    assert "heart attack" in names
    assert result.triage.level != "emergency"
    assert "breathlessness" in result.triage.guidance.lower()


def test_chest_pressure_with_sweating_and_breathing_trouble_is_emergency(monkeypatch):
    query = "My chest pressure is accompanied by sweating and difficulty breathing."
    assert check_emergency(query).triggered
    result = _run(monkeypatch, query, [])
    assert result.triage.level == "emergency"
    assert "112" in (result.answer + " " + (result.triage.guidance or ""))
    assert "call 112" not in (result.answer or "").lower()


def test_mild_headache_does_not_lead_with_a_rare_neurological_note(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    rare = _note("Brain tumour", "brain_tumour", "emergency", "A headache can rarely come from a brain tumour.")
    common = _note("Tension headache", "tension_headache", "self_care", "Poor sleep is a common headache trigger.")
    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: ([rare, common], [rare, common]))
    result = rp.run_pipeline("I have a mild headache after sleeping poorly.")
    names = [row["condition"].lower() for row in result.possible_conditions]
    assert names[0] == "tension headache"
    assert "brain tumour" in names
    assert result.triage.level != "emergency"
    first_explanation = result.answer.lower().split("2.")[0]
    assert "tension" in first_explanation
    assert "tumour" not in first_explanation and "tumor" not in first_explanation


def test_sudden_extremely_severe_headache_is_emergency(monkeypatch):
    query = "I have a sudden, extremely severe headache."
    assert check_emergency(query).triggered
    result = _run(monkeypatch, query, [])
    assert result.triage.level == "emergency"
    assert "112" in (result.answer + " " + (result.triage.guidance or ""))
    assert "call 112" not in (result.answer or "").lower()


def test_mild_headache_with_sudden_extreme_severity_is_emergency(monkeypatch):
    query = "I have a mild headache with sudden onset of extreme severity."
    assert check_emergency(query).triggered
    result = _run(monkeypatch, query, [])
    assert result.triage.level == "emergency"
    assert "112" in (result.answer + " " + (result.triage.guidance or ""))
    assert "call 112" not in (result.answer or "").lower()


def test_short_cough_does_not_become_an_emergency_or_drop_common_notes(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    serious = _note("Tuberculosis", "tuberculosis", "emergency", "A cough can sometimes be tuberculosis.")
    common = _note("Viral cough", "viral_cough", "self_care", "A cough for a couple of days is often viral.")
    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: ([serious, common], [serious, common]))
    result = rp.run_pipeline("I have a cough for two days.")
    names = [row["condition"].lower() for row in result.possible_conditions]
    assert names[0] == "viral cough"
    assert result.triage.level != "emergency"


def test_blood_with_a_cough_is_not_ignored(monkeypatch):
    prompt = [
        "I am coughing up blood.",
        "There is blood when I cough.",
        "My cough has blood in it.",
        "I have a persistent cough with blood.",
    ]
    assert hemoptysis_is_emergency(prompt[0])
    for query in prompt[1:]:
        assert hemoptysis_needs_prompt_care(query), query
        assert not check_emergency(query).triggered, query
    unstable = "I have a persistent cough with blood and I feel breathless."
    assert check_emergency(unstable).triggered
    result = _run(monkeypatch, prompt[3], [])
    assert result.triage.level == "consult_doctor"
    assert "blood" in result.answer.lower()
    assert "prompt" in result.triage.guidance.lower() or "assessment" in result.triage.guidance.lower()
    assert "heart attack" not in result.answer.lower()


def test_nosebleed_wording_is_not_treated_as_coughing_blood():
    assert not hemoptysis_needs_prompt_care("I have a nosebleed.")
    assert not hemoptysis_is_emergency("I have a nosebleed.")
    assert check_emergency("I am vomiting blood.").triggered


def test_exercise_arm_pain_keeps_musculoskeletal_notes_ahead_of_cardiac(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    heart = _note("Heart attack", "heart_attack", "emergency", "Arm pain can occasionally accompany a heart attack.")
    muscle = _note("Muscle strain", "muscle_strain", "self_care", "Arm pain after exercise that worsens with movement is often a muscle strain.")
    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: ([heart, muscle], [heart, muscle]))
    result = rp.run_pipeline("My arm hurts after exercise and worsens with movement.")
    names = [row["condition"].lower() for row in result.possible_conditions]
    assert names[0] == "muscle strain"
    assert "heart attack" in names
    assert result.triage.level != "emergency"


def test_chest_pain_to_the_jaw_with_faintness_is_emergency(monkeypatch):
    query = "I have chest pain spreading to my jaw and feel faint."
    assert check_emergency(query).triggered
    result = _run(monkeypatch, query, [])
    assert result.triage.level == "emergency"
    blob = (result.answer + " " + (result.triage.guidance or "")).lower()
    assert blob.count("medical emergency") == 1
    assert "call 112" not in (result.answer or "").lower()


def test_mild_stomach_discomfort_keeps_a_common_explanation(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    urgent = _note("Appendicitis", "appendicitis", "emergency", "Stomach pain can occasionally be appendicitis.")
    common = _note("Indigestion", "indigestion", "self_care", "Mild stomach discomfort after eating is often indigestion.")
    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: ([urgent, common], [urgent, common]))
    result = rp.run_pipeline("I have mild stomach discomfort after eating.")
    names = [row["condition"].lower() for row in result.possible_conditions]
    assert names[0] == "indigestion"
    assert "appendicitis" in names
    assert result.triage.level != "emergency"
    assert check_emergency("I have severe abdominal pain.").triggered


def test_negation_dosage_and_stroke_rules_still_hold():
    assert not check_emergency("I don't have chest pain.").triggered
    assert check_prescription_request("How many mg of ibuprofen should I take?").triggered
    assert check_emergency("My face is drooping and my speech is slurred.").triggered
    assert check_emergency("I am having a seizure.").triggered


def test_body_map_location_is_added_only_when_missing_from_the_text():
    from app.services.message_service import retrieval_query

    added = retrieval_query("it hurts", ["chest"])
    assert "chest" in added.lower()
    assert retrieval_query("I have chest pain", ["chest"]) == "I have chest pain"


def test_weak_chest_retrieval_does_not_invent_a_diagnosis(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: ([], []))
    monkeypatch.setattr(rp, "can_use_llm_kb_fallback", lambda: True)
    monkeypatch.setattr(rp, "generate_kb_miss_bundle", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no model")))
    result = rp.run_pipeline("I have chest pain.")
    assert result.possible_conditions == []
    assert result.triage.level == "consult_doctor"
    assert "?" in result.answer or "chest pain" in result.answer.lower()
    assert "you have" not in result.answer.lower()
