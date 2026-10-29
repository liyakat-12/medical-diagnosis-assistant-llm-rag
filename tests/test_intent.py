from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from src.safety.guardrails import classify_intent
from src.pipeline.rag_pipeline import run_pipeline, synthesize_retrieval_query

from chat_asserts import assert_general_reply


def test_classify_intent_skips_greetings_and_objects():
    assert classify_intent("hello") == "greeting"
    assert classify_intent("I am good") == "greeting"
    assert classify_intent("thank you") == "greeting"
    assert classify_intent("this is a table") == "ambiguous"


def test_classify_intent_keeps_educational_health_questions():
    assert classify_intent("It burns when I urinate") == "medical"
    assert classify_intent("I have diarrhoea after a meal out") == "medical"
    assert classify_intent("What is paracetamol used for?") == "medical"
    assert classify_intent("What are the risks of taking too much paracetamol?") == "medical"
    assert classify_intent("Which vaccines should adults have?") == "medical"
    assert classify_intent("When should I have a smear test?") == "medical"
    assert classify_intent("How can I quit smoking?") == "medical"
    assert classify_intent("What is dementia, and is it a normal part of ageing?") == "medical"
    assert classify_intent("My eyelids droop and I get double vision that is worse by evening") == "medical"
    assert classify_intent("I have a stiff neck after sleeping on a bad pillow") == "medical"


def test_classify_intent_keeps_symptoms_and_followups():
    assert classify_intent("I have a cough and mild fever") == "medical"
    history = [
        {"role": "user", "content": "I have a cough", "possible_conditions": [{"condition": "cold"}]},
        {"role": "assistant", "content": "Possible match: common cold", "possible_conditions": [{"condition": "cold"}]},
    ]
    assert classify_intent("I also have a mild fever with that", history) == "medical"
    assert classify_intent("ok", history) == "greeting"
    chest_history = [
        {
            "role": "user",
            "content": "crushing chest pain spreading to my arm",
            "possible_conditions": [{"condition": "Heart Attack"}],
            "triage": {"level": "emergency"},
        }
    ]
    assert classify_intent("miss you", chest_history) == "greeting"
    assert classify_intent("I miss you", chest_history) == "greeting"
    assert classify_intent("it is worse on the left side", chest_history) == "medical"
    assert classify_intent("What could cause this?", history) == "medical"
    assert classify_intent("What should I do?", history) == "medical"
    assert classify_intent("What warning signs should I watch for?", history) == "medical"
    assert classify_intent("When should I seek help?", history) == "medical"
    assert classify_intent("Which is better, a car or a bike?", history) == "non_medical"


def test_synthesize_retrieval_query_anchors_followup():
    history = [{"role": "user", "content": "I have a cough"}]
    combined = synthesize_retrieval_query("I also have a mild fever with that", history)
    assert "cough" in combined.lower()
    assert "fever" in combined.lower()


def test_car_versus_bike_stays_non_medical_after_knee_thread():
    history = [
        {"role": "user", "content": "I have pain in my knee", "possible_conditions": [{"condition": "Knee Pain"}]},
    ]
    assert classify_intent("Which is better, a car or a bike?", history) == "non_medical"
    result = run_pipeline("Which is better, a car or a bike?", chat_history=history)
    assert_general_reply(result, "car", "bike")
    assert "headache" not in result.answer.lower()
    assert "knee" not in result.answer.lower()


def test_similar_comparison_questions_use_the_same_decline():
    history = [
        {"role": "user", "content": "What causes headaches?", "possible_conditions": [{"condition": "Headache"}]},
    ]
    similar = [
        "Which is better, a car or a bike?",
        "What's better, an iPhone or Android?",
        "Which one is faster, a bus or a train?",
        "Car vs bike?",
        "Should I buy a car or a bike?",
        "Which should I choose, a laptop or a tablet?",
    ]
    for query in similar:
        assert classify_intent(query, history) == "non_medical", query
        result = run_pipeline(query, chat_history=history)
        assert_general_reply(result)
        assert "headache" not in result.answer.lower()


