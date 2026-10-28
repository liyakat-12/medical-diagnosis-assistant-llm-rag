"""Deterministic question-type classification for retrieval and answer shape.

This is not a clinical classifier and does not diagnose. Emergency and
prescription checks in guardrails remain independent and run on the raw
user text.
"""
from __future__ import annotations

import re

from src.retrieval.query_normalize import (
    is_follow_question,
    is_symptom_correction,
    is_underspecified_medical_query,
)
from src.safety.guardrails import (
    check_emergency,
    check_prescription_request,
    classify_intent,
    is_general_intent,
)

GENERAL_KNOWLEDGE = "GENERAL_KNOWLEDGE"
MEDICAL_EDUCATION = "MEDICAL_EDUCATION"
SYMPTOM_INFORMATION = "SYMPTOM_INFORMATION"
POSSIBLE_CAUSES = "POSSIBLE_CAUSES"
TREATMENT_INFORMATION = "TREATMENT_INFORMATION"
MEDICATION_SAFETY = "MEDICATION_SAFETY"
EMERGENCY = "EMERGENCY"
FOLLOW_UP = "FOLLOW_UP"
CLARIFICATION = "CLARIFICATION"
OUT_OF_SCOPE = "OUT_OF_SCOPE"

QUESTION_TYPES = (
    GENERAL_KNOWLEDGE,
    MEDICAL_EDUCATION,
    SYMPTOM_INFORMATION,
    POSSIBLE_CAUSES,
    TREATMENT_INFORMATION,
    MEDICATION_SAFETY,
    EMERGENCY,
    FOLLOW_UP,
    CLARIFICATION,
    OUT_OF_SCOPE,
)

_STOP = {
    "a", "an", "the", "please", "just", "me", "my", "about", "to", "in", "for",
    "of", "on", "and", "or", "is", "are", "was", "be", "can", "you", "your",
}

