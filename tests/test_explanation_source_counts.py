"""Target up to four explanations/sources without inventing fillers or delaying emergency triage."""
from __future__ import annotations

from src.pipeline.rag_pipeline import (
    OUTCOME_LIMIT,
    _select_emergency_explanation_notes,
    _select_explanation_notes,
    build_possible_conditions,
    citations_from_evidence,
)
from src.retrieval.retriever import Evidence
from src.safety.guardrails import check_emergency


def _note(
    title: str,
    condition: str,
    level: str,
    text: str,
    *,
    score: float = 0.84,
    url: str = "",
    doc_id: str | None = None,
) -> Evidence:
    return Evidence(
        text=text,
        title=title,
        source="Sample note",
        url=url or f"https://example.test/{condition}",
        condition=condition,
        triage_level=level,
        relevance_score=score,
        doc_id=doc_id or condition,
        vector_score=score - 0.05,
    )


def test_outcome_limit_is_four():
    assert OUTCOME_LIMIT == 4


def test_emergency_note_selection_allows_up_to_four_serious_notes():
    notes = [
        _note(
            "Chest Pain Warning Signs",
            "chest_pain_warning",
            "emergency",
            "Crushing chest pressure with sweat can be a heart attack. Call emergency care.",
            score=0.95,
        ),
        _note(
            "Heart Attack (Myocardial Infarction)",
            "heart_attack",
            "emergency",
            "Chest pressure spreading to the arm with sweating can be a heart attack.",
            score=0.93,
        ),
        _note(
            "Pulmonary Embolism Warning",
            "pulmonary_embolism",
            "emergency",
            "Sudden breathlessness with chest pain can be a clot in the lung.",
            score=0.90,
        ),
        _note(
            "Unstable Angina Warning Signs",
            "unstable_angina",
            "warning",
            "New or worsening chest pressure at rest needs emergency assessment.",
            score=0.88,
        ),
        _note(
            "Shoulder Pain After Carrying a Bag",
            "shoulder_strain",
            "self_care",
            "A tired shoulder muscle can ache after carrying a heavy bag.",
            score=0.86,
        ),
    ]
    selected = _select_emergency_explanation_notes(
        "I have severe crushing chest pain with sweating and shortness of breath",
        notes,
    )
    assert len(selected) == 4
    titles = {ev.title for ev in selected}
    assert "Shoulder Pain After Carrying a Bag" not in titles
    assert "Chest Pain Warning Signs" in titles
    assert "Heart Attack (Myocardial Infarction)" in titles


def test_emergency_note_selection_does_not_pad_when_only_two_serious_notes():
    notes = [
        _note(
            "Chest Pain Warning Signs",
            "chest_pain_warning",
            "emergency",
            "Crushing chest pressure with sweat can be a heart attack.",
            score=0.95,
        ),
        _note(
            "Heart Attack (Myocardial Infarction)",
            "heart_attack",
            "emergency",
            "Chest pressure with sweating can be a heart attack.",
            score=0.93,
        ),
        _note(
            "Shoulder Pain After Carrying a Bag",
            "shoulder_strain",
            "self_care",
            "A tired shoulder muscle can ache after carrying a heavy bag.",
            score=0.92,
        ),
        _note(
            "Tender Chest Wall When You Press",
            "costochondritis",
            "consult_doctor",
            "Chest wall pain that is sore to press can be costochondritis.",
            score=0.91,
        ),
    ]
    selected = _select_emergency_explanation_notes(
        "I have severe crushing chest pain with sweating",
        notes,
    )
    assert len(selected) == 2
    assert {ev.title for ev in selected} == {
        "Chest Pain Warning Signs",
        "Heart Attack (Myocardial Infarction)",
    }


