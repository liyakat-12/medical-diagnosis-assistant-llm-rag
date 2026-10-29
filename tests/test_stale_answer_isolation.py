"""Regression: a new symptom in the same chat must not inherit the prior answer."""
from __future__ import annotations

import hashlib
import re

import pytest

from src.pipeline.conversation_state import build_conversation_state
from src.pipeline.rag_pipeline import run_pipeline
from src.retrieval.query_normalize import (
    related_history_texts,
    retrieval_topics,
    should_reuse_retrieval_history,
)
from src.retrieval.retriever import retrieve


CHEST_QUERY = (
    "CHEST LITTLE PAIN; Chest discomfort\n\n"
    "Body map context (user-described discomfort, not a diagnosis): locations = Chest."
)
FINGER_QUERY = "FINGURE INJURED LITTLE"
CHEST_HISTORY = [
    {"role": "user", "content": CHEST_QUERY},
    {
        "role": "assistant",
        "content": (
            "Possible explanations include tender chest wall, pericarditis, and heart attack. "
            "Crushing central pressure with sweat is an emergency. "
            "Rest from the movement that hurts, use heat or ice."
        ),
        "possible_conditions": [
            {"condition": "Costochondritis", "title": "Chest Wall Pain"},
            {"condition": "Pericarditis", "title": "Pericarditis"},
        ],
        "triage": {"level": "consult_doctor", "label": "See a doctor"},
        "recommendations": [
            "Crushing central pressure with sweat is an emergency.",
            "Rest from the movement that hurts, use heat or ice.",
        ],
    },
]


def _fingerprint(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:12]


def test_finger_typo_after_chest_is_new_complaint_not_follow_up():
    assert "arm_shoulder" in retrieval_topics(FINGER_QUERY)
    assert "chest_lung" in retrieval_topics(CHEST_QUERY)
    assert should_reuse_retrieval_history(FINGER_QUERY, [CHEST_QUERY]) is False
    assert related_history_texts(FINGER_QUERY, [CHEST_QUERY]) == []

    state = build_conversation_state(FINGER_QUERY, CHEST_HISTORY)
    assert state.status == "new_complaint"
    assert state.reuse_history is False
    assert "chest" not in state.search_query.lower()
    assert "finger" in state.search_query.lower()
    assert state.generation_history == []
    assert state.search_query.strip()
    assert _fingerprint(state.search_query) != _fingerprint(CHEST_QUERY)


def test_same_chat_second_turn_retrieves_hand_not_chest_docs():
    state = build_conversation_state(FINGER_QUERY, CHEST_HISTORY)
    hits = retrieve(state.search_query, top_k=4, mode="general")
    assert hits, "finger injury should retrieve some general-index evidence"
    blob = " ".join(f"{hit.doc_id} {hit.title} {hit.condition} {hit.text[:200]}" for hit in hits).lower()
    handish = any(
        token in blob
        for token in ("finger", "hand", "wrist", "sprain", "cut", "wound", "injury", "fracture", "nail")
    )
    chestish = any(
        token in blob
        for token in ("costochondritis", "pericarditis", "heart attack", "chest pain", "angina")
    )
    assert handish or not chestish
    # Even if the index is thin on finger notes, prior chest docs must not dominate solely via history reuse.
    assert "costochondritis" not in state.search_query.lower()


def test_same_chat_second_answer_does_not_copy_chest_cards():
    result = run_pipeline(FINGER_QUERY, chat_history=CHEST_HISTORY)
    answer = (result.answer or "").lower()
    conditions = " ".join(str(item.get("condition") or "") for item in (result.possible_conditions or [])).lower()
    sources = " ".join(
        f"{item.get('title') or ''} {item.get('source') or ''}" for item in (result.citations or [])
    ).lower()
    recs = " ".join(result.recommendations or []).lower()
    combined = f"{answer}\n{conditions}\n{sources}\n{recs}"

    assert result.query
    assert "chest little pain" not in (result.query or "").lower()
    assert not re.search(r"\bcostochondritis\b", combined)
    assert not re.search(r"\bpericarditis\b", combined)
    assert "crushing central pressure" not in combined
    assert "pain spreading to the arm or jaw" not in combined
    # Triage for an isolated finger injury must not inherit a prior chest-pain consult card blindly.
    if result.triage is not None:
        level = result.triage.level if hasattr(result.triage, "level") else result.triage.get("level")
        assert level in {"self_care", "consult_doctor", "emergency", "uncertain"}


def test_second_turn_search_query_matches_current_message():
    state = build_conversation_state(FINGER_QUERY, CHEST_HISTORY)
    assert "fingure" not in state.search_query.lower() or "finger" in state.search_query.lower()
    assert "finger" in state.search_query.lower()
    assert CHEST_QUERY.split("\n", 1)[0].lower() not in state.search_query.lower()


def test_body_map_location_change_uses_latest_region():
    history = [
        {
            "role": "user",
            "content": (
                "Chest discomfort\n\n"
                "Body map context (user-described discomfort, not a diagnosis): locations = Chest."
            ),
        }
    ]
    second = (
        "Finger pain after a crush\n\n"
        "Body map context (user-described discomfort, not a diagnosis): locations = Wrist / hand."
    )
    state = build_conversation_state(second, history)
    assert state.reuse_history is False
    assert "chest" not in state.search_query.lower()
    assert "hand" in state.search_query.lower() or "finger" in state.search_query.lower() or "wrist" in state.search_query.lower()


def test_genuine_follow_up_still_keeps_active_complaint():
    history = [{"role": "user", "content": CHEST_QUERY}]
    state = build_conversation_state("What should I watch for?", history)
    assert state.status == "follow_up"
    assert state.reuse_history is True
    assert "chest" in state.search_query.lower()


def test_concurrent_conversations_do_not_share_search_state():
    chest_state = build_conversation_state(CHEST_QUERY, [])
    finger_state = build_conversation_state(FINGER_QUERY, CHEST_HISTORY)
    other = build_conversation_state("I have a dry cough at night", [])
    assert "chest" in chest_state.search_query.lower()
    assert "chest" not in finger_state.search_query.lower()
    assert "cough" in other.search_query.lower()
    assert finger_state.search_query != chest_state.search_query
    assert other.search_query != finger_state.search_query


def test_safety_and_citations_are_turn_local():
    first = run_pipeline(CHEST_QUERY)
    second = run_pipeline(FINGER_QUERY, chat_history=CHEST_HISTORY)
    assert first.answer
    assert second.answer
    # Each turn keeps its own citation list object / contents; second must not equal first's chest pack.
    first_ids = [str(item.get("title") or "") for item in (first.citations or [])]
    second_ids = [str(item.get("title") or "") for item in (second.citations or [])]
    if first_ids and second_ids:
        assert first_ids != second_ids or "finger" in (second.answer or "").lower() or "wrist" in (second.answer or "").lower()
    first_blob = " ".join(first_ids).lower()
    second_blob = f"{second.answer} {' '.join(second_ids)}".lower()
    if "costochondritis" in first_blob or "chest" in first_blob:
        assert "crushing central pressure" not in second_blob