_PERSONAL = re.compile(
    r"\b(i have|i've got|i have got|i am having|i'm having|i feel|i felt|"
    r"i've been|i have been|my \w+ (hurts?|aches?|pain|is sore|feels)|"
    r"it hurts|it burns when|it is worse|it's worse|"
    r"extra detail:|body map context|"
    r"i cannot breathe|i can't breathe|cannot speak|can't speak)\b",
    re.I,
)
_WANT_TO_LEARN = re.compile(
    r"\b(i want to (understand|know|learn)|help me understand|can you explain|"
    r"could you explain|would you explain|tell me about|explain)\b",
    re.I,
)
_DEICTIC = re.compile(
    r"\b(this|that|it|these|those|the (first|second|third) (one|condition|match)|"
    r"more simply|in simple(r)? (words|language|terms)|more detail|"
    r"tell me more|what about that)\b",
    re.I,
)
_MEDICATION = re.compile(
    r"\b(paracetamol|acetaminophen|ibuprofen|aspirin|nsaid|antibiotic|"
    r"amoxicillin|medication|medicine|tablet|dose|dosage|mg\b|interaction|"
    r"contraindicat|side effect|used for|safe if|give a child)\b",
    re.I,
)
_TREATMENT = re.compile(
    r"\b(treat(?:ed|ment|ments)?|manage(?:d|ment)?|therapy|how do doctors|"
    r"what (can|should) (be )?done|how can (.{0,40}) be treated)\b",
    re.I,
)
_SYMPTOM_OF = re.compile(
    r"\b(symptoms?|signs?|how does .{0,40} feel|what (does|can) .{0,40} feel like)\b",
    re.I,
)
_CAUSES = re.compile(
    r"\b(what causes|what could cause|possible causes?|why (does|do|is)|"
    r"what is the cause)\b",
    re.I,
)
_DEFINITION = re.compile(
    r"\b(what is|what's|whats|what are|tell me about|explain|describe|define|"
    r"i want to (understand|know|learn about)|help me understand|"
    r"in simple(r)? (words|language|terms)|to a beginner)\b",
    re.I,
)
_INVERTED_WHAT = re.compile(
    r"^\s*(?:please\s+)?what\s+(?P<topic>(?:(?!\bis\b).)+?)\s+is\s*[?.!]?\s*$",
    re.I,
)
_TELL_ABOUT = re.compile(
    r"^\s*(?:please\s+|can you\s+|could you\s+|would you\s+)?"
    r"(?:tell me about|explain|describe|define|help me understand|"
    r"i want to (?:understand|know|learn(?: about)?))\s+"
    r"(?:an?\s+|the\s+)?(?P<topic>.+?)"
    r"(?:\s+in\s+simple(?:r)?\s+(?:words|language|terms)|\s+to\s+(?:a\s+)?beginner|"
    r"\s+more simply|\s+simply|\s+in\s+simple\s+words)?\s*[?.!]?\s*$",
    re.I,
)
_WHAT_IS = re.compile(
    r"^\s*(?:please\s+|can you\s+|could you\s+)?"
    r"(?:what(?:'s|s)?|what is|what are)\s+(?:an?\s+|the\s+)?(?P<topic>.+?)"
    r"(?:\s+in\s+simple(?:r)?\s+(?:words|language|terms)|\s+to\s+(?:a\s+)?beginner|"
    r"\s+simply)?\s*[?.!]?\s*$",
    re.I,
)
_SYMPTOMS_OF = re.compile(
    r"^\s*(?:(?:what (?:are|is)|explain|tell me(?: about)?|list)\s+)?"
    r"(?:the\s+)?(?:symptoms?|signs?)\s+(?:of|for)\s+(?:an?\s+|the\s+)?(?P<topic>.+?)\s*[?.!]?\s*$"
    r"|^\s*(?:how does|what does)\s+(?P<topic2>.+?)\s+feel(?: like)?\s*[?.!]?\s*$"
    r"|^\s*(?P<topic3>.+?)\s+symptoms?\s*[?.!]?\s*$"
    r"|^\s*what signs (?:can|does)\s+(?P<topic4>.+?)\s+cause\s*[?.!]?\s*$",
    re.I,
)
_TREATMENT_OF = re.compile(
    r"^\s*(?:how (?:is|can|do(?:es)?|should)\s+(?:an?\s+|the\s+)?(?P<topic>.+?)\s+"
    r"(?:be\s+)?(?:treated|managed)|"
    r"what (?:treatments?|management|options?)\s+(?:are|is)\s+(?:available\s+)?"
    r"(?:for|of)\s+(?:an?\s+|the\s+)?(?P<topic2>.+?)|"
    r"how do doctors (?:treat|manage)\s+(?:an?\s+|the\s+)?(?P<topic3>.+?))\s*[?.!]?\s*$",
    re.I,
)
_CAUSES_OF = re.compile(
    r"^\s*what (?:causes|is the cause of)\s+(?:an?\s+|the\s+)?(?P<topic>.+?)\s*[?.!]?\s*$",
    re.I,
)
_SIMPLE_STYLE = re.compile(
    r"\b(simple(?:r)? (words|language|terms)|beginner|simply|eli5|plain (english|language))\b",
    re.I,
)
_PLACEHOLDER = re.compile(r"^\s*(this|that|it|these|those)\s*$", re.I)
_QUESTION_SHAPE = re.compile(
    r"^\s*(what|what's|whats|why|how|when|which|who|where|is |are |can |could |should |"
    r"explain|tell|describe|define|help me)\b|\?\s*$",
    re.I,
)
_SYMPTOM_REPORT = re.compile(
    r"\b(sore throat|runny nose|blocked nose|itchy rash|dry cough|stiff neck|"
    r"no fever( now)?|i (do not|don't|dont) have|just a sore|mild fever|"
    r"wheez\w+|breathless|cannot breathe|can't breathe)\b",
    re.I,
)


def _looks_like_education(text: str) -> bool:
    raw = text or ""
    inverted = _INVERTED_WHAT.match(raw)
    if inverted:
        topic = _clean_topic(inverted.group("topic"))
        return bool(topic) and not _PLACEHOLDER.match(topic)
    symptoms = _SYMPTOMS_OF.match(raw)
    if symptoms:
        topic = _clean_topic(
            symptoms.group("topic")
            or symptoms.groupdict().get("topic2")
            or symptoms.groupdict().get("topic3")
            or symptoms.groupdict().get("topic4")
        )
        return bool(topic) and not _PLACEHOLDER.match(topic)
    treatment = _TREATMENT_OF.match(raw)
    if treatment:
        topic = _clean_topic(
            treatment.group("topic")
            or treatment.groupdict().get("topic2")
            or treatment.groupdict().get("topic3")
        )
        return bool(topic) and not _PLACEHOLDER.match(topic)
    tell = _TELL_ABOUT.match(raw)
    if tell:
        topic = _clean_topic(tell.group("topic"))
        return bool(topic) and not _PLACEHOLDER.match(topic)
    what = _WHAT_IS.match(raw)
    if what:
        topic = _clean_topic(what.group("topic"))
        return bool(topic) and not _PLACEHOLDER.match(topic) and "used for" not in topic.lower()
    causes = _CAUSES_OF.match(raw)
    if causes:
        topic = _clean_topic(causes.group("topic"))
        return bool(topic) and not _PLACEHOLDER.match(topic)
    return False


