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

from src.retrieval.query_normalize import (
    is_follow_question,
    is_symptom_correction,
    is_travel_calf_breathless_followup,
)

# ---------------------------------------------------------------------------
# Emergency red-flag patterns
# ---------------------------------------------------------------------------
# Grouped by theme purely for readability/maintainability.
_EMERGENCY_PHRASES: list[str] = [
    # Cardiac
    r"chest pain", r"pain in (my )?chest", r"pressure (in|on) (my )?(the )?chest",
    r"chest tightness", r"sudden (chest|cardiac) (pain|pressure)",
    r"crushing (chest|pain|pressure)", r"tight(ness)? in (my|the) chest",
    r"pain (radiating|spreading) (to|down) (my )?(left |right )?(arm|jaw|neck|back)",
    r"heart attack",
    # Respiratory
    r"can'?t breathe", r"cannot breathe", r"difficulty breathing",
    r"breathing is (severely )?difficult", r"severely difficult (to breathe|breathing)",
    r"can'?t catch (my )?breath", r"struggling to breathe", r"gasping for air", r"turning blue",
    r"short(ness)? of breath",
    r"(calf|clot|long[- ]?flight).{0,80}breathless",
    r"breathless.{0,80}(calf|clot|chest|long[- ]?flight)",
    r"lips? (turning|are|is) blue",
    # Neurological / stroke
    r"face (is )?droop", r"slurred speech", r"can'?t speak properly",
    r"cannot speak (normally|properly)", r"can'?t speak (normally|properly)",
    r"wheez\w*.{0,60}(cannot|can'?t) speak",
    r"sudden (weakness|numbness)", r"one side of (my )?(body|face)",
    r"worst headache of my life", r"sudden severe headache", r"thunderclap headache",
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
    r"(fever|headache).{0,80}stiff neck", r"stiff neck.{0,80}(fever|headache)",
    r"rash that does not fade", r"non-blanching rash",
    r"glass (is )?(pressed|rolled) (on|over)",
    # Poisoning / overdose
    r"overdose", r"(?<!food )(?<!food-)poison(ed|ing)?", r"swallowed.{0,25}(chemicals|pills|tablets|bleach|medication)",
    r"drank.{0,20}(bleach|chemicals|poison)",
    # Mental health crisis
    r"suicid", r"kill myself", r"end(ing)? my (own )?life", r"want to die",
    r"self[- ]harm",
    r"(want to|going to|about to|try to) hurt myself",
    r"hurt myself on purpose",
    r"no (reason|point) (in|to) living",
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
    r"how many (pills?|tablets?) should i take",
    r"how many .{0,40}(pills?|tablets?) should i take",
    r"how many .{0,40}\d+\s*mg",
    r"what (mg|dose|dosage) of",
    r"should i take .{0,30}\d+\s*(mg|ml)",
    r"give me (a )?(dose|dosage|prescription)",
    r"tell me the (dose|dosage)",
]
PRESCRIPTION_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _PRESCRIPTION_PHRASES]

_NEGATION_PREFIX = re.compile(
    r"\b(no|not|never|without|don't|dont|do not|didn't|did not|isn't|is not|wasn't|was not)\b",
    re.I,
)
_HYPOTHETICAL_PREFIX = re.compile(
    r"\b(what if|imagine if|hypothetic|for example|e\.g\.|in a (movie|story|novel|play)|"
    r"asking for a friend|does ['\"]?.{0,30}mean)\b",
    re.I,
)
_DEFINITION_HINT = re.compile(r"\b(what does|what is|meaning of|define)\b", re.I)


@dataclass
class GuardrailResult:
    triggered: bool
    matched_terms: list[str]


def _inside_quotes(text: str, start: int) -> bool:
    before = text[:start]
    return before.count('"') % 2 == 1 or before.count("'") % 2 == 1


def _user_history_texts(history: list[dict] | None) -> list[str]:
    texts: list[str] = []
    for item in history or []:
        if item.get("role") != "user":
            continue
        content = str(item.get("content") or "").strip()
        if content:
            texts.append(content)
    return texts[-8:]


def _scan_emergency_text(raw: str) -> list[str]:
    matches: list[str] = []
    for pattern in EMERGENCY_PATTERNS:
        for match in pattern.finditer(raw):
            window = raw[max(0, match.start() - 48) : match.start()]
            if _NEGATION_PREFIX.search(window):
                continue
            quoted = _inside_quotes(raw, match.start())
            if quoted and (_HYPOTHETICAL_PREFIX.search(raw) or _DEFINITION_HINT.search(raw)):
                continue
            if _HYPOTHETICAL_PREFIX.search(window) and not re.search(
                r"\b(i (have|am having|got)|i'm having)\b", raw, re.I
            ):
                continue
            matches.append(pattern.pattern)
            break
    return matches


