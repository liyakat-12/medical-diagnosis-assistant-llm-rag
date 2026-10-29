"""Regression coverage for the three 14-case evaluation fixes."""
from __future__ import annotations

from src.pipeline import rag_pipeline as rp
from src.retrieval.query_normalize import note_addresses_hemoptysis, note_claims_unreported_context
from src.retrieval.retriever import Evidence
from src.safety.guardrails import check_emergency, hemoptysis_needs_prompt_care, hemoptysis_present


def _note(
    title: str,
    condition: str,
    level: str,
    text: str,
    *,
    score: float = 0.84,
    doc_id: str | None = None,
) -> Evidence:
    return Evidence(
        text=text,
        title=title,
        source="Sample note",
        url="",
        condition=condition,
        triage_level=level,
        relevance_score=score,
        doc_id=doc_id or condition,
        vector_score=0.7,
    )


def _emergency_blob(result) -> str:
    guidance = (result.triage.guidance if result.triage else "") or ""
    return f"{result.answer or ''}\n{guidance}"


def test_note_addresses_hemoptysis_prefers_blood_and_tb_not_blood_pressure():
    assert note_addresses_hemoptysis(
        "Tuberculosis (TB)",
        "Tuberculosis",
        "tuberculosis",
        "Typical symptoms include coughing up blood or sputum.",
    ) >= 2
    assert note_addresses_hemoptysis(
        "When to See a Doctor for a Cough",
        "Cough When to Seek Help",
        "when_to_see_doctor_cough",
        "Get checked if you cough blood or feel breathless.",
    ) >= 2
    assert (
        note_addresses_hemoptysis(
            "Tickly Cough After Starting a Blood Pressure Tablet",
            "Medicine-Related Cough",
            "dry_cough_ace_note",
            "Some blood-pressure tablets in the ACE-inhibitor group can cause a dry tickly cough.",
        )
        == 0
    )
    assert (
        note_addresses_hemoptysis(
            "Blood on Toilet Paper",
            "Piles",
            "blood_on_toilet_paper",
            "Bright red blood on the paper after a hard stool.",
        )
        == 0
    )
    assert (
        note_addresses_hemoptysis(
            "Dry Cough at Night",
            "Dry Cough",
            "dry_cough_at_night",
            "A dry night cough is often leftover from a cold.\n\n"
            "See a doctor if a cough lasts more than three weeks. Seek emergency care for coughing blood.",
        )
        == 0
    )


def test_exam_headache_note_requires_exam_context():
    assert note_claims_unreported_context(
        "I have a sudden, extremely severe headache.",
        "Headache During Board Exams",
        "Exam Headache",
        "school_exam_headache",
    )
    assert not note_claims_unreported_context(
        "I have a headache during exams.",
        "Headache During Board Exams",
        "Exam Headache",
        "school_exam_headache",
    )


def test_persistent_cough_with_blood_prefers_blood_related_notes(monkeypatch):
    query = "I have a persistent cough with blood."
    assert hemoptysis_needs_prompt_care(query)
    dry = _note(
        "Dry Cough at Night",
        "Dry Cough",
        "self_care",
        "A dry night cough is often leftover from a cold. See a doctor if you cough blood.",
        score=0.92,
    )
    tb = _note(
        "Tuberculosis (TB)",
        "Tuberculosis",
        "consult_doctor",
        "Typical symptoms include a cough lasting three weeks or more, coughing up blood or sputum.",
        score=0.70,
        doc_id="tuberculosis",
    )
    when = _note(
        "When to See a Doctor for a Cough",
        "Cough When to Seek Help",
        "consult_doctor",
        "Get checked if a cough lasts longer than three weeks or you cough blood.",
        score=0.68,
        doc_id="when_to_see_doctor_cough",
    )
    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: ([dry, tb, when], [dry, tb, when]))
    result = rp.run_pipeline(query)
    names = [row["condition"].lower() for row in result.possible_conditions]
    assert result.triage.level == "consult_doctor"
    assert names[0] in {"tuberculosis", "cough when to seek help"}
    assert "dry cough" not in names
    assert "blood" in (result.triage.guidance or "").lower()


def test_blood_when_i_cough_prefers_blood_related_notes(monkeypatch):
    query = "There is blood when I cough."
    dry = _note(
        "Tickly Throat Cough",
        "Tickly Cough",
        "self_care",
        "A tickly cough is usually mild. Seek care if you cough blood.",
        score=0.9,
    )
    tb = _note(
        "Tuberculosis (TB)",
        "Tuberculosis",
        "consult_doctor",
        "Coughing up blood or sputum can occur with tuberculosis.",
        score=0.65,
        doc_id="tuberculosis",
    )
    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: ([dry, tb], [dry, tb]))
    result = rp.run_pipeline(query)
    names = [row["condition"].lower() for row in result.possible_conditions]
    assert hemoptysis_present(query)
    assert result.triage.level == "consult_doctor"
    assert names == ["tuberculosis"]