def is_personal_symptom_query(text: str) -> bool:
    raw = text or ""
    if "extra detail:" in raw.lower() or "body map context" in raw.lower():
        return True
    if _WANT_TO_LEARN.search(raw) and not _PERSONAL.search(raw):
        return False
    if _looks_like_education(raw):
        return False
    if _PERSONAL.search(raw) or _SYMPTOM_REPORT.search(raw):
        return True
    if not _QUESTION_SHAPE.search(raw) and classify_intent(raw) == "medical":
        return True
    return False


def is_educational_reference_query(text: str) -> bool:
    if not (text or "").strip():
        return False
    raw = text or ""
    if "extra detail:" in raw.lower() or "body map context" in raw.lower():
        return False
    if _PERSONAL.search(raw) and not _WANT_TO_LEARN.search(raw):
        return False
    if _looks_like_education(raw):
        return True
    return bool(_DEFINITION.search(raw) and not _PERSONAL.search(raw) and not _DEICTIC.search(raw))


def _clean_topic(topic: str | None) -> str:
    value = re.sub(r"\s+", " ", (topic or "").strip(" .?!,"))
    value = re.sub(
        r"\s+(in simple(?:r)? (?:words|language|terms)|to a beginner|simply|please)$",
        "",
        value,
        flags=re.I,
    )
    words = [part for part in value.split() if part.lower() not in _STOP or part.lower() in {"type", "2"}]
    cleaned = " ".join(words) if words else value
    return cleaned.strip(" .?!")


def rewrite_educational_search(text: str, original: str | None = None) -> str:
    """Canonical search phrasing for educational paraphrases. Original message is unchanged."""
    source = original if original is not None else text
    if is_personal_symptom_query(source):
        return text
    raw = re.sub(r"\s+", " ", (text or "").strip())
    if not raw:
        return raw
    simple = bool(_SIMPLE_STYLE.search(source) or _SIMPLE_STYLE.search(raw))
    suffix = " Explain in simple language." if simple else ""

    symptoms = _SYMPTOMS_OF.match(raw)
    if symptoms:
        topic = _clean_topic(
            symptoms.group("topic")
            or symptoms.groupdict().get("topic2")
            or symptoms.groupdict().get("topic3")
            or symptoms.groupdict().get("topic4")
        )
        if topic and not _PLACEHOLDER.match(topic):
            return f"What are the symptoms of {topic}?"

    treatment = _TREATMENT_OF.match(raw)
    if treatment:
        topic = _clean_topic(
            treatment.group("topic")
            or treatment.groupdict().get("topic2")
            or treatment.groupdict().get("topic3")
        )
        if topic and not _PLACEHOLDER.match(topic):
            return f"What are the general treatment and management options for {topic}?"

    causes = _CAUSES_OF.match(raw)
    if causes:
        topic = _clean_topic(causes.group("topic"))
        if topic and not _PLACEHOLDER.match(topic):
            return f"What causes {topic}?"

    inverted = _INVERTED_WHAT.match(raw)
    if inverted:
        topic = _clean_topic(inverted.group("topic"))
        if topic and not _PLACEHOLDER.match(topic):
            return f"What is {topic}?{suffix}".strip()

    tell = _TELL_ABOUT.match(raw)
    if tell:
        topic = _clean_topic(tell.group("topic"))
        if topic and not _PLACEHOLDER.match(topic):
            return f"What is {topic}?{suffix}".strip()

    what = _WHAT_IS.match(raw)
    if what:
        topic = _clean_topic(what.group("topic"))
        if topic and not _PLACEHOLDER.match(topic) and "used for" not in topic.lower():
            lowered_topic = topic.lower()
            if lowered_topic.startswith("symptoms of "):
                return f"What are the symptoms of {topic[12:].strip()}?"
            return f"What is {topic}?{suffix}".strip()

    return raw


def _named_topic_question(text: str) -> bool:
    """True when the question names a condition rather than pointing at 'this/it'."""
    if _DEICTIC.search(text or "") and not _DEFINITION.search(text or ""):
        if re.search(r"\b(this|that|it)\b", text or "", re.I) and not _INVERTED_WHAT.match(text or ""):
            if not re.search(r"\b(asthma|diabetes|migraine|cold|flu|dementia)\b", text or "", re.I):
                return False
    return is_educational_reference_query(text)


