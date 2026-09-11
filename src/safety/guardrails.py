"""
Rule-based safety guardrails.

Two independent checks that run BEFORE the LLM ever sees the query:

1. Emergency red-flag detection - if the raw text matches known
   life-threatening symptom patterns, the system must escalate to
   "emergency" no matter what retrieval or the LLM would otherwise say.
   This is a deliberately simple, auditable keyword/regex layer: for a
   safety-critical feature we prefer a transparent rule list that can be
   reviewed and extended over an opaque model that could silently miss
   cases.

2. Prescription / dosage request detection - if the user is asking
   "what drug/dose should I take", the assistant must refuse and defer to
   a licensed professional or pharmacist instead of generating an answer,
   even if the knowledge base happens to contain dosage information.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Emergency red-flag patterns
# ---------------------------------------------------------------------------
# Grouped by theme purely for readability/maintainability.
_EMERGENCY_PHRASES: list[str] = [
    # Cardiac
    r"chest pain", r"crushing (chest|pain)", r"tight(ness)? in (my|the) chest",
    r"pain (radiating|spreading) (to|down) (my )?(arm|jaw|neck|back)",
    r"heart attack",
    # Respiratory
    r"can'?t breathe", r"cannot breathe", r"difficulty breathing",
    r"struggling to breathe", r"gasping for air", r"turning blue",
    r"lips? (turning|are|is) blue",
    # Neurological / stroke
    r"face (is )?droop", r"slurred speech", r"can'?t speak properly",
    r"sudden (weakness|numbness)", r"one side of (my )?(body|face)",
    r"worst headache of my life", r"sudden severe headache",
    r"loss of (vision|balance)", r"can'?t see", r"seizure", r"convulsion",
    r"unconscious", r"unresponsive", r"passed out", r"fainted",
    r"stroke",
    # Bleeding / trauma
    r"severe bleeding", r"won'?t stop bleeding", r"heavy blood loss",
    r"coughing up blood", r"vomiting blood", r"blood in (my )?vomit",
    r"deep wound", r"compound fracture", r"bone (is )?sticking out",
    # Allergic / anaphylaxis
    r"anaphyla", r"throat.{0,20}closing", r"swelling of (my )?(throat|tongue|face)",
    r"severe allergic reaction", r"epipen",
    # Abdomen
    r"severe abdominal pain", r"rigid (abdomen|stomach|belly)",
    # Sepsis / infection
    r"very high fever", r"fever (of|over) (10[4-9]|1[1-9]\d)",
    r"confusion and fever", r"sepsis",
    # Poisoning / overdose
    r"overdose", r"poison(ed|ing)?", r"swallowed.{0,25}(chemicals|pills|tablets|bleach|medication)",
    r"drank.{0,20}(bleach|chemicals|poison)",
    # Mental health crisis
    r"suicid", r"kill myself", r"end(ing)? my (own )?life", r"want to die",
    r"self[- ]harm", r"hurt myself", r"no (reason|point) (in|to) living",
    r"thinking about (ending|hurting)",
    # Pregnancy emergency
    r"heavy bleeding.*pregnan", r"pregnan.*heavy bleeding",
]
EMERGENCY_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _EMERGENCY_PHRASES]

# ---------------------------------------------------------------------------
# Prescription / dosage request patterns
# ---------------------------------------------------------------------------
_PRESCRIPTION_PHRASES: list[str] = [
    r"how (much|many) (mg|milligram|ml|milliliter|pills?|tablets?|dose)",
    r"what dose", r"what dosage", r"how often should I take",
    r"which (drug|medicine|medication|antibiotic|pill) should I (take|use)",
    r"can you prescribe", r"prescribe me", r"write me a prescription",
    r"is it safe to take \d", r"can I take \d+\s*(mg|ml)",
    r"recommend a (medicine|drug|medication|antibiotic)",
    r"what medication (should|can) I (take|use)",
    r"dosage for",
]
PRESCRIPTION_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _PRESCRIPTION_PHRASES]


@dataclass
class GuardrailResult:
    triggered: bool
    matched_terms: list[str]


def check_emergency(text: str) -> GuardrailResult:
    matches = [p.pattern for p in EMERGENCY_PATTERNS if p.search(text)]
    return GuardrailResult(triggered=bool(matches), matched_terms=matches)


def check_prescription_request(text: str) -> GuardrailResult:
    matches = [p.pattern for p in PRESCRIPTION_PATTERNS if p.search(text)]
    return GuardrailResult(triggered=bool(matches), matched_terms=matches)


PRESCRIPTION_REFUSAL_MESSAGE = (
    "I cannot suggest drugs or doses. Please ask a doctor or pharmacist — "
    "dosing depends on your history, weight, allergies, and other medicines."
)

EMERGENCY_BANNER_MESSAGE = (
    "This sounds like it could be a medical emergency. Call your local emergency "
    "number (e.g. 911/112/999) or go to the nearest emergency department right now. "
    "Do not wait for an online tool to confirm this."
)
