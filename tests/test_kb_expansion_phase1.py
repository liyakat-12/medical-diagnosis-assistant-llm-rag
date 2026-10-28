"""Retrieval and metadata checks for the Phase 1 knowledge-base gap notes.

Rebuild the general index after adding notes:
    python scripts/build_index.py general
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))
sys.path.insert(0, str(ROOT_DIR / "scripts"))

from extra_sample_kb_10 import PHASE1_DOCUMENTS, PHASE1_NEW_IDS
from src.ingestion.loader import load_documents
from src.pipeline.conversation_state import build_conversation_state
from src.retrieval.retriever import retrieve
from src.safety.guardrails import check_emergency

PHASE1_IDS = set(PHASE1_NEW_IDS)

LABELED_QUERIES = [
    ("How can I prevent food poisoning at home?", ("food_safety_at_home",)),
    ("What is the winter vomiting bug?", ("norovirus",)),
    ("Which vaccines should adults have?", ("adult_vaccination_overview",)),
    ("When should I have a smear test?", ("cervical_screening",)),
    ("What is a mammogram and who is invited?", ("breast_screening",)),
    ("How does bowel cancer screening work with a FIT kit?", ("bowel_cancer_screening",)),
    ("What is dementia, and is it a normal part of ageing?", ("dementia",)),
    ("I am pregnant and worried about listeria from soft cheese", ("listeriosis",)),
    ("What is a common cold?", ("common_cold", "common_cold_vs_flu")),
    ("I have a one-sided headache with nausea and light sensitivity", ("migraine", "headache_with_nausea", "migraine_light_sound")),
    ("I am very thirsty and peeing a lot", ("type2_diabetes", "what_is_high_sugar_simple", "diabetes_foot_sore")),
    ("It burns when I urinate", ("burning_when_urinating", "urinary_tract_infection", "what_is_a_uti_simple")),
    ("I have a wheezy cough and a tight chest", ("asthma_mild", "what_is_asthma_simple", "exercise_induced_asthma")),
    ("I get burning in my chest after meals", ("gerd", "heartburn_after_meals", "acidity_burning_chest")),
    ("Pain shoots down my leg when I sit", ("sciatica", "sciatica_when_sitting")),
    ("What is influenza?", ("influenza", "common_cold_vs_flu")),
    ("I have a band-like pressure headache from stress", ("tension_headache", "stress_headache_jaw")),
    ("What is iron deficiency anaemia?", ("anemia", "iron_deficiency_symptoms", "what_is_anaemia_simple")),
    ("Fever, cough, and a sore throat for two days", ("sore_throat_and_fever", "influenza", "common_cold", "viral_sore_throat")),
]

SYNONYM_QUERIES = [
    ("stomach flu vomiting and diarrhoea suddenly", ("norovirus", "mild_gastroenteritis")),
    ("smear test HPV cervix screening", ("cervical_screening", "hpv_infection")),
    ("home stool test for hidden blood FIT", ("bowel_cancer_screening", "colorectal_cancer_warning")),
]


def test_phase1_notes_are_unique_and_well_formed():
    docs = load_documents()
    ids = [doc.id for doc in docs]
    assert len(docs) == 1017
    assert len(set(ids)) == 1017
    assert PHASE1_IDS.issubset(set(ids))
    by_id = {doc.id: doc for doc in docs}
    for doc_id, title, source, url, condition, triage, body in PHASE1_DOCUMENTS:
        doc = by_id[doc_id]
        assert doc.title == title
        assert doc.source == source
        assert doc.url == url
        assert doc.url.startswith("https://")
        assert doc.condition == condition
        assert doc.triage_level == triage
        assert doc.triage_level in {"self_care", "consult_doctor", "emergency"}
        assert len(doc.body.split()) >= 40
        assert "See a" in doc.body or "see a" in doc.body or "Ask a" in doc.body
        assert "https://" not in body


def test_phase1_notes_do_not_duplicate_existing_ids_or_bodies():
    docs = load_documents()
    bodies = {}
    for doc in docs:
        key = " ".join(doc.body.lower().split())
        bodies.setdefault(key, []).append(doc.id)
    duplicates = {key: ids for key, ids in bodies.items() if len(ids) > 1}
    assert duplicates == {}
    old_ids = {doc.id for doc in docs} - PHASE1_IDS
    assert not (PHASE1_IDS & old_ids)


def _recall_and_mrr(queries: list[tuple[str, tuple[str, ...]]], k: int = 4) -> tuple[float, float, list[str]]:
    hits = 0
    reciprocal = 0.0
    misses: list[str] = []
    for query, expected in queries:
        retrieved = [hit.doc_id for hit in retrieve(query, top_k=k, mode="general")]
        rank = None
        for index, doc_id in enumerate(retrieved, start=1):
            if doc_id in expected:
                rank = index
                break
        if rank is None:
            misses.append(f"{query!r} -> {retrieved} (wanted {expected})")
        else:
            hits += 1
            reciprocal += 1.0 / rank
    n = len(queries)
    return hits / n, reciprocal / n, misses


def test_phase1_retrieval_recall_and_mrr():
    labeled = LABELED_QUERIES + SYNONYM_QUERIES
    recall4, mrr, misses = _recall_and_mrr(labeled, k=4)
    assert not misses, "Recall@4 misses:\n" + "\n".join(misses)
    assert recall4 >= 0.9
    assert mrr >= 0.5


def test_phase1_new_topics_retrieve_by_name_and_symptom():
    for query, expected in LABELED_QUERIES[:8]:
        hits = retrieve(query, top_k=4, mode="general")
        retrieved = {hit.doc_id for hit in hits}
        assert retrieved & set(expected), f"{query!r} retrieved {retrieved}, expected {expected}"
        for hit in hits:
            assert hit.source
            assert hit.title
            assert hit.url.startswith("https://") or not hit.url


def test_phase1_notes_remain_after_later_batches():
    ids = {doc.id for doc in load_documents()}
    assert PHASE1_IDS.issubset(ids)


def test_new_complaint_does_not_reuse_unrelated_history():
    history = [
        {"role": "user", "content": "Why does my knee hurt when I climb stairs?"},
        {"role": "assistant", "content": "This may be leftover knee strain."},
    ]
    state = build_conversation_state("What is the winter vomiting bug?", history)
    assert state.status == "new_complaint"
    assert state.reuse_history is False
    assert "knee" not in state.search_query.lower()
    hits = retrieve(state.search_query, top_k=4, mode="general")
    retrieved = {hit.doc_id for hit in hits}
    assert retrieved & {"norovirus", "mild_gastroenteritis"}
    assert "knee_pain_stairs" not in retrieved


def test_emergency_queries_still_trigger_safety_pathway():
    chest = check_emergency("I have severe crushing chest pain spreading to my jaw")
    stroke = check_emergency("The left side of my face is drooping and my speech is slurred")
    breath = check_emergency("I suddenly cannot breathe and my lips feel blue")
    allergy = check_emergency("My tongue is swelling and I have a severe allergic reaction")
    assert chest.triggered
    assert stroke.triggered
    assert breath.triggered
    assert allergy.triggered