def classify_question_type(
    query: str,
    *,
    intent: str | None = None,
    status: str | None = None,
    history: list[dict] | None = None,
) -> str:
    text = query or ""
    if intent is None:
        intent = classify_intent(query, history)
    if check_prescription_request(text).triggered or status == "prescription":
        return MEDICATION_SAFETY
    if check_emergency(text, history).triggered or status == "emergency":
        return EMERGENCY
    if is_general_intent(intent) or status in {"greeting", "non_medical"}:
        return GENERAL_KNOWLEDGE
    if intent == "ambiguous" and status not in {"follow_up", "new_complaint"}:
        return CLARIFICATION

    personal = is_personal_symptom_query(text)
    if _MEDICATION.search(text) and not personal and (
        re.search(r"\b(used for|safe|risks?|side effect|interaction|give a child|ulcer|pregnan)\b", text, re.I)
        or re.search(r"\b(paracetamol|ibuprofen|aspirin)\b", text, re.I)
    ):
        return MEDICATION_SAFETY
    if personal and _MEDICATION.search(text) and re.search(r"\b(safe|ulcer|pregnan|child|give)\b", text, re.I):
        return MEDICATION_SAFETY

    if not personal:
        if _TREATMENT_OF.match(text) or (
            _TREATMENT.search(text) and is_educational_reference_query(text)
        ):
            return TREATMENT_INFORMATION
        if _SYMPTOMS_OF.match(text) or (
            _SYMPTOM_OF.search(text) and is_educational_reference_query(text)
        ):
            return SYMPTOM_INFORMATION
        if _CAUSES_OF.match(text) or (
            _CAUSES.search(text) and _named_topic_question(text)
        ):
            return POSSIBLE_CAUSES
        if is_educational_reference_query(text):
            return MEDICAL_EDUCATION
        if _DEFINITION.search(text) and not _DEICTIC.search(text):
            return MEDICAL_EDUCATION

    if status == "follow_up" or is_follow_question(text) or is_symptom_correction(text):
        if _TREATMENT.search(text) or _TREATMENT_OF.match(text):
            return TREATMENT_INFORMATION
        if _CAUSES.search(text) or _CAUSES_OF.match(text):
            return POSSIBLE_CAUSES
        if _SYMPTOM_OF.search(text):
            return SYMPTOM_INFORMATION
        return FOLLOW_UP

    if is_underspecified_medical_query(text) or intent == "ambiguous":
        return CLARIFICATION
    if personal:
        if _CAUSES.search(text):
            return POSSIBLE_CAUSES
        return SYMPTOM_INFORMATION
    return MEDICAL_EDUCATION


def infer_personal_context(query: str, related_texts: list[str] | None, reuse: bool) -> bool:
    if is_personal_symptom_query(query):
        return True
    if is_educational_reference_query(query) and not _DEICTIC.search(query or ""):
        return False
    if reuse:
        return any(is_personal_symptom_query(item) for item in (related_texts or []))
    return False


def uses_personalized_triage(question_type: str, personal_context: bool) -> bool:
    if question_type == EMERGENCY:
        return True
    if not personal_context:
        return False
    return question_type not in {
        MEDICAL_EDUCATION,
        TREATMENT_INFORMATION,
        GENERAL_KNOWLEDGE,
        OUT_OF_SCOPE,
    }


def uses_condition_cards(question_type: str, personal_context: bool) -> bool:
    if question_type in {
        MEDICAL_EDUCATION,
        TREATMENT_INFORMATION,
        MEDICATION_SAFETY,
        GENERAL_KNOWLEDGE,
        OUT_OF_SCOPE,
        CLARIFICATION,
    }:
        return False
    if question_type == EMERGENCY:
        return True
    return personal_context


def generation_mode(question_type: str, personal_context: bool) -> str:
    if question_type == TREATMENT_INFORMATION:
        return "treatment"
    if question_type == POSSIBLE_CAUSES and not personal_context:
        return "causes"
    if question_type == SYMPTOM_INFORMATION and not personal_context:
        return "symptom_education"
    if question_type == MEDICAL_EDUCATION or (question_type == FOLLOW_UP and not personal_context):
        return "education"
    if question_type == MEDICATION_SAFETY and not personal_context:
        return "education"
    return "symptom"
