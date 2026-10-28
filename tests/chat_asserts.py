from __future__ import annotations

from src.safety.guardrails import NON_MEDICAL_REPLY


def assert_general_reply(result, *needles: str) -> None:
    assert result.triage is None
    assert result.citations == []
    assert result.possible_conditions == []
    assert result.recommendations == []
    assert result.answer
    assert result.answer != NON_MEDICAL_REPLY
    assert getattr(result, "evidence_origin", "general") == "general"
    assert (result.timings or {}).get("retrieve_ms", 0) == 0
    lowered = result.answer.lower()
    for needle in needles:
        assert needle.lower() in lowered, result.answer