def check_emergency(text: str, history: list[dict] | None = None) -> GuardrailResult:
    raw = text or ""
    matches = _scan_emergency_text(raw)
    if matches:
        return GuardrailResult(triggered=True, matched_terms=matches)
    prior = _user_history_texts(history)
    if prior and is_travel_calf_breathless_followup(raw, prior):
        return GuardrailResult(triggered=True, matched_terms=["contextual:calf_travel_breathless"])
    return GuardrailResult(triggered=False, matched_terms=[])


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
_SOCIAL = re.compile(
    r"^\s*((i|we)\s+)?(miss|love)\s+you\b|"
    r"^\s*(miss you|love you|thinking of you|take care|good night|good luck|"
    r"sweet dreams|see you soon|x+|xx+|hugs?)\s*[!.?<3]*\s*$",
    re.I,
)
_SYMPTOM_FOLLOW = re.compile(
    r"\b(left|right|both|side|since|yesterday|today|tonight|weeks?|days?|hours?|"
    r"when i|after|before|morning|walking|stairs|sitting|lifting|"
    r"mild|severe|little|still|worse|"
    r"(getting|feeling|feels) better|it'?s better|it is better|is it better)\b",
    re.I,
)
_MEDICAL = re.compile(
    r"\b(pain|ache|aching|hurt|hurts|sore|fever|cough|cold|flu|vomit\w*|nause\w*|"
    r"dizz\w*|rash|bleed\w*|breath\w*|chest|headache\w*|migraine|stomach|abdomen|throat|"
    r"symptom\w*|illness|ill\b|sick|infect\w*|swell\w*|diabet\w*|asthma|covid|pregnan\w*|"
    r"period|urine|urinat\w*|pee\b|diarrhea|diarrhoea|constipat\w*|anxiety|depress\w*|insomni\w*|allerg\w*|"
    r"wound|burns?|fracture|sprain|doctor|hospital|triage|diagnos\w*|"
    r"medicine|medication|paracetamol|acetaminophen|ibuprofen|aspirin|nsaid|"
    r"itchy|itching|fatigue|tired|lump|swelling|swollen|painful|"
    r"knee|kneecap|ankle|calf|shin|thigh|"
    r"runny nose|congestion|wheeze|cramp|bloating|heartburn|reflux|"
    r"first aid|vaccin\w*|vitamin|nutrition|thyroid|cancer|cholesterol|"
    r"smear|mammogram|screening|dementia|alzheimer|smok\w*|unwell|neck|"
    r"something is wrong|feel unwell|"
    r"droop|double vision|eyelid|"
    r"blood pressure|treatment|prevent|mental health|injur\w*|bruise\w*|"
    r"infection|blood test|x-?ray|scan|therapy|physiotherapy|first-aid|"
    r"diseases?|syndrome|disorder|"
    r"\w+(itis|osis|emia|oma|pathy)|extra detail:|body map context)\b",
    re.I,
)
_NON_MEDICAL = re.compile(
    r"\b(travel from|travel to|distance (from|between|to)|how far (is|from)|"
    r"book(ing)? (a )?flight|flight (to|from|number)|plane ticket|"
    r"hotel|itinerary|weather|forecast|"
    r"python|javascript|typescript|write (me )?(some )?code|programming|"
    r"laptop|iphone|android phone|shopping|netflix|movie|"
    r"stock price|bitcoin|"
    r"should i (buy|get|choose|pick))\b|"
    r"(?:what's|what\s+is|what\s+are|which(?:\s+one)?\s+(?:is|are))\s+"
    r"(?:better|best|worse|faster|cheaper|easier|safer)\b|"
    r"\bvs\.?\b|\bversus\b|"
    r"\b(car|bike|bicycle|motorcycle|scooter|bus|train|plane|iphone|android|"
    r"laptop|phone|tablet)\b.{0,50}\b(or|vs\.?|versus)\b|"
    r"\b(or|vs\.?|versus)\b.{0,50}\b(car|bike|bicycle|motorcycle|scooter|bus|"
    r"train|plane|iphone|android|laptop|phone|tablet)\b|"
    r"print\s*\(|console\.log|def\s+\w+\s*\(|import\s+\w+|from\s+\w+\s+import",
    re.I,
)
_FOLLOWUP = re.compile(
    r"\b(also|as well|with that|tell me more|more about|second (one|condition|match)|"
    r"first (one|condition|match)|third (one|condition)|what about|how about|"
    r"worse|(getting|feeling|feels) better|it'?s better|it is better|is it better|"
    r"still have|and a |plus a |"
    r"what could cause|what should i do|what can i do|warning signs|"
    r"when should i seek|i meant)\b",
    re.I,
)
_BODY_SYMPTOM = re.compile(
    r"\b(my|the)\s+(left |right )?(knee|kneecap|ankle|calf|shin|thigh|hip|foot|heel|"
    r"toe|wrist|elbow|shoulder|arm|hand|finger)s?\b|"
    r"\b(painful|swollen)\b",
    re.I,
)