def test_self_care_and_consult_selection_target_four_when_available():
    notes = [
        _note(
            "Knee Pain When Walking",
            "early_osteoarthritis",
            "self_care",
            "Common possibilities include early osteoarthritis. Pain eases with rest.",
            score=0.91,
        ),
        _note(
            "Kneecap Pain When Squatting",
            "patellofemoral_pain",
            "self_care",
            "A grind at the front of the knee when squatting can be kneecap irritation.",
            score=0.88,
        ),
        _note(
            "Knee Pain When Climbing Stairs",
            "weak_thigh_muscles",
            "self_care",
            "Weak thigh muscles can make stairs painful. Supportive shoes help.",
            score=0.86,
        ),
        _note(
            "Pain on the Inner Side of the Knee",
            "medial_knee_strain",
            "consult_doctor",
            "Inner knee pain after a twist can be a simple strain. See a doctor if it locks.",
            score=0.84,
        ),
        _note(
            "Unrelated Ear Wax",
            "ear_wax",
            "self_care",
            "Ear wax can cause muffled hearing.",
            score=0.10,
        ),
    ]
    selected = _select_explanation_notes("knee pain", "knee pain", notes)
    assert len(selected) == 4
    assert all("ear" not in (ev.title or "").lower() for ev in selected)

    consult_notes = [
        _note(
            "Appendicitis Belly Pain",
            "appendicitis",
            "consult_doctor",
            "Lower right belly pain that starts near the navel can be appendicitis.",
            score=0.92,
        ),
        _note(
            "Constipation Belly Ache",
            "constipation",
            "consult_doctor",
            "Lower belly discomfort with infrequent stools can be constipation.",
            score=0.89,
        ),
        _note(
            "Ovarian Cyst Pain",
            "ovarian_cyst",
            "consult_doctor",
            "One-sided lower belly pain can come from an ovarian cyst.",
            score=0.87,
        ),
        _note(
            "Pelvic Inflammatory Pain",
            "pid",
            "consult_doctor",
            "Lower tummy pain with fever can need prompt clinician review.",
            score=0.85,
        ),
    ]
    consult_selected = _select_explanation_notes(
        "lower right belly pain for two days",
        "lower right belly pain for two days",
        consult_notes,
    )
    assert len(consult_selected) == 4


def test_citations_dedupe_duplicate_titles_and_keep_distinct_sources():
    notes = [
        _note("Knee Pain When Walking", "oa", "self_care", "Walking pain.", score=0.9, url="https://example.test/knee"),
        _note("Knee Pain When Walking", "oa", "self_care", "Same title again.", score=0.8, url="https://example.test/knee"),
        _note("Kneecap Pain When Squatting", "pf", "self_care", "Squat pain.", score=0.85, url="https://example.test/kneecap"),
        _note("Knee Pain When Climbing Stairs", "stairs", "self_care", "Stairs pain.", score=0.82, url="https://example.test/stairs"),
        _note("Pain on the Inner Side of the Knee", "medial", "self_care", "Inner pain.", score=0.80, url="https://example.test/inner"),
    ]
    citations = citations_from_evidence(notes)
    titles = [row["title"] for row in citations]
    assert titles.count("Knee Pain When Walking") == 1
    assert len(citations) == 4
    assert len({row["url"] for row in citations}) == 4


def test_possible_conditions_dedupe_labels_and_skip_incomplete():
    evidence = [
        _note(
            "Knee Pain When Walking",
            "early_osteoarthritis",
            "self_care",
            "Common possibilities include early osteoarthritis and a simple strain. Rest helps.",
            score=0.9,
        ),
        _note(
            "Kneecap Pain When Squatting",
            "patellofemoral_pain",
            "self_care",
            "Kneecap irritation can cause a grind when squatting.",
            score=0.85,
        ),
        _note(
            "Knee Pain When Climbing Stairs",
            "early_osteoarthritis",
            "self_care",
            "Early osteoarthritis can also hurt on stairs.",
            score=0.83,
        ),
        _note(
            "Vague Note",
            "",
            "self_care",
            "x",
            score=0.5,
        ),
    ]
    citations = citations_from_evidence(evidence)
    rows = build_possible_conditions(citations, evidence=evidence, query="knee pain")
    labels = [row["condition"].lower() for row in rows]
    assert len(labels) == len(set(labels))
    assert all((row.get("explanation") or "").strip() for row in rows)
    assert len(rows) <= OUTCOME_LIMIT


