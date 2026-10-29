"""Ambiguous follow-ups, thin condition labels, and mixed-origin citation regressions."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from src.llm.notes_answer import (
    clinical_ideas_from_notes,
    normalize_condition_label,
    synthesize_notes_answer,
)
from src.pipeline.conversation_state import build_conversation_state
from src.pipeline.rag_pipeline import run_pipeline
from src.retrieval.query_normalize import (
    is_ambiguous_symptom_restatement,
    should_reuse_retrieval_history,
)
from src.safety.citation_faithfulness import audit_citation_faithfulness


FEVER_KNEE_HISTORY = [
    {"role": "user", "content": "knee pain with fever and swelling"},
    {
        "role": "assistant",
        "content": "Fever with joint swelling needs clinician review.",
        "possible_conditions": [{"condition": "Irritated bursa"}],
    },
]


def test_normalize_drops_thin_non_condition_labels():
    assert normalize_condition_label("Dry air") is None
    assert normalize_condition_label("Splint") is None
    assert normalize_condition_label("Sore Throat Self-Care") is None
    assert normalize_condition_label("Other treatment") is None
    assert normalize_condition_label("Early osteoarthritis") == "Early osteoarthritis"
    assert normalize_condition_label("viral") == "Viral infection"
    assert normalize_condition_label("strep") == "Strep throat"
    assert normalize_condition_label("flu") == "Flu"
    assert normalize_condition_label("cold") == "Cold"
    assert normalize_condition_label("sciatica") == "Sciatica"
    assert normalize_condition_label("follows a cough") is None
    assert normalize_condition_label("called a cervicogenic") == "Cervicogenic headache"
    assert normalize_condition_label("extra lifting") is None
    assert normalize_condition_label("appendicitis") == "Appendicitis"
    assert normalize_condition_label("less typical in women") is None


def test_normalize_rejects_document_topic_and_warning_headings():
    """Catalog / warning note headings must not become diagnosis cards."""
    assert normalize_condition_label("Study Eye Strain") is None
    assert normalize_condition_label("Sore Throat Possibilities") is None
    assert normalize_condition_label("Belly Button Pain") is None
    assert normalize_condition_label("Chest Pain Red Flag") is None
    assert normalize_condition_label("Common Reasons for a Sore Throat") is None
    assert normalize_condition_label("Chest Pain Warning Signs") is None
    # Warning-category suffix is stripped to the underlying serious condition.
    assert normalize_condition_label("Brain Tumour Warning Signs") == "Brain Tumour"
    # Nearby valid clinical labels stay, including exam-context symptoms.
    assert normalize_condition_label("Exam Headache") == "Exam Headache"
    assert normalize_condition_label("Viral Sore Throat") == "Viral Sore Throat"
    assert normalize_condition_label("Appendicitis") == "Appendicitis"
    assert normalize_condition_label("Heart attack") == "Heart attack"
    assert normalize_condition_label("Costochondritis") == "Costochondritis"
    assert normalize_condition_label("viral_cough") == "Viral cough"


def test_fallback_does_not_readmit_rejected_topic_labels():
    from src.pipeline.rag_pipeline import build_possible_conditions
    from src.retrieval.retriever import Evidence

    evidence = [
        Evidence(
            text="Eye strain after long study sessions often eases with breaks and better lighting.",
            title="Eye Ache After Long Study",
            source="NHS",
            url="https://example.test/eye",
            condition="Study Eye Strain",
            triage_level="self_care",
            relevance_score=0.8,
            doc_id="eye_study",
            vector_score=0.7,
        ),
        Evidence(
            text="Common possibilities include viral infection or strep. Rest and fluids help.",
            title="Common Reasons for a Sore Throat",
            source="NHS",
            url="https://example.test/throat",
            condition="Sore Throat Possibilities",
            triage_level="self_care",
            relevance_score=0.75,
            doc_id="throat_reasons",
            vector_score=0.65,
        ),
        Evidence(
            text="Pain that starts at the navel and then settles in the lower right can be appendicitis.",
            title="Pain Around the Belly Button",
            source="NHS",
            url="https://example.test/belly",
            condition="Belly Button Pain",
            triage_level="consult_doctor",
            relevance_score=0.7,
            doc_id="belly",
            vector_score=0.6,
        ),
        Evidence(
            text="Crushing central chest pain with sweat can be a heart attack. Seek emergency care.",
            title="Chest Pain Warning Signs",
            source="NHS",
            url="https://example.test/chest",
            condition="Chest Pain Red Flag",
            triage_level="emergency",
            relevance_score=0.9,
            doc_id="chest_warn",
            vector_score=0.8,
        ),
    ]
    citations = [
        {
            "title": ev.title,
            "source": ev.source,
            "url": ev.url,
            "condition": ev.condition,
            "relevance_score": ev.relevance_score,
        }
        for ev in evidence
    ]
    rows = build_possible_conditions(citations, evidence=evidence, query="symptoms")
    names = [row["condition"].lower() for row in rows]
    assert "study eye strain" not in names
    assert "sore throat possibilities" not in names
    assert "belly button pain" not in names
    assert "chest pain red flag" not in names
    # Serious clinical content from the warning note body is still allowed.
    assert any("heart attack" in name or "appendicitis" in name or "viral" in name or "strep" in name for name in names)
    assert all((row.get("explanation") or "").strip() for row in rows)
    # Citations / note titles remain available even when a metadata label is dropped.
    assert {ev.title for ev in evidence} >= {row["title"] for row in rows}


def test_clinical_ideas_skip_self_care_and_environment_fragments():
    notes = [
        {
            "title": "Soothing a Sore Throat at Home",
            "source": "NHS",
            "text": (
                "Common possibilities include dry air, viral infection, or strep. "
                "Helpful first steps are rest, fluids, and a splint is not relevant here."
            ),
        }
    ]
    ideas = clinical_ideas_from_notes(notes, limit=6)
    names = [item["condition"].lower() for item in ideas]
    assert "dry air" not in names
    assert "splint" not in names
    assert any("viral" in name or "strep" in name for name in names)
    assert all(item.get("explanation") for item in ideas)


def test_synthesized_answer_keeps_source_on_same_claim_unit():
    blocks = [
        "[1] Source: Knee Pain When Walking (NHS)\n"
        "Common possibilities include early osteoarthritis, a simple strain, or irritation of the kneecap. "
        "Helpful first steps are shorter walks and ice. "
        "See a doctor if the knee swells or locks."
    ]
    answer = synthesize_notes_answer("knee pain", blocks, mode="symptom")
    audit = audit_citation_faithfulness(
        answer,
        [{"title": "Knee Pain When Walking", "source": "NHS", "url": "https://www.nhs.uk/conditions/knee-pain/"}],
    )
    unsupported = [claim for claim in audit.claims if claim.status == "unsupported"]
    assert unsupported == []
    assert audit.fabricated_count == 0


def test_ambiguous_knee_restatement_does_not_reuse_fever_swelling():
    prior = ["knee pain with fever and swelling"]
    assert is_ambiguous_symptom_restatement("knee pain", prior) is True
    assert should_reuse_retrieval_history("knee pain", prior) is False
    state = build_conversation_state("knee pain", FEVER_KNEE_HISTORY)
    assert state.status == "ambiguous_follow_up"
    assert state.reuse_history is False
    assert "fever" not in state.search_query.lower()
    assert "swelling" not in state.search_query.lower()
    assert "fever" in state.context_clarification.lower() or "swelling" in state.context_clarification.lower()


def test_explicit_continuity_reuses_prior_knee_modifiers():
    prior = ["knee pain with fever and swelling"]
    query = "the fever and swelling are still there"
    assert is_ambiguous_symptom_restatement(query, prior) is False
    assert should_reuse_retrieval_history(query, prior) is True
    history = FEVER_KNEE_HISTORY + [{"role": "user", "content": query}]
    # Build from prior user turns only through medical_user_texts inside state.
    state = build_conversation_state(query, FEVER_KNEE_HISTORY)
    assert state.reuse_history is True
    assert state.status == "follow_up"
    assert "fever" in state.search_query.lower() or "swelling" in state.search_query.lower()


def test_pipeline_ambiguous_knee_asks_clarification_and_avoids_bursa_bias():
    result = run_pipeline("knee pain", chat_history=FEVER_KNEE_HISTORY)
    blob = (result.answer or "").lower()
    assert "earlier you also mentioned" in blob or "still present" in blob
    names = " ".join(str(item.get("condition") or "") for item in (result.possible_conditions or [])).lower()
    # Without merging fever/swelling into search, bursa/swelling cards should not dominate.
    assert "irritated bursa" not in names or "osteoarthritis" in names or "strain" in names
    assert not any(
        (item.get("condition") or "").lower() in {"dry air", "splint", "sore throat self-care"}
        for item in (result.possible_conditions or [])
    )
    if result.possible_conditions:
        assert all((item.get("explanation") or "").strip() for item in result.possible_conditions)


def test_finger_after_fever_knee_stays_isolated():
    result = run_pipeline("finger injury", chat_history=FEVER_KNEE_HISTORY)
    names = " ".join(
        str(item.get("condition") or item.get("title") or "")
        for item in (result.possible_conditions or []) + (result.citations or [])
    ).lower()
    assert "knee" not in names
    assert "bursa" not in names
    assert "fever" not in (result.answer or "").lower() or "finger" in (result.answer or "").lower()


def test_sore_throat_cough_does_not_lead_with_unreported_incense():
    result = run_pipeline("sore throat and cough")
    titles = [str(item.get("title") or "") for item in (result.citations or [])]
    assert titles
    assert "incense" not in titles[0].lower()
    assert "smoke at home" not in titles[0].lower()
    blob = (result.answer or "").lower()
    assert "incense" not in blob.split("possible explanations")[0]
    assert "self-care" in blob or "rest" in blob
    assert result.evidence_origin == "knowledge_base"
    assert all((item.get("explanation") or "").strip() for item in (result.possible_conditions or []))


def test_pipeline_knee_answer_usually_stays_knowledge_base_origin():
    result = run_pipeline("knee pain")
    titles = [str(item.get("title") or "") for item in (result.citations or [])]
    general = [
        title
        for title in titles
        if "general medical knowledge" in title.lower() or title.lower().startswith("general ai")
    ]
    # Sibling NHS note titles that share one URL must remain citable so origin stays KB-only.
    assert result.evidence_origin == "knowledge_base"
    assert general == []
    assert len(titles) >= 2