GREETING_REPLY = (
    "Hello! Welcome to MediAssist. How can I help you with a health-related question today?"
)
THANKS_REPLY = (
    "You're welcome. I'm here if you want to describe symptoms or ask a medical question."
)
BYE_REPLY = "Take care. Come back if you want to look up a health-related question."
SOCIAL_REPLY = (
    "That's kind — I'm just MediAssist, a medical information helper. "
    "If you have a health-related question, describe it in your own words or tap the body map."
)
NON_MEDICAL_REPLY = (
    "I'm designed to help with medical and health-related information. Please ask me a health-related question."
)
AMBIGUOUS_REPLY = (
    "I need a bit more detail. Are you asking about a symptom, a condition, a general question, or something else?"
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


def is_general_intent(intent: str) -> bool:
    return intent in {"non_medical", "general"}


def classify_intent(text: str, history: list[dict] | None = None) -> str:
    """Return 'medical', 'greeting', 'non_medical' (general chat), or 'ambiguous'."""
    raw = (text or "").strip()
    if not raw:
        return "greeting"
    lowered = raw.lower()
    if _BODY_MAP_HINT in lowered or "extra detail:" in lowered:
        return "medical"
    if check_emergency(raw).triggered or check_prescription_request(raw).triggered:
        return "medical"

    plain = _plain_query(raw)
    if (
        _GREETING.match(plain)
        or _WELLBEING.match(plain)
        or _SMALLTALK.match(plain)
        or _SOCIAL.match(plain)
    ):
        return "greeting"
    # Symptom or condition words win even when travel or other context is present.
    if _MEDICAL.search(plain) or _BODY_SYMPTOM.search(plain):
        return "medical"
    # Off-topic comparisons and consumer questions beat follow-up inheritance.
    if _NON_MEDICAL.search(plain):
        return "non_medical"
    if history_has_medical_context(history) and (
        _FOLLOWUP.search(plain)
        or _SYMPTOM_FOLLOW.search(plain)
        or is_follow_question(plain)
        or is_symptom_correction(plain)
    ):
        return "medical"
    if len(plain.split()) <= 4:
        return "ambiguous"
    return "non_medical"


def conversational_reply(text: str, intent: str | None = None) -> str:
    plain = _plain_query(text).lower()
    resolved = intent or classify_intent(text)
    if re.search(r"\b(thank(s| you)?|thx|ty)\b", plain):
        return THANKS_REPLY
    if re.search(r"bye|goodbye|see you", plain):
        return BYE_REPLY
    if _SOCIAL.match(plain) or re.search(r"\b(miss you|love you)\b", plain):
        return SOCIAL_REPLY
    if resolved == "ambiguous":
        return AMBIGUOUS_REPLY
    if is_general_intent(resolved):
        return NON_MEDICAL_REPLY
    return GREETING_REPLY


PRESCRIPTION_REFUSAL_MESSAGE = (
    "I cannot suggest drugs or doses. Please ask a doctor or pharmacist — "
    "dosing depends on your history, weight, allergies, and other medicines."
)

def emergency_banner_message() -> str:
    from src import config

    number = config.EMERGENCY_NUMBER
    if config.EMERGENCY_REGION in {"IN", "INDIA"}:
        return (
            f"This sounds like it could be a medical emergency. In India, call {number} now "
            "or go to the nearest emergency department. Do not wait for an online tool "
            "to confirm this. Automated detection is not infallible."
        )
    return (
        f"This sounds like it could be a medical emergency. Call {number} now "
        "or go to the nearest emergency department. Do not wait for an online tool "
        "to confirm this. Automated detection is not infallible."
    )


EMERGENCY_BANNER_MESSAGE = emergency_banner_message()

# Chest-pain wording that should escalate even when retrieval is empty/weak.
_CHEST_PAIN = re.compile(
    r"\b(chest pain|crushing (chest|pain|pressure)|tight(ness)? in (my|the) chest|"
    r"left[-\s]?sided?\s+chest|pain .{0,24}(arm|jaw|neck|back|shoulder))\b",
    re.IGNORECASE,
)


def has_chest_pain_signal(text: str) -> bool:
    return bool(_CHEST_PAIN.search(text or ""))