def test_emergency_pipeline_keeps_triage_and_can_return_four_sources(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    notes = [
        _note(
            "Chest Pain Warning Signs",
            "chest_pain_warning",
            "emergency",
            "Crushing pressure with sweat and breathlessness needs emergency care. Heart attack is possible.",
            score=0.96,
        ),
        _note(
            "Heart Attack (Myocardial Infarction)",
            "heart_attack",
            "emergency",
            "Chest pressure spreading to the arm with sweating can be a heart attack.",
            score=0.94,
        ),
        _note(
            "Pulmonary Embolism Warning",
            "pulmonary_embolism",
            "emergency",
            "Sudden breathlessness with chest pain can be a clot in the lung.",
            score=0.91,
        ),
        _note(
            "Unstable Angina Warning Signs",
            "unstable_angina",
            "warning",
            "Chest pressure at rest that is new or worsening needs emergency assessment.",
            score=0.89,
        ),
    ]
    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: (notes, list(notes)))
    monkeypatch.setattr(rp, "can_use_llm_kb_fallback", lambda: False)
    monkeypatch.setattr(
        rp,
        "generate_grounded_answer",
        lambda query, blocks, *_a, **_k: (
            "Crushing pressure with sweat can be a heart attack "
            "(Source: Chest Pain Warning Signs). "
            "Sudden breathlessness with chest pain can be a clot in the lung "
            "(Source: Pulmonary Embolism Warning)."
        ),
    )

    query = "I have severe crushing chest pain with sweating and shortness of breath"
    assert check_emergency(query).triggered
    result = rp.run_pipeline(query)

    assert result.triage is not None
    assert result.triage.level == "emergency"
    assert "112" in (result.triage.guidance or "") or "emergency" in (result.triage.guidance or "").lower()
    assert len(result.citations) == 4
    assert len({c["title"] for c in result.citations}) == 4
    assert 1 <= len(result.possible_conditions) <= 4
    assert all((row.get("condition") or "").strip() for row in result.possible_conditions)
    assert all((row.get("explanation") or "").strip() for row in result.possible_conditions)


def test_self_care_pipeline_returns_up_to_four_explanations_and_sources(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    notes = [
        _note(
            "Knee Pain When Walking",
            "early_osteoarthritis",
            "self_care",
            "Common possibilities include early osteoarthritis. Pain is usually in the front or inner knee and eases with rest.",
            score=0.92,
        ),
        _note(
            "Kneecap Pain When Squatting",
            "patellofemoral_pain",
            "self_care",
            "A grind or ache at the front of the knee when squatting can be kneecap irritation.",
            score=0.88,
        ),
        _note(
            "Knee Pain When Climbing Stairs",
            "weak_thigh_muscles",
            "self_care",
            "Weak thigh muscles can make climbing stairs painful. Supportive shoes and gentle exercises help.",
            score=0.86,
        ),
        _note(
            "Pain on the Inner Side of the Knee",
            "medial_knee_strain",
            "self_care",
            "Inner knee pain after a twist can be a simple strain. Ice after activity can help.",
            score=0.84,
        ),
    ]
    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: (notes, list(notes)))
    monkeypatch.setattr(rp, "can_use_llm_kb_fallback", lambda: False)
    monkeypatch.setattr(
        rp,
        "generate_grounded_answer",
        lambda query, blocks, *_a, **_k: (
            "Common possibilities include early osteoarthritis "
            "(Source: Knee Pain When Walking). "
            "A grind when squatting can be kneecap irritation "
            "(Source: Kneecap Pain When Squatting)."
        ),
    )
    result = rp.run_pipeline("knee pain")
    assert result.triage is None or result.triage.level in {"self_care", "consult_doctor"}
    assert len(result.citations) == 4
    assert len(result.possible_conditions) <= 4
    assert len(result.possible_conditions) >= 1
    assert all((row.get("explanation") or "").strip() for row in result.possible_conditions)
