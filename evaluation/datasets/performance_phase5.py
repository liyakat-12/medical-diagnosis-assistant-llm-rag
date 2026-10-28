"""Phase 5 performance benchmark scenarios.

Fixed query set for cold-start and warm latency measurements.
Reuses wording from Phase 3 / Phase 4 so later quality regressions stay comparable.
This file does not score correctness.

layer: pipeline — in-process run_pipeline / iter_pipeline_stream only.
Does not measure FastAPI, MongoDB, SSE transport, or the browser.
"""
from __future__ import annotations


def _s(sid: str, category: str, query: str, **meta) -> dict:
    return {
        "id": sid,
        "category": category,
        "layer": "pipeline",
        "query": query,
        "history": meta.pop("history", None),
        "notes": meta.pop("notes", ""),
        **meta,
    }


KNEE_HISTORY = [
    {
        "role": "user",
        "content": "Why does my knee hurt when I climb stairs?",
        "possible_conditions": [{"condition": "Knee Pain"}],
        "triage": {"level": "self_care"},
    },
    {
        "role": "assistant",
        "content": "This may be leftover knee strain. Not a diagnosis — see a clinician if needed.",
        "possible_conditions": [{"condition": "Knee Pain"}],
        "triage": {"level": "self_care"},
    },
]


SCENARIOS: list[dict] = [
    _s(
        "pf01",
        "simple_medical",
        "I have a dry cough at night",
        notes="Common symptom expected to retrieve notes.",
    ),
    _s(
        "pf02",
        "multi_source_medical",
        "Why does my knee hurt when I climb stairs?",
        notes="Typically returns several knee-related notes.",
    ),
    _s(
        "pf03",
        "followup",
        "What should I do?",
        history=KNEE_HISTORY,
        notes="Follow-up that should reuse the knee complaint.",
    ),
    _s(
        "pf04",
        "general_chat",
        "Write a Python function for Fibonacci numbers",
        notes="Non-medical; retrieval should be skipped.",
    ),
    _s(
        "pf05",
        "general_chat",
        "Which is better, a car or a bike?",
        notes="Non-medical comparison after no medical history.",
    ),
    _s(
        "pf06",
        "weak_evidence",
        "What is Pompe disease?",
        notes="Named disease not covered by local notes.",
    ),
    _s(
        "pf07",
        "weak_evidence",
        "pain",
        notes="Underspecified medical query.",
    ),
    _s(
        "pf08",
        "emergency",
        "I have severe crushing chest pain spreading to my jaw",
        notes="Regex emergency; still times the existing retrieve-or-banner path.",
    ),
    _s(
        "pf09",
        "safety_refusal",
        "How many 500 mg paracetamol tablets should I take?",
        notes="Prescription refuse; no retrieval and no LLM.",
    ),
    _s(
        "pf10",
        "educational",
        "What is a rare disease in general?",
        notes="Broad educational medical question with weak local match.",
    ),
]


def dump_jsonl(path) -> None:
    import json
    from pathlib import Path

    target = Path(path)
    with target.open("w", encoding="utf-8") as handle:
        for row in SCENARIOS:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")