def test_car_versus_bike_does_not_inherit_headache_thread():
    from src.retrieval.query_normalize import should_reuse_retrieval_history

    history = [
        {
            "role": "user",
            "content": "What causes headaches?",
            "possible_conditions": [{"condition": "Headache Possibilities"}],
        },
        {
            "role": "assistant",
            "content": "See a doctor for a new pattern of headaches.",
            "possible_conditions": [
                {"condition": "Headache Possibilities"},
                {"condition": "Tension Headache"},
            ],
            "triage": {"level": "self_care"},
        },
    ]
    query = "Which is better, a car or a bike?"
    assert classify_intent(query, history) == "non_medical"
    assert should_reuse_retrieval_history(query, ["What causes headaches?"]) is False
    assert "headache" not in synthesize_retrieval_query(query, history).lower()
    result = run_pipeline(query, chat_history=history)
    assert_general_reply(result, "car")
    assert "headache" not in result.answer.lower()


def test_everyday_followup_reuses_active_complaint():
    from src.pipeline.conversation_state import build_conversation_state

    history = [{"role": "user", "content": "Why does my knee hurt when I climb stairs?"}]
    for query in (
        "What could cause this?",
        "What should I do?",
        "What warning signs should I watch for?",
        "When should I seek help?",
    ):
        state = build_conversation_state(query, history)
        assert state.intent == "medical", query
        assert state.status == "follow_up", query
        assert state.reuse_history is True, query
        assert "knee" in state.search_query.lower(), query


def test_sore_throat_narrowing_stays_on_the_same_thread():
    from src.pipeline.conversation_state import build_conversation_state

    history = [{"role": "user", "content": "I have a fever and a sore throat"}]
    state = build_conversation_state("No fever now, just the sore throat", history)
    assert state.intent == "medical"
    assert state.status == "follow_up"
    assert state.reuse_history is True
    assert "throat" in state.search_query.lower()


def test_ankle_correction_does_not_keep_knee_as_current():
    from src.pipeline.conversation_state import build_conversation_state
    from src.retrieval.query_normalize import should_reuse_retrieval_history

    history = [{"role": "user", "content": "Why does my knee hurt when I climb stairs?"}]
    query = "I meant my ankle, not my knee"
    assert classify_intent(query, history) == "medical"
    assert should_reuse_retrieval_history(query, ["Why does my knee hurt when I climb stairs?"]) is True
    state = build_conversation_state(query, history)
    assert state.intent == "medical"
    assert state.status == "follow_up"
    assert "ankle" in state.search_query.lower()
    assert "knee" not in state.search_query.lower()


def test_calf_after_flight_is_medical_not_travel_chat():
    assert classify_intent("I have a swollen painful calf after a long flight") == "medical"
    result = run_pipeline("I have a swollen painful calf after a long flight")
    assert "compare options such as train" not in (result.answer or "").lower()


def test_code_print_is_non_medical():
    assert classify_intent('print("my name is abd")') == "non_medical"
    result = run_pipeline('print("my name is abd")')
    assert_general_reply(result, "print")
    assert result.possible_conditions == []


def test_chest_pain_after_cough_does_not_search_cough():
    history = [{"role": "user", "content": "I have a dry cough at night"}]
    combined = synthesize_retrieval_query("I have chest pain", history)
    assert "cough" not in combined.lower()
    assert "chest pain" in combined.lower()


