from __future__ import annotations

from src.safety.guardrails import check_emergency, check_prescription_request, emergency_banner_message


def test_emergency_paraphrases():
    positives = [
        "pressure on my chest and sweating",
        "I can't catch my breath",
        "thunderclap headache started suddenly",
        "I have crushing chest pain spreading to my arm",
        "I have a sudden, extremely severe headache",
        "I am coughing up blood",
    ]
    for query in positives:
        assert check_emergency(query).triggered, query
    not_automatic = [
        "I have chest pain",
        "pain in my chest since this morning",
        "I have a mild chest ache only when coughing",
        "I have a persistent cough with blood",
    ]
    for query in not_automatic:
        assert not check_emergency(query).triggered, query


def test_negated_emergency_does_not_trigger():
    negatives = [
        "I don't have chest pain",
        "I do not have chest pain or shortness of breath",
        "no chest pain, just a mild cough",
    ]
    for query in negatives:
        assert not check_emergency(query).triggered, query


def test_quoted_and_hypothetical_emergency_wording():
    assert not check_emergency('What does "chest pain" mean?').triggered
    assert not check_emergency("What if I had chest pain in a movie scene?").triggered


def test_real_chest_pain_still_triggers_after_other_chat():
    assert check_emergency("I have crushing chest pain spreading to my arm").triggered


def test_prescription_direct_and_indirect():
    assert check_prescription_request("How many mg of ibuprofen should I take for this?").triggered
    assert check_prescription_request("Tell me the dose of paracetamol I should take").triggered
    assert check_prescription_request("How many tablets should I take?").triggered
    assert check_prescription_request("How many 500 mg paracetamol tablets should I take?").triggered
    assert not check_prescription_request("What is paracetamol used for?").triggered
    assert not check_prescription_request("I have a headache and feel nauseous, what could this be?").triggered


def test_meningitis_style_emergency_phrases():
    assert check_emergency(
        "Sudden high fever, a very stiff neck, severe headache, and bright light hurts my eyes"
    ).triggered
    assert check_emergency("Fever and a rash that does not fade when a glass is pressed on it").triggered
    assert not check_emergency("I have a stiff neck after sleeping on a bad pillow").triggered


def test_food_poisoning_and_sports_injury_are_not_emergencies():
    assert not check_emergency("How can I prevent food poisoning at home?").triggered
    assert not check_emergency("I hurt myself playing football and my ankle is sore").triggered


def test_flight_calf_and_breathless_is_emergency():
    assert check_emergency(
        "I have a swollen painful calf after a long flight and now I feel breathless"
    ).triggered


def test_breathless_after_calf_flight_uses_history():
    history = [
        {"role": "user", "content": "I have a swollen painful calf after a long flight"},
        {"role": "assistant", "content": "This may need a clinician review."},
    ]
    assert check_emergency("Now I feel breathless", history).triggered
    assert not check_emergency("Now I feel breathless").triggered


def test_breathless_followup_is_emergency_without_retrieval(monkeypatch):
    from src.pipeline import rag_pipeline as rp
    from src.pipeline.rag_pipeline import run_pipeline

    def boom(*_a, **_k):
        raise AssertionError("emergency must not depend on retrieval")

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("store down")))
    monkeypatch.setattr(rp, "can_use_llm_kb_fallback", lambda: True)
    monkeypatch.setattr(rp, "generate_kb_miss_bundle", boom)
    history = [{"role": "user", "content": "I have a swollen painful calf after a long flight"}]
    result = run_pipeline("Now I feel breathless", chat_history=history)
    assert result.triage is not None
    assert result.triage.level == "emergency"
    assert "112" in (result.answer + " " + (result.triage.guidance or ""))
    assert "call 112" not in (result.answer or "").lower()
    assert "diagnosis" not in result.answer.lower() or "not a diagnosis" in result.answer.lower()


def test_breathless_without_calf_travel_is_not_regex_emergency():
    assert not check_emergency("Now I feel breathless").triggered
    assert not check_emergency(
        "Now I feel breathless",
        [{"role": "user", "content": "I have a dry cough at night"}],
    ).triggered
    assert not check_emergency("I feel breathless after a flight of stairs").triggered
    assert not check_emergency(
        "What should I do?",
        [{"role": "user", "content": "I get burning in my chest after meals"}],
    ).triggered


def test_emergency_banner_uses_configured_number(monkeypatch):
    monkeypatch.setattr("src.config.EMERGENCY_REGION", "IN")
    monkeypatch.setattr("src.config.EMERGENCY_NUMBER", "112")
    text = emergency_banner_message()
    assert "112" in text
    assert "not infallible" in text.lower()
