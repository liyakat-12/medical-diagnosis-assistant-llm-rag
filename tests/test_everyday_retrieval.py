"""
Retrieval checks for everyday symptom questions added in the 1000-note corpus.

These tests need the general Chroma index to include the expanded notes.
Rebuild with: python scripts/build_index.py general
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from src.ingestion.loader import load_documents
from src.retrieval.retriever import retrieve
from src.safety.guardrails import check_emergency

EXPECTED_NEW_IDS = {
    "knee_pain_stairs",
    "shoulder_pain_lifting_arm",
    "lower_back_pain_after_sitting",
    "headache_with_nausea",
    "sore_throat_and_fever",
    "dry_cough_at_night",
    "indigestion_bloating",
    "heel_pain_first_steps",
    "wrist_pain_computer",
    "burning_when_urinating",
    "red_flag_chest_pain",
    "red_flag_stroke",
    "red_flag_allergic",
}

EVERYDAY_QUERIES = [
    (
        "Why does my knee hurt when I climb stairs?",
        ("knee", "stair"),
        ("knee_pain_stairs", "knee_pain_walking", "differential_knee_pain", "knee_pain_downhill"),
    ),
    (
        "My shoulder hurts when I lift my arm.",
        ("shoulder", "arm"),
        ("shoulder_pain_lifting_arm", "pain_lifting_arm_everyday", "differential_shoulder_pain"),
    ),
    (
        "I have lower back pain after sitting.",
        ("back", "sit"),
        ("lower_back_pain_after_sitting", "pain_after_sitting_long", "muscle_pain_after_sitting"),
    ),
    (
        "What can cause a headache with nausea?",
        ("headache", "nausea", "migraine"),
        ("headache_with_nausea", "migraine", "differential_headache"),
    ),
    (
        "I have a fever and sore throat.",
        ("throat", "fever"),
        ("sore_throat_and_fever", "viral_sore_throat", "strep_throat"),
    ),
    (
        "I have a dry cough at night.",
        ("cough", "night"),
        ("dry_cough_at_night", "cough_worse_lying_down", "self_care_dry_cough"),
    ),
    (
        "My stomach feels bloated after eating.",
        ("bloat", "indigest", "stomach"),
        ("indigestion_bloating", "stomach_cramps_after_food", "wind_and_cramps"),
    ),
    (
        "My heel hurts when I take my first steps.",
        ("heel", "plantar"),
        ("heel_pain_first_steps", "plantar_fasciitis", "heel_pain_after_running"),
    ),
    (
        "My wrist hurts after using a computer.",
        ("wrist", "computer", "mouse"),
        ("wrist_pain_computer", "carpal_tunnel"),
    ),
    (
        "It burns when I urinate.",
        ("urinat", "urine", "uti", "burning"),
        ("burning_when_urinating", "urinary_tract_infection", "when_to_see_doctor_urine"),
    ),
    (
        "I have pain in my temples after a tight ponytail.",
        ("temple", "ponytail", "headache"),
        ("tight_ponytail_headache", "temple_pain_tight", "tension_headache"),
    ),
    (
        "What is a fever?",
        ("fever",),
        ("what_is_a_fever", "when_fever_needs_a_doctor", "when_to_see_doctor_fever"),
    ),
    (
        "I have fever and body aches after getting wet in the rain.",
        ("fever", "rain", "monsoon", "ache"),
        ("fever_after_rain_outing", "monsoon_viral_fever", "viral_fever_body_aches"),
    ),
]


def test_expanded_corpus_has_1000_unique_notes():
    docs = load_documents()
    ids = [doc.id for doc in docs]
    assert len(docs) == 1017
    assert len(set(ids)) == 1017
    assert EXPECTED_NEW_IDS.issubset(set(ids))
    assert {"temple_pain_tight", "what_is_a_fever", "monsoon_viral_fever"}.issubset(set(ids))


def test_every_new_note_has_citation_metadata():
    docs = {doc.id: doc for doc in load_documents()}
    for doc_id in EXPECTED_NEW_IDS:
        doc = docs[doc_id]
        assert doc.source
        assert doc.url.startswith("https://")
        assert doc.triage_level in {"self_care", "consult_doctor", "emergency"}
        assert "See a" in doc.body or "Seek" in doc.body or "Call emergency" in doc.body


def _hits_are_relevant(query: str, keywords: tuple[str, ...], expected_ids: tuple[str, ...]) -> None:
    hits = retrieve(query, top_k=4, mode="general")
    assert hits, f"no retrieval hits for: {query}"
    blob = " ".join(
        f"{hit.doc_id} {hit.title} {hit.condition} {hit.text[:200]}"
        for hit in hits
    ).lower()
    assert any(word in blob for word in keywords), f"no keyword {keywords} in hits for {query!r}: {blob[:400]}"
    retrieved_ids = {hit.doc_id for hit in hits}
    assert retrieved_ids & set(expected_ids), (
        f"expected one of {expected_ids} among {retrieved_ids} for {query!r}"
    )
    for hit in hits:
        assert hit.source
        assert hit.title


def test_everyday_queries_retrieve_relevant_sourced_notes():
    for query, keywords, expected_ids in EVERYDAY_QUERIES:
        _hits_are_relevant(query, keywords, expected_ids)


def test_emergency_guardrails_do_not_depend_on_knowledge_base():
    chest = check_emergency("I have severe crushing chest pain spreading to my arm")
    breath = check_emergency("I suddenly cannot breathe and my lips feel blue")
    stroke = check_emergency("The left side of my face is drooping and my speech is slurred")
    allergy = check_emergency("My tongue is swelling and I have a severe allergic reaction")
    assert chest.triggered
    assert breath.triggered
    assert stroke.triggered
    assert allergy.triggered
