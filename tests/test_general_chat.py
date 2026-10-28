from __future__ import annotations

from chat_asserts import assert_general_reply
from src.pipeline.conversation_state import build_conversation_state
from src.pipeline.rag_pipeline import iter_pipeline_stream, run_pipeline
from src.safety.guardrails import GREETING_REPLY, classify_intent


def test_greeting_stays_canned(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no retrieve")))
    result = run_pipeline("hello")
    assert classify_intent("hello") == "greeting"
    assert result.answer == GREETING_REPLY
    assert result.possible_conditions == []
    assert result.evidence_origin == "none"


def test_general_knowledge_question_skips_retrieval(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no retrieve")))
    result = run_pipeline("Explain how photosynthesis works in simple terms.")
    assert classify_intent("Explain how photosynthesis works in simple terms.") == "non_medical"
    assert_general_reply(result)


def test_coding_print_statement(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no retrieve")))
    result = run_pipeline('print("my name is abd")')
    assert_general_reply(result, "print")


def test_car_versus_bike_comparison():
    result = run_pipeline("Which is better, a car or a bike?")
    assert_general_reply(result, "car", "bike")


def test_travel_question():
    result = run_pipeline("I want to travel from Bengaluru to Delhi.")
    assert_general_reply(result, "travel")


def test_general_follow_up_keeps_plain_history():
    history = [
        {"role": "user", "content": "Which is better, a car or a bike?"},
        {"role": "assistant", "content": "A car is better for long trips; a bike is cheaper in the city."},
    ]
    state = build_conversation_state("What about the second option?", history)
    assert state.intent == "non_medical"
    assert state.reuse_history is False
    assert any("car" in (item.get("content") or "").lower() for item in state.generation_history)
    result = run_pipeline("What about the second option?", chat_history=history)
    assert_general_reply(result)


def test_medical_to_unrelated_topic_has_no_cards():
    history = [
        {
            "role": "user",
            "content": "I have pain in my knee",
            "possible_conditions": [{"condition": "Knee Pain"}],
            "triage": {"level": "self_care"},
        }
    ]
    result = run_pipeline("Which is better, a car or a bike?", chat_history=history)
    assert_general_reply(result, "car")
    assert "knee" not in result.answer.lower()


def test_general_to_new_medical_complaint_does_not_reuse_vehicle_text():
    history = [
        {"role": "user", "content": "Which is better, a car or a bike?"},
        {"role": "assistant", "content": "A car is better for long trips."},
    ]
    state = build_conversation_state("I have a dry cough at night", history)
    assert state.intent == "medical"
    assert state.status == "new_complaint"
    assert "car" not in state.search_query.lower()
    assert "bike" not in state.search_query.lower()


def test_general_stream_has_no_triage_or_citations(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no retrieve")))
    events = list(iter_pipeline_stream("Should I buy a car or a bike?"))
    types = [event.get("type") for event in events]
    assert "triage" not in types
    assert "citation" not in types
    done = [event for event in events if event.get("type") == "done"][-1]
    result = done["result"]
    assert result["possible_conditions"] == []
    assert result["citations"] == []
    assert result["triage"] is None
    assert result["evidence_origin"] == "general"
    assert "car" in result["answer"].lower()


def test_general_provider_failure_is_graceful(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    monkeypatch.setattr(rp, "generate_conversational_answer", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("429")))
    result = run_pipeline("Explain how gravity keeps planets in orbit around the sun.")
    assert result.possible_conditions == []
    assert "try again" in result.answer.lower()
