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
from src.safety.guardrails import check_emergency

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


@dataclass
class TriageResult:
    level: str  # "self_care" | "consult_doctor" | "emergency"
    label: str
    guidance: str
    reason: str
    matched_emergency_terms: list[str] = field(default_factory=list)


def _primary_evidence_level(evidence: list[Evidence]) -> str:
    """Use the top-ranked (most relevant) document's triage level.

    Earlier we used the most severe level among all top-k hits, which was
    overly conservative and often escalated mild queries when one unrelated
    emergency passage appeared in the shortlist. The emergency regex
    guardrail still provides a hard override for true red-flag wording.
    """
    if not evidence:
        return "consult_doctor"  # safe default when nothing was retrieved
    level = evidence[0].triage_level
    return level if level in SEVERITY_ORDER else "consult_doctor"


def classify_triage(query: str, evidence: list[Evidence], history: list[dict] | None = None) -> TriageResult:
    guard = check_emergency(query, history)
    if guard.triggered:
        return TriageResult(
            level="emergency",
            label=TRIAGE_LABELS["emergency"],
            guidance=emergency_guidance(),
            reason="Rule-based safety layer detected emergency red-flag symptoms in your description.",
            matched_emergency_terms=guard.matched_terms,
        )

    level = _primary_evidence_level(evidence)
    return TriageResult(
        level=level,
        label=TRIAGE_LABELS[level],
        guidance=TRIAGE_GUIDANCE[level],
        reason="Based on the most relevant retrieved reference document.",
        matched_emergency_terms=[],
    )
