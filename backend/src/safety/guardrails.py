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
    r"chest pain", r"crushing (chest|pain|pressure)", r"tight(ness)? in (my|the) chest",
    r"pain (radiating|spreading) (to|down) (my )?(left |right )?(arm|jaw|neck|back)",
    r"heart attack",
    # Respiratory
    r"can'?t breathe", r"cannot breathe", r"difficulty breathing",
    r"struggling to breathe", r"gasping for air", r"turning blue",
    r"lips? (turning|are|is) blue",
    # Neurological / stroke
    r"face (is )?droop", r"slurred speech", r"can'?t speak properly",
    r"sudden (weakness|numbness)", r"one side of (my )?(body|face)",
    r"worst headache of my life", r"sudden severe headache",
    r"loss of (vision|balance)", r"can'?t see", r"cannot see", r"seizure", r"convulsion",
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


# ---------------------------------------------------------------------------
# Intent / domain classifier (runs before retrieval)
# ---------------------------------------------------------------------------
_BODY_MAP_HINT = "body map context"
_STRIP_BODY_MAP = re.compile(r"body map context \(user-described discomfort, not a diagnosis\):[\s\S]*$", re.I)
_STRIP_EXTRA = re.compile(r"\n\nextra detail:[\s\S]*$", re.I)

_GREETING = re.compile(
    r"^\s*(hi|hello|hey|yo|hola|howdy|good\s+(morning|afternoon|evening)|"
    r"thanks?( you)?|thx|ty|ok(ay)?|k+|cool|great|nice|sure|yep|yes|no|nope|"
    r"bye|goodbye|see you|cheers|please)\s*[!.?]*\s*$",
    re.I,
)
_WELLBEING = re.compile(
    r"^\s*(i am|i'm|im|i feel)\s+(good|fine|ok|okay|well|great|alright|better)\s*[!.?]*\s*$",
    re.I,
)
_SMALLTALK = re.compile(
    r"^\s*(how are you|what('?s| is) up|who are you|what (can|do) you do|"
    r"what is (this|mediassist)|help me|test|testing)\s*[!.?]*\s*$",
    re.I,
)
_MEDICAL = re.compile(
    r"\b(pain|ache|aching|hurt|hurts|sore|fever|cough|cold|flu|vomit|nause|"
    r"dizz|rash|bleed|breath|chest|headache|migraine|stomach|abdomen|throat|"
    r"symptom|illness|ill\b|sick|infect|swell|diabet|asthma|covid|pregnan|"
    r"period|urine|pee\b|diarrhea|constipat|anxiety|depress|insomni|allerg|"
    r"wound|burn|fracture|sprain|doctor|hospital|triage|condition|diagnos|"
    r"medicine|medication|itchy|itching|fatigue|tired|weak|lump|swelling|"
    r"runny nose|congestion|wheeze|cramp|bloating|heartburn|reflux|"
    r"\w+(itis|osis|emia|oma|pathy)|what is|what'?s|tell me about|"
    r"extra detail:|body map context)\b",
    re.I,
)
_FOLLOWUP = re.compile(
    r"\b(also|as well|with that|tell me more|more about|second (one|condition|match)|"
    r"first (one|condition|match)|third (one|condition)|what about|how about|"
    r"worse|better|still have|and a |plus a )\b",
    re.I,
)


def _plain_query(text: str) -> str:
    cleaned = _STRIP_BODY_MAP.sub("", text or "")
    cleaned = _STRIP_EXTRA.sub("", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def history_has_medical_context(history: list[dict] | None) -> bool:
    if not history:
        return False
    for item in history[-10:]:
        if item.get("possible_conditions"):
            return True
        triage = item.get("triage") or {}
        if isinstance(triage, dict) and triage.get("level") and triage.get("level") != "none":
            return True
        content = str(item.get("content") or "")
        if _MEDICAL.search(content) or _BODY_MAP_HINT in content.lower():
            return True
    return False


def classify_intent(text: str, history: list[dict] | None = None) -> str:
    """Return 'medical', 'conversational', or 'off_topic'."""
    raw = (text or "").strip()
    if not raw:
        return "conversational"
    lowered = raw.lower()
    if _BODY_MAP_HINT in lowered or "extra detail:" in lowered:
        return "medical"
    if check_emergency(raw).triggered or check_prescription_request(raw).triggered:
        return "medical"

    plain = _plain_query(raw)
    if _GREETING.match(plain) or _WELLBEING.match(plain) or _SMALLTALK.match(plain):
        return "conversational"
    if _MEDICAL.search(plain):
        return "medical"
    if history_has_medical_context(history) and (_FOLLOWUP.search(plain) or len(plain.split()) <= 12):
        if _GREETING.match(plain) or _WELLBEING.match(plain):
            return "conversational"
        return "medical"
    if len(plain.split()) <= 3 and not _MEDICAL.search(plain):
        return "off_topic" if not _GREETING.match(plain) else "conversational"
    return "off_topic"


def conversational_reply(text: str) -> str:
    plain = _plain_query(text).lower()
    if re.search(r"thank|thx|ty\b", plain):
        return (
            "You're welcome. I'm here if you want to describe symptoms or ask a medical question. "
            "This is not a diagnosis."
        )
    if re.search(r"bye|goodbye|see you", plain):
        return "Take care. Come back if you want to look up symptoms — I'm not a doctor, just an information helper."
    if classify_intent(text) == "off_topic":
        return (
            "I didn't catch a medical question in that. MediAssist looks up symptom information "
            "from curated notes — describe how you feel, or tap the body map, whenever you're ready."
        )
    return (
        "Hello — I'm MediAssist, a medical information helper. "
        "Describe symptoms in your own words, or tap the body map, whenever you want to look something up. "
        "I'm not a doctor and this is not a diagnosis."
    )


PRESCRIPTION_REFUSAL_MESSAGE = (
    "I cannot suggest drugs or doses. Please ask a doctor or pharmacist — "
    "dosing depends on your history, weight, allergies, and other medicines."
)

EMERGENCY_BANNER_MESSAGE = (
    "This sounds like it could be a medical emergency. In India, call 112 now "
    "or go to the nearest emergency department. Do not wait for an online tool "
    "to confirm this."
)

# Chest-pain wording that should escalate even when retrieval is empty/weak.
_CHEST_PAIN = re.compile(
    r"\b(chest pain|crushing (chest|pain|pressure)|tight(ness)? in (my|the) chest|"
    r"left[-\s]?sided?\s+chest|pain .{0,24}(arm|jaw|neck|back|shoulder))\b",
    re.IGNORECASE,
)


def has_chest_pain_signal(text: str) -> bool:
    return bool(_CHEST_PAIN.search(text or ""))