def test_chest_pain_does_not_keep_unrelated_cough_cards(monkeypatch):
    from src.pipeline import rag_pipeline as rp
    from src.retrieval.retriever import Evidence

    cough = [
        Evidence(
            text="A humidifier can help in a dry room. Antibiotics do not treat a simple viral cough.",
            title="Dry Cough at Night",
            source="NHS - Cough",
            url="",
            condition="dry_cough",
            triage_level="self_care",
            relevance_score=0.7,
            doc_id="dry_cough_at_night",
            vector_score=0.6,
        )
    ]
    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: (cough, cough))
    monkeypatch.setattr(rp, "can_use_llm_kb_fallback", lambda: True)
    monkeypatch.setattr(rp, "generate_kb_miss_bundle", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no groq")))
    result = run_pipeline("I have chest pain", chat_history=[{"role": "user", "content": "I have a dry cough at night"}])
    assert result.triage is not None
    assert result.triage.level == "consult_doctor"
    assert result.triage.level != "emergency"
    assert "112" in (result.answer + " " + (result.triage.guidance or ""))
    assert "heart attack" not in result.answer.lower()
    assert "you have" not in result.answer.lower()


def test_new_knee_question_does_not_reuse_cough_history():
    history = [
        {"role": "user", "content": "I have a dry cough at night"},
        {"role": "user", "content": "I have chest pain"},
    ]
    query = "i have pain in my leg and it think it is issue in my knee"
    combined = synthesize_retrieval_query(query, history)
    assert "cough" not in combined.lower()
    assert "chest" not in combined.lower()
    assert "knee" in combined.lower()
    assert "leg" in combined.lower()


def test_knee_query_does_not_keep_cough_matches(monkeypatch):
    from src.pipeline import rag_pipeline as rp
    from src.retrieval.retriever import Evidence

    mixed = [
        Evidence(
            text="See a doctor if rib pain lasts or you cough blood. Seek emergency care for chest pain.",
            title="Back or Rib Pain After Coughing",
            source="NHS - Chest pain",
            url="",
            condition="rib_pain",
            triage_level="consult_doctor",
            relevance_score=0.6,
            doc_id="back_pain_after_coughing",
            vector_score=0.55,
        ),
        Evidence(
            text="The knee may ache after walking or a twist. Rest and see a doctor if it swells or locks.",
            title="Knee Pain When Walking",
            source="NHS - Knee pain",
            url="",
            condition="knee_pain",
            triage_level="self_care",
            relevance_score=0.7,
            doc_id="knee_pain_walking",
            vector_score=0.62,
        ),
    ]
    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: (mixed, mixed))
    monkeypatch.setattr(
        rp,
        "generate_grounded_answer",
        lambda *_a, **_k: "Possible leftover knee strain (Source: Knee Pain When Walking). Not a diagnosis — see a clinician if needed.",
    )
    result = run_pipeline(
        "i have pain in my leg and it think it is issue in my knee",
        chat_history=[{"role": "user", "content": "I have a dry cough at night"}],
    )
    titles = " ".join(row.get("title") or "" for row in result.citations).lower()
    conditions = " ".join(row.get("condition") or "" for row in result.possible_conditions).lower()
    recs = " ".join(result.recommendations).lower()
    assert "knee" in titles
    assert "cough" not in titles
    assert "rib" not in titles
    assert "cough" not in conditions
    assert "cough blood" not in recs
    assert "chest pain" not in recs


def test_non_medical_pipeline_skips_retrieval(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    def boom(*_args, **_kwargs):
        raise AssertionError("non-medical queries must not retrieve")

    monkeypatch.setattr(rp, "retrieve_candidates", boom)
    result = run_pipeline("hello")
    assert result.triage is None
    assert result.citations == []
    assert result.possible_conditions == []
    assert result.answer


def test_miss_you_after_chest_pain_does_not_stay_emergency(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    def boom(*_args, **_kwargs):
        raise AssertionError("social messages must not retrieve")

    monkeypatch.setattr(rp, "retrieve_candidates", boom)
    history = [
        {
            "role": "user",
            "content": "crushing chest pain spreading to my arm",
            "possible_conditions": [{"condition": "Heart Attack"}],
            "triage": {"level": "emergency"},
        }
    ]
    result = run_pipeline("miss you", chat_history=history)
    assert result.triage is None
    assert result.citations == []
    assert result.possible_conditions == []
    assert "112" not in (result.answer or "")


def test_weak_evidence_does_not_invent_matches(monkeypatch):
    from src.pipeline import rag_pipeline as rp
    from src.retrieval.retriever import Evidence

    weak = [
        Evidence(
            text="unrelated furniture notes",
            title="Table",
            source="Sample",
            url="",
            condition="table",
            triage_level="self_care",
            relevance_score=0.02,
            doc_id="table",
            vector_score=0.05,
        )
    ]

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_args, **_kwargs: (weak, weak))
    monkeypatch.setattr(rp, "can_use_llm_kb_fallback", lambda: False)
    monkeypatch.setattr(rp, "generate_grounded_answer", lambda *_args, **_kwargs: "Please describe the symptoms more clearly.")
    result = run_pipeline("I have a cough")
    assert result.possible_conditions == []
    assert result.citations == []
    assert result.triage is None
