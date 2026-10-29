"""
Triage classification.

Combines two signals into one final triage level:

1. Rule-based emergency detection (src.safety.guardrails) - a hard
   override. If it fires, the result is always "emergency" regardless of
   what retrieval found, because missing a true emergency is far worse
   than a false alarm.
2. The triage_level metadata attached to the most relevant retrieved
   evidence - used when no hard red-flag is present, since the retrieved
   documents encode a clinician-reviewed severity for that condition.

Levels, from least to most severe: self_care < consult_doctor < emergency
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.retrieval.retriever import Evidence
from src.safety.guardrails import (
    check_emergency,
    has_chest_pain_signal,
    hemoptysis_needs_prompt_care,
)

SEVERITY_ORDER = {"self_care": 0, "consult_doctor": 1, "emergency": 2}

TRIAGE_LABELS = {
    "self_care": "Self care",
    "consult_doctor": "Consult a doctor soon",
    "emergency": "Seek emergency care",
}

def emergency_guidance() -> str:
    from src import config

    number = config.EMERGENCY_NUMBER
    if config.EMERGENCY_REGION in {"IN", "INDIA"}:
        return (
            f"This may be a medical emergency. In India, call {number} (national emergency) or go to the "
            "nearest emergency department now. Do not wait for an online tool to confirm this. "
            "Automated detection is not infallible."
        )
    return (
        f"This may be a medical emergency. Call {number} or go to the nearest emergency department now. "
        "Do not wait for an online tool to confirm this. Automated detection is not infallible."
    )


TRIAGE_GUIDANCE = {
    "self_care": "This appears manageable with home/self-care. Monitor your symptoms and seek care if they worsen or don't improve.",
    "consult_doctor": "You should book an appointment with a doctor soon to get this properly evaluated. It is not an emergency, but professional assessment is recommended.",
    "emergency": emergency_guidance(),
}

CHEST_PAIN_SAFETY_QUESTIONS = [
    "Is the chest pain new, severe, persistent, or getting worse?",
    "Do you also have breathlessness, sweating, fainting, nausea, or pain spreading to an arm, jaw, back, or shoulder?",
]

def chest_caution_guidance() -> str:
    from src import config

    number = config.EMERGENCY_NUMBER
    return (
        "Chest discomfort has several possible causes and cannot be diagnosed from a chat message. "
        f"Call {number} or seek emergency care now if it is severe, getting worse, or comes with "
        "breathlessness, sweating, fainting, nausea, or pain spreading to an arm, jaw, back, or shoulder. "
        "Otherwise arrange a medical assessment."
    )


def hemoptysis_guidance() -> str:
    from src import config

    number = config.EMERGENCY_NUMBER
    return (
        "Blood when you cough needs a prompt in-person medical assessment. This chat cannot tell how serious it is. "
        f"Call {number} now if there is a large amount of blood, trouble breathing, chest pain, fainting, or dizziness."
    )


@dataclass
class TriageResult:
    level: str  # "self_care" | "consult_doctor" | "emergency"
    label: str
    guidance: str
    reason: str
    matched_emergency_terms: list[str] = field(default_factory=list)


def _primary_evidence_level(evidence: list[Evidence]) -> str:
    """Use the top-ranked document's triage level, never above consult_doctor.

    Emergency is decided only by the symptom rules in guardrails. A retrieved
    heart-attack note must not turn an everyday symptom into an emergency label.
    """
    if not evidence:
        return "consult_doctor"
    level = evidence[0].triage_level
    if level not in SEVERITY_ORDER:
        return "consult_doctor"
    if level == "emergency":
        return "consult_doctor"
    return level


def classify_triage(query: str, evidence: list[Evidence], history: list[dict] | None = None) -> TriageResult:
    guard = check_emergency(query, history)
    if guard.triggered:
        return TriageResult(
            level="emergency",
            label=TRIAGE_LABELS["emergency"],
            guidance=emergency_guidance(),
            reason="Rule-based safety layer detected emergency warning signs in your description.",
            matched_emergency_terms=guard.matched_terms,
        )

    level = _primary_evidence_level(evidence)
    if hemoptysis_needs_prompt_care(query):
        return TriageResult(
            level="consult_doctor",
            label=TRIAGE_LABELS["consult_doctor"],
            guidance=hemoptysis_guidance(),
            reason="Blood with a cough needs prompt assessment. This is not a diagnosis.",
            matched_emergency_terms=[],
        )
    if has_chest_pain_signal(query):
        if level == "self_care":
            level = "consult_doctor"
        return TriageResult(
            level=level,
            label=TRIAGE_LABELS[level],
            guidance=chest_caution_guidance(),
            reason="Chest discomfort needs assessment. The wording did not meet emergency criteria.",
            matched_emergency_terms=[],
        )
    return TriageResult(
        level=level,
        label=TRIAGE_LABELS[level],
        guidance=TRIAGE_GUIDANCE[level],
        reason="Based on the most relevant retrieved reference document.",
        matched_emergency_terms=[],
    )