def test_frank_hemoptysis_with_breathlessness_is_emergency(monkeypatch):
    query = "I am coughing up a large amount of blood and struggling to breathe."
    assert check_emergency(query).triggered
    tb = _note(
        "Tuberculosis (TB)",
        "Tuberculosis",
        "consult_doctor",
        "Seek emergency care for coughing up large amounts of blood.",
        doc_id="tuberculosis",
    )
    dry = _note("Dry Cough at Night", "Dry Cough", "self_care", "A dry cough can linger.")
    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: ([dry, tb], [dry, tb]))
    result = rp.run_pipeline(query)
    assert result.triage.level == "emergency"
    assert "112" in _emergency_blob(result)
    names = [row["condition"].lower() for row in result.possible_conditions]
    assert "tuberculosis" in names
    assert "dry cough" not in names


def test_dry_cough_without_blood_keeps_ordinary_notes(monkeypatch):
    query = "I have a dry cough without blood."
    dry = _note("Dry Cough at Night", "Dry Cough", "self_care", "A dry night cough is often leftover from a cold.")
    tb = _note(
        "Tuberculosis (TB)",
        "Tuberculosis",
        "consult_doctor",
        "Typical symptoms include coughing up blood or sputum.",
        score=0.5,
        doc_id="tuberculosis",
    )
    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: ([dry, tb], [dry, tb]))
    result = rp.run_pipeline(query)
    assert not hemoptysis_present(query)
    assert result.triage.level != "emergency"
    names = [row["condition"].lower() for row in result.possible_conditions]
    assert names[0] == "dry cough"


def test_sudden_severe_headache_emergency_skips_exam_card(monkeypatch):
    query = "I have a sudden, extremely severe headache."
    assert check_emergency(query).triggered
    exam = _note(
        "Headache During Board Exams",
        "Exam Headache",
        "self_care",
        "Long study can cause a tight exam-week headache.",
        score=0.95,
        doc_id="school_exam_headache",
    )
    warning = _note(
        "Brain Tumour Warning Signs",
        "Brain Tumour Warning Signs",
        "warning",
        "A sudden worst-ever headache needs emergency care.",
        score=0.7,
        doc_id="brain_tumour_warning",
    )
    migraine = _note("Migraine", "Migraine", "self_care", "Migraine can cause a severe throbbing headache.", score=0.8)
    monkeypatch.setattr(
        rp,
        "retrieve_candidates",
        lambda *_a, **_k: ([exam, warning, migraine], [exam, warning, migraine]),
    )
    result = rp.run_pipeline(query)
    assert result.triage.level == "emergency"
    names = [row["condition"].lower() for row in result.possible_conditions]
    assert "exam headache" not in names
    assert "migraine" not in names
    # Warning-category tails are stripped; the serious condition name remains.
    assert names == ["brain tumour"]
    assert "112" in (result.triage.guidance or "")
    assert (result.answer or "").lower().count("call 112") == 0


def test_mild_headache_after_poor_sleep_keeps_everyday_notes(monkeypatch):
    query = "I have a mild headache after sleeping poorly."
    tension = _note(
        "Mild Tension Headache",
        "Tension Headache",
        "self_care",
        "Poor sleep commonly triggers a tension-type headache.",
        score=0.88,
    )
    exam = _note(
        "Headache During Board Exams",
        "Exam Headache",
        "self_care",
        "Exam stress can cause a headache.",
        score=0.9,
        doc_id="school_exam_headache",
    )
    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: ([exam, tension], [exam, tension]))
    result = rp.run_pipeline(query)
    assert result.triage.level != "emergency"
    names = [row["condition"].lower() for row in result.possible_conditions]
    assert "exam headache" not in names
    assert names[0] == "tension headache"


def test_headache_during_exams_keeps_exam_note(monkeypatch):
    query = "I have a headache during exams."
    exam = _note(
        "Headache During Board Exams",
        "Exam Headache",
        "self_care",
        "Long study and worry commonly cause a tight exam-week headache.",
        score=0.9,
        doc_id="school_exam_headache",
    )
    tension = _note("Mild Tension Headache", "Tension Headache", "self_care", "A band-like mild headache.", score=0.7)
    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: ([tension, exam], [tension, exam]))
    result = rp.run_pipeline(query)
    assert result.triage.level != "emergency"
    names = [row["condition"].lower() for row in result.possible_conditions]
    assert names[0] == "exam headache"


def test_emergency_answer_does_not_duplicate_112_banner(monkeypatch):
    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: ([], []))
    monkeypatch.setattr(rp, "can_use_llm_kb_fallback", lambda: False)
    cases = [
        "I have chest pressure with sweating and difficulty breathing.",
        "I have chest discomfort and shortness of breath.",
        "I have a sudden, extremely severe headache.",
    ]
    for query in cases:
        assert check_emergency(query).triggered, query
        result = rp.run_pipeline(query)
        assert result.triage.level == "emergency", query
        guidance = result.triage.guidance or ""
        assert "112" in guidance, query
        answer = result.answer or ""
        # Urgency card owns the Call-112 banner; answer must not repeat it.
        assert answer.lower().count("call 112") == 0, query
        assert (answer + "\n" + guidance).lower().count("call 112") == 1, query
