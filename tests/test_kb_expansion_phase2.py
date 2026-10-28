"""Phase 2 evaluation-set and gap-note checks.

Rebuild the general index after adding notes:
    python scripts/build_index.py general
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))
sys.path.insert(0, str(ROOT_DIR / "scripts"))
sys.path.insert(0, str(ROOT_DIR / "evaluation" / "datasets"))

from extra_sample_kb_11 import PHASE2_DOCUMENTS, PHASE2_NEW_IDS
from extra_sample_kb_12 import PHASE2B_DOCUMENTS, PHASE2B_NEW_IDS
from kb_phase2_queries import QUERIES, retrieval_queries
from src.ingestion.loader import load_documents
from src.pipeline.conversation_state import build_conversation_state
from src.retrieval.query_normalize import normalize_retrieval_query
from src.retrieval.retriever import retrieve
from src.safety.guardrails import check_emergency, check_prescription_request, classify_intent

PHASE2_IDS = set(PHASE2_NEW_IDS) | set(PHASE2B_NEW_IDS)


def test_phase2_eval_set_has_at_least_100_queries():
    assert len(QUERIES) >= 100
    assert len(retrieval_queries()) >= 80
    categories = {row["category"] for row in QUERIES}
    for needed in {
        "symptom",
        "combo",
        "condition",
        "prevention",
        "medication",
        "life_stage",
        "rare",
        "synonym",
        "followup",
        "emergency",
        "out_of_scope",
    }:
        assert needed in categories


def test_phase2_notes_are_unique_and_cited():
    docs = load_documents()
    ids = [doc.id for doc in docs]
    assert len(docs) == 1017
    assert len(set(ids)) == 1017
    assert PHASE2_IDS.issubset(set(ids))
    by_id = {doc.id: doc for doc in docs}
    for doc_id, title, source, url, condition, triage, body in PHASE2_DOCUMENTS + PHASE2B_DOCUMENTS:
        doc = by_id[doc_id]
        assert doc.title == title
        assert doc.source == source
        assert doc.url == url
        assert doc.url.startswith("https://")
        assert doc.condition == condition
        assert doc.triage_level == triage
        assert "See a" in doc.body or "see a" in doc.body
        assert "mg" not in doc.body.lower()
        assert "https://" not in body
    bodies = {}
    for doc in docs:
        bodies.setdefault(" ".join(doc.body.lower().split()), []).append(doc.id)
    assert all(len(ids) == 1 for ids in bodies.values())


def test_tummy_hurts_expands_to_abdominal_pain():
    normalized = normalize_retrieval_query("My tummy hurts in the lower part")
    assert "abdominal pain" in normalized.lower()


def test_common_misspellings_expand_for_retrieval():
    assert "migraine" in normalize_retrieval_query("I get a migrane").lower()
    assert "diarrhoea" in normalize_retrieval_query("I have diarrea").lower()
    assert "asthma" in normalize_retrieval_query("What is ashtma?").lower()
    assert "hypertension" in normalize_retrieval_query("What is hypertention?").lower()


def test_phase2_new_topics_retrieve():
    cases = [
        ("What causes Fabry disease?", "fabry_disease"),
        ("What are the risks of taking too much paracetamol?", "paracetamol_safety"),
        ("Is ibuprofen safe if I have a stomach ulcer?", "ibuprofen_nsaid_safety"),
        ("Can I give a child aspirin for a fever?", "aspirin_and_children"),
        ("Which everyday pain medicines are safer in pregnancy?", "medicines_in_pregnancy"),
        ("How can I quit smoking?", "smoking_cessation"),
        ("My father became suddenly confused over a few hours in hospital. Is that dementia?", "delirium"),
        ("How can I protect my skin from the sun to lower skin cancer risk?", "sun_safety_prevention"),
        ("What is Gaucher disease?", "gaucher_disease"),
    ]
    for query, expected in cases:
        search = build_conversation_state(query).search_query
        hits = retrieve(search, top_k=4, mode="general")
        retrieved = {hit.doc_id for hit in hits}
        assert expected in retrieved, f"{query!r} retrieved {retrieved}"
        for hit in hits:
            assert hit.source
            assert str(hit.url).startswith("https://")


def test_phase2_safety_and_isolation():
    assert check_emergency("I have severe crushing chest pain spreading to my jaw").triggered
    assert check_emergency("The left side of my face is drooping and my speech is slurred").triggered
    assert check_emergency(
        "Sudden high fever, a very stiff neck, severe headache, and bright light hurts my eyes"
    ).triggered
    assert check_emergency("Fever and a rash that does not fade when a glass is pressed on it").triggered
    assert not check_emergency("I have a stiff neck after sleeping on a bad pillow").triggered
    assert check_prescription_request("Write me a prescription for amoxicillin 500mg").triggered
    assert check_prescription_request("How many 500 mg paracetamol tablets should I take?").triggered
    assert not check_prescription_request("What is paracetamol used for?").triggered
    assert classify_intent("Write a Python function for Fibonacci numbers") != "medical"
    history = [
        {"role": "user", "content": "Why does my knee hurt when I climb stairs?"},
        {"role": "assistant", "content": "This may be leftover knee strain."},
    ]
    state = build_conversation_state("What causes Fabry disease?", history)
    assert state.status == "new_complaint"
    assert "knee" not in state.search_query.lower()
    hits = retrieve(state.search_query, top_k=4, mode="general")
    retrieved = {hit.doc_id for hit in hits}
    assert "fabry_disease" in retrieved
    assert "knee_pain_stairs" not in retrieved
