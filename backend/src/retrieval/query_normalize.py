"""
Turn body-map metadata and free-text symptoms into a natural retrieval query.

The UI often sends lines like:
  Body map context (...): locations = Abdomen.
  Body map context (...): locations = Head; symptoms = Headache.

Those boilerplate strings embed poorly against clinical notes. Retrieval works
better with plain symptom language, while the original message is kept for
display, intent, and safety checks.
"""
from __future__ import annotations

import re

_BODY_MAP_BLOCK = re.compile(
    r"body map context\s*\(user-described discomfort, not a diagnosis\)\s*:\s*(.+?)(?:\.?\s*)?$",
    re.IGNORECASE | re.DOTALL,
)
_EXTRA_DETAIL = re.compile(r"\n\nextra detail:[\s\S]*$", re.IGNORECASE)
_LOCATIONS = re.compile(r"locations\s*=\s*([^;]+)", re.IGNORECASE)
_SYMPTOMS = re.compile(r"symptoms\s*=\s*([^;]+)", re.IGNORECASE)

# Location → retrieval phrasing only (not diagnosed diseases, not invented symptoms).
_LOCATION_PHRASES: dict[str, str] = {
    "head": "head discomfort",
    "chest": "chest discomfort",
    "abdomen": "abdomen discomfort",
    "stomach": "abdomen discomfort",
    "belly": "abdomen discomfort",
    "back": "back discomfort",
    "arm": "arm discomfort",
    "leg": "leg discomfort",
}

_SYNONYM_EXPAND: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(stomach|belly|tummy)\s+(pain|ache|discomfort|hurts?)\b", re.I), "abdominal pain"),
    (re.compile(r"\babdominal\s+(pain|ache|discomfort)\b", re.I), "abdomen stomach pain"),
    (re.compile(r"\bhead\s+(pain|ache|discomfort)\b", re.I), "headache"),
    (re.compile(r"\bchest\s+(discomfort|tightness|pressure)\b", re.I), "chest pain"),
    # Keep wording broad: help sleep-related headache notes compete without naming a disease.
    (
        re.compile(
            r"\b(headache|head pain).{0,48}\b(sleep(?:ing)? poorly|poor sleep|bad night|little sleep|"
            r"not sleep(?:ing)?|insomni\w*)\b|"
            r"\b(sleep(?:ing)? poorly|poor sleep|bad night|little sleep|not sleep(?:ing)?|insomni\w*)"
            r".{0,48}\b(headache|head pain)\b",
            re.I,
        ),
        "poor sleep headache tension-type headache",
    ),
    (
        re.compile(
            r"\b(chest (?:pain|ache|discomfort|pressure|tightness)|pain in (?:my |the )?chest)"
            r".{0,40}\bcough|"
            r"\bcough.{0,40}\b(chest (?:pain|ache|discomfort|pressure)|pain in (?:my |the )?chest)\b",
            re.I,
        ),
        "cough related chest wall pain",
    ),
    (re.compile(r"\b(knee|kneecap)\b", re.I), "knee pain"),
    (re.compile(r"\b(leg|thigh|calf|shin)\s+(pain|ache|hurt|issue|problem)\b", re.I), "leg pain"),
    (re.compile(r"\b(swollen|painful)\s+(calf|leg)\b", re.I), "calf swelling"),
    (re.compile(r"\bmigrane\b", re.I), "migraine"),
    (re.compile(r"\bdiarrea\b", re.I), "diarrhoea"),
    (re.compile(r"\bashtma\b", re.I), "asthma"),
    (re.compile(r"\bhypertention\b", re.I), "hypertension"),
]

# If a note's title/condition names a specific trigger, that same trigger must appear
# in the user's words. Body text can mention many differentials; titles are the claim.
_NOTE_CONTEXT_REQUIREMENTS: list[tuple[re.Pattern[str], re.Pattern[str]]] = [
    (
        re.compile(r"\b(alcohol|drinking|hangover)\b", re.I),
        re.compile(r"\b(alcohol|drink(?:ing|s)?|drank|drunk|hangover|beer|wine|liquor)\b", re.I),
    ),
    (
        re.compile(r"\b(anxiety|anxious|panic)\b", re.I),
        re.compile(r"\b(anxiety|anxious|panic|worried|worry|fear(?:ful)?|stressed|stress)\b", re.I),
    ),
    (
        re.compile(r"\b(caffeine|coffee)\b", re.I),
        re.compile(r"\b(caffeine|coffee|tea|energy drink)\b", re.I),
    ),
    (
        re.compile(r"\b(screens?|computer|phone)\b", re.I),
        re.compile(r"\b(screens?|computer|phone|laptop|monitor|tv)\b", re.I),
    ),
    (
        re.compile(r"\b(grind(?:ing)?|bruxism|clench(?:ing)?)\b", re.I),
        re.compile(r"\b(grind(?:ing)?|bruxism|clench(?:ing)?|teeth grinding)\b", re.I),
    ),
    (
        re.compile(r"\b(skip(?:ping)? breakfast|missed meal|fasting)\b", re.I),
        re.compile(r"\b(breakfast|meal|food|eating|ate|fast(?:ing)?|hungry|skip(?:ped|ping)?)\b", re.I),
    ),
    (
        re.compile(r"\b(days? off|weekend)\b", re.I),
        re.compile(r"\b(days? off|weekend|holiday|vacation|day off)\b", re.I),
    ),
    (
        re.compile(r"\b(pregnan|postpartum)\b", re.I),
        re.compile(r"\b(pregnan|postpartum|post[- ]partum)\b", re.I),
    ),
    (
        re.compile(r"\b(gym|workout|after exercise)\b", re.I),
        re.compile(r"\b(gym|workout|exercise|exercising|lifting|training|run(?:ning)?)\b", re.I),
    ),
    (
        re.compile(r"\b(exam|exams|board[- ]?exam)\b", re.I),
        re.compile(
            r"\b(exam|exams|board[- ]?exam|test(?:ing)?|stud(?:y|ying)|revision)\b",
            re.I,
        ),
    ),
]

_WARNING_SIGN_NOTE = re.compile(
    r"\b(warning signs?|red[- ]?flag|when (?:a |the )?\w+ needs a check|when to (?:see|seek))\b",
    re.I,
)

_CONTEXT_CUES: list[tuple[str, re.Pattern[str]]] = [
    ("sleep", re.compile(r"\b(sleep|slept|sleeping|insomni\w*|bad night|poor sleep)\b", re.I)),
    ("cough", re.compile(r"\b(cough|coughing)\b", re.I)),
    ("exercise", re.compile(r"\b(exercise|exercising|gym|workout|lifting|training|movement)\b", re.I)),
    ("eating", re.compile(r"\b(eat(?:ing)?|ate|meal|food|after (?:meals?|eating)|indigestion)\b", re.I)),
    ("alcohol", re.compile(r"\b(alcohol|drink(?:ing|s)?|drank|drunk|hangover|beer|wine)\b", re.I)),
    ("anxiety", re.compile(r"\b(anxiety|anxious|panic|worried|worry|fear(?:ful)?)\b", re.I)),
]

# Distinct symptom areas used to avoid mixing a new complaint with an old one.
_TOPIC_GROUPS: dict[str, tuple[str, ...]] = {
    "knee_leg": (
        "knee", "kneecap", "patella", "leg", "thigh", "calf", "shin",
        "ankle", "foot", "heel", "toe", "hip", "hamstring",
    ),
    "chest_lung": (
        "chest", "rib", "ribs", "cough", "breath", "lung", "wheeze",
        "pleurisy", "asthma",
    ),
    "head": ("headache", "migraine", "head", "dizzy", "dizziness", "vertigo"),
    "abdomen": (
        "abdomen", "abdominal", "stomach", "belly", "tummy", "nausea",
        "vomit", "diarrhea", "diarrhoea", "constipat",
    ),
    "throat": ("throat", "swallow", "tonsil"),
    "back": ("back", "spine", "sciatica", "lumbar"),
    "arm_shoulder": ("shoulder", "arm", "elbow", "wrist", "hand", "finger"),
    "urinary": ("urine", "urinat", "pee", "bladder", "kidney"),
    "skin": ("rash", "itch", "skin", "hives"),
}

# Additive / refinement language that can keep an active complaint.
# Do NOT include bare severity words like "little"/"mild"/"severe" here: those
# appear in brand-new complaints ("finger injured little") and previously caused
# unrelated prior chest evidence to be reused as if it were a follow-up.
_FOLLOW_HINT = re.compile(
    r"\b(also|as well|with that|tell me more|more about|second (one|condition|match)|"
    r"first (one|condition|match)|third (one|condition)|what about|how about|"
    r"worse|(getting|feeling|feels) better|it'?s better|it is better|is it better|"
    r"still have|and a |plus a |"
    r"left|right|both|side|since|yesterday|today|tonight|weeks?|days?|hours?|"
    r"when i|after|before|morning|walking|stairs|sitting|lifting|"
    r"extra detail:|more simply|in simple(r)? (words|language|terms)|"
    r"more detail|explain (that|this|it))\b",
    re.I,
)
_ADDITIVE_FOLLOW = re.compile(
    r"\b(also|as well|with that|plus a |still have|and a )\b",
    re.I,
)
# Untagged new symptom statements (often typos) must not inherit prior complaints.
_NEW_SYMPTOM_CUE = re.compile(
    r"\b("
    r"pain|hurt|hurts|aching|ache|sore|injured?|injure|injury|"
    r"swollen|swelling|bleed(?:ing)?|cut|burn(?:ed|ing)?|rash|fever|"
    r"cough(?:ing)?|dizzy|nause(?:a|ous)?|vomit(?:ing)?"
    r")\w*\b",
    re.I,
)
# Everyday advice/cause questions that keep the active complaint (fu01–fu04).
_FOLLOW_QUESTION = re.compile(
    r"\b(what could cause (this|it|that)|what (can|should) i do|"
    r"what warning signs|warning signs should i|"
    r"when should i (seek|see|get) (help|care|a doctor|an? emergency)|"
    r"what (should|can) i (watch|look) for|"
    r"how (can|do|should) i (treat|ease|help|relieve|manage) (this|it)|"
    r"what causes (this|it|that)|is (this|it) (serious|normal|ok|okay)|"
    r"can (it|this|that) be treated|how is (it|this|that) treated|"
    r"explain (that|this|it)( more)?( simply)?|"
    r"more simply|in simple(r)? (words|language|terms)|more detail)\b",
    re.I,
)
_CORRECTION = re.compile(
    r"\b((i |sorry[, ]+i )?meant|not my |not the |actually (it'?s|i meant))\b",
    re.I,
)
_NEW_COMPLAINT_SHAPE = re.compile(
    r"\b(i have|i've got|i have got|i am having|i'm having|now i have)\b",
    re.I,
)
_REFINEMENT = re.compile(
    r"\b(just|still|only|no longer|not anymore|except|"
    r"no (fever|cough|pain|rash)|without (the |a )?(fever|cough|pain))\b",
    re.I,
)
_NEGATED_BODY = re.compile(r"\bnot (?:my |the |a )?([a-z]+)\b", re.I)
_MEANT_BODY = re.compile(r"\bmeant (?:my |the |an? )?([a-z]+)\b", re.I)
_BREATHLESS_NOW = re.compile(
    r"\b(breathless|short(ness)? of breath|can'?t breathe|cannot breathe|"
    r"difficulty breathing|gasping for air|can'?t catch (my )?breath)\b",
    re.I,
)
_CALF_SWELLING = re.compile(
    r"\b((swollen|painful|swell\w*|pain)\s+(calf|lower leg)|(calf|lower leg)\s+"
    r"(is |feels )?(swollen|painful|swell\w*|sore))\b",
    re.I,
)
_LONG_TRAVEL = re.compile(
    r"\b(long[- ]?(flight|haul|drive|bus|train|travel)|after a long flight|"
    r"after a flight(?!\s+of))\b",
    re.I,
)


def _split_csv(value: str) -> list[str]:
    parts: list[str] = []
    for raw in re.split(r"[,;/|]+", value or ""):
        item = raw.strip(" .")
        if item:
            parts.append(item)
    return parts


def parse_body_map(query: str) -> tuple[str, list[str], list[str]]:
    """Return (free_text, locations, symptoms) from a composed user message."""
    text = (query or "").strip()
    text = _EXTRA_DETAIL.sub("", text).strip()
    locations: list[str] = []
    symptoms: list[str] = []
    free = text
    match = _BODY_MAP_BLOCK.search(text)
    if match:
        details = match.group(1).strip().rstrip(".")
        free = _BODY_MAP_BLOCK.sub("", text).strip()
        loc_m = _LOCATIONS.search(details)
        sym_m = _SYMPTOMS.search(details)
        if loc_m:
            locations = _split_csv(loc_m.group(1))
        if sym_m:
            symptoms = _split_csv(sym_m.group(1))
        # Fallback when only "locations = X" style without labels failed parsing
        if not locations and not symptoms and "=" not in details:
            locations = _split_csv(details)
    return free, locations, symptoms


def _location_phrase(label: str) -> str:
    key = re.sub(r"[^a-z]", "", (label or "").lower())
    return _LOCATION_PHRASES.get(key, f"{label.strip().lower()} discomfort" if label.strip() else "")


def _dedupe_phrases(parts: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for part in parts:
        cleaned = re.sub(r"\s+", " ", (part or "").strip())
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        # Skip if already covered by a longer phrase
        if any(key in existing for existing in seen):
            continue
        seen = {s for s in seen if s not in key}
        seen.add(key)
        out.append(cleaned)
    return out


_EXACT_TOPIC_TERMS = {"head", "arm", "back", "hand", "hip", "leg", "foot", "rib"}


def retrieval_topics(text: str) -> set[str]:
    """Return coarse symptom-area labels present in a query or note."""
    lowered = _apply_typos(text or "").lower()
    if not lowered:
        return set()
    found: set[str] = set()
    for topic, terms in _TOPIC_GROUPS.items():
        for term in terms:
            pattern = rf"\b{re.escape(term)}s?\b" if term in _EXACT_TOPIC_TERMS else rf"\b{re.escape(term)}\w*\b"
            if re.search(pattern, lowered):
                found.add(topic)
                break
    return found


def is_follow_question(query: str) -> bool:
    return bool(_FOLLOW_QUESTION.search(query or ""))


def is_symptom_correction(query: str) -> bool:
    return bool(_CORRECTION.search(query or ""))


def apply_symptom_correction(text: str, query: str) -> str:
    negated = contradicted_terms(query)
    if not negated:
        return text
    return _rewrite_correction(text, negated, correction_replacement(query))


def contradicted_terms(query: str) -> set[str]:
    return {match.group(1).lower() for match in _NEGATED_BODY.finditer(query or "")}


def correction_replacement(query: str) -> str | None:
    match = _MEANT_BODY.search(query or "")
    return match.group(1).lower() if match else None


def _rewrite_correction(text: str, negated: set[str], replacement: str | None) -> str:
    rewritten = text
    for term in negated:
        if replacement:
            rewritten = re.sub(rf"\b{re.escape(term)}\b", replacement, rewritten, flags=re.I)
        else:
            rewritten = re.sub(rf"\b{re.escape(term)}\b", "", rewritten, flags=re.I)
    return re.sub(r"\s+", " ", rewritten).strip()


def is_travel_calf_breathless_followup(query: str, prior_texts: list[str]) -> bool:
    """Breathlessness after a swollen/painful calf and prolonged travel."""
    if not _BREATHLESS_NOW.search(query or ""):
        return False
    blob = " ".join(prior_texts)
    return bool(_CALF_SWELLING.search(blob) and _LONG_TRAVEL.search(blob))


def _is_follow_language(query: str) -> bool:
    return bool(
        _FOLLOW_HINT.search(query or "")
        or _FOLLOW_QUESTION.search(query or "")
        or _CORRECTION.search(query or "")
    )


def related_history_texts(query: str, prior_texts: list[str]) -> list[str]:
    """Keep only earlier messages that share this question's body area."""
    if is_symptom_correction(query):
        related = prior_texts[-3:]
        negated = contradicted_terms(query)
        replacement = correction_replacement(query)
        if negated:
            related = [_rewrite_correction(text, negated, replacement) for text in related]
        return related
    if is_travel_calf_breathless_followup(query, prior_texts):
        return prior_texts[-3:]
    current = retrieval_topics(query)
    if not current:
        if is_follow_question(query) or _ADDITIVE_FOLLOW.search(query or ""):
            return prior_texts[-1:]
        # "finger injured little" (typos / untagged) is a new complaint, not a follow-up.
        if _NEW_SYMPTOM_CUE.search(query or ""):
            return []
        return prior_texts[-1:] if _is_follow_language(query) else []
    related = [text for text in prior_texts if retrieval_topics(text) & current]
    return related[-3:]


def should_reuse_retrieval_history(query: str, prior_texts: list[str]) -> bool:
    """Reuse earlier symptom text only for follow-ups, not a new complaint."""
    if not prior_texts:
        return False
    current = retrieval_topics(query)
    prior: set[str] = set()
    for text in prior_texts:
        prior |= retrieval_topics(text)
    if is_symptom_correction(query):
        return True
    if is_travel_calf_breathless_followup(query, prior_texts):
        return True
    if _REFINEMENT.search(query or "") and prior_texts:
        # Refinement of an active complaint (e.g. "no fever now") may reuse.
        # A disjoint new body area must not.
        if current and prior and current.isdisjoint(prior):
            return False
        return True
    if current and prior and current.isdisjoint(prior):
        return False
    if _NEW_COMPLAINT_SHAPE.search(query or "") and not _REFINEMENT.search(query or ""):
        return False
    if not current:
        # Explicit advice / additive follow-ups keep the active complaint.
        if is_follow_question(query) or _ADDITIVE_FOLLOW.search(query or ""):
            return True
        # Untagged new symptom text must start a fresh retrieval thread.
        if _NEW_SYMPTOM_CUE.search(query or ""):
            return False
        return _is_follow_language(query)
    if _is_follow_language(query):
        return True
    if current and prior and current & prior:
        return True
    return False


_TYPO_SUBS = [
    (re.compile(r"\bmigrane\b", re.I), "migraine"),
    (re.compile(r"\bdiarrea\b", re.I), "diarrhoea"),
    (re.compile(r"\bashtma\b", re.I), "asthma"),
    (re.compile(r"\bhypertention\b", re.I), "hypertension"),
    (re.compile(r"\bfingure\b", re.I), "finger"),
    (re.compile(r"\bfinguer\b", re.I), "finger"),
]
_PAIN_INJECT = {
    "knee pain",
    "chest pain",
    "headache",
    "abdominal pain",
    "abdomen stomach pain",
    "leg pain",
    "calf swelling",
}


def _apply_typos(text: str) -> str:
    updated = text
    for pattern, replacement in _TYPO_SUBS:
        updated = pattern.sub(replacement, updated)
    return updated


def expand_synonyms(text: str, *, inject_symptoms: bool = True) -> str:
    expanded = _apply_typos(text)
    extras: list[str] = []
    lowered = expanded.lower()
    negated = contradicted_terms(expanded)
    for pattern, phrase in _SYNONYM_EXPAND:
        if not inject_symptoms and phrase.lower() in _PAIN_INJECT:
            continue
        if not pattern.search(expanded):
            continue
        if negated:
            hits = [match.group(0).lower() for match in pattern.finditer(expanded)]
            if hits and all(any(term in hit or hit in term for term in negated) for hit in hits):
                continue
        phrase_l = phrase.lower()
        # Skip near-duplicates (e.g. "left side chest pain" vs "left sided chest pain").
        if phrase_l in lowered:
            continue
        compact = re.sub(r"sided", "side", re.sub(r"[^a-z0-9]+", "", phrase_l))
        existing = re.sub(r"sided", "side", re.sub(r"[^a-z0-9]+", "", lowered))
        if compact and compact in existing:
            continue
        extras.append(phrase)
        lowered = f"{lowered} {phrase_l}"
    if extras:
        expanded = f"{expanded} {' '.join(extras)}"
    return expanded


_GENERIC_DISEASE_WORDS = {
    "a", "an", "the", "rare", "common", "this", "that", "genetic", "inherited", "some", "any",
    "what", "which", "causes", "cause", "about", "called", "named", "known",
}
_NAMED_DISEASE = re.compile(
    r"\b((?:[a-z][a-z'-]+)(?:\s+[a-z][a-z'-]+){0,3})\s+diseases?\b",
    re.I,
)
_VAGUE_MEDICAL = re.compile(
    r"^\s*(pain|hurt|ache|unwell|sick|ill)\b|"
    r"\b(i feel unwell|something is wrong|i feel (off|bad)|cannot describe)\b",
    re.I,
)


def named_disease_phrases(query: str) -> list[str]:
    """Distinctive 'X disease' phrases, ignoring 'a rare disease' style wording."""
    phrases: list[str] = []
    for match in _NAMED_DISEASE.finditer(query or ""):
        words = [
            token
            for token in re.findall(r"[a-z]+", match.group(1).lower())
            if token not in _GENERIC_DISEASE_WORDS and len(token) > 2
        ]
        if words:
            phrases.append(" ".join(words))
    return phrases


def evidence_supports_named_disease(query: str, texts: list[str]) -> bool:
    phrases = named_disease_phrases(query)
    if not phrases:
        return True
    blob = " ".join(texts).lower()
    return any(phrase in blob for phrase in phrases)


def reported_context_cues(query: str) -> set[str]:
    """Coarse context labels the user actually mentioned."""
    text = query or ""
    return {name for name, pattern in _CONTEXT_CUES if pattern.search(text)}


def note_claims_unreported_context(query: str, title: str, condition: str = "", doc_id: str = "") -> bool:
    """True when the note's title asserts a trigger the user never reported.

    Only title/condition/id are checked. Body text often lists many differentials.
    """
    claim = f"{title or ''} {condition or ''} {doc_id or ''}"
    if not claim.strip():
        return False
    for note_pattern, query_pattern in _NOTE_CONTEXT_REQUIREMENTS:
        if note_pattern.search(claim) and not query_pattern.search(query or ""):
            return True
    return False


def is_warning_sign_note(title: str, condition: str = "", doc_id: str = "") -> bool:
    return bool(_WARNING_SIGN_NOTE.search(f"{title or ''} {condition or ''} {doc_id or ''}"))


# Avoid matching "blood pressure" / "blood-pressure" compounds as hemoptysis evidence.
_BLOOD_TOKEN = re.compile(r"(?<![\w-])blood(?!(?:-|\s+)pressure)(?![\w-])", re.I)
_HEMOPTYSIS_NOTE_STRONG = re.compile(
    r"(?<![\w-])(hemoptysis|haemoptysis)(?![\w-])|"
    r"cough(?:ing)?\s+up\s+(?:large\s+amounts?\s+of\s+)?blood|"
    r"coughing\s+blood|"
    r"blood\s+in\s+(?:the\s+)?(?:sputum|phlegm|mucus)|"
    r"bloody\s+(?:sputum|phlegm|mucus)",
    re.I,
)
_TB_TITLE = re.compile(r"(?<![\w-])(tuberculosis|tb)(?![\w-])", re.I)
_COUGH_BLOOD_MENTION = re.compile(
    r"(?:you\s+)?cough(?:ing)?\s+(?:up\s+)?(?:large\s+amounts?\s+of\s+)?blood|"
    r"mucus\s+is\s+bloody",
    re.I,
)
_IRRELEVANT_BLOOD_NOTE = re.compile(
    r"(?<![\w-])(toilet|stool|semen|urine|period|menstrual|nosebleed|gum|rectal)(?![\w-])",
    re.I,
)


def _clinical_note_body(text: str) -> str:
    """Drop trailing see-a-doctor / seek-emergency footers that mention cough blood generically."""
    raw = text or ""
    parts = re.split(
        r"(?i)\n\s*(?:see a doctor|seek (?:emergency )?care|seek urgent care)\b",
        raw,
        maxsplit=1,
    )
    return parts[0]


def note_addresses_hemoptysis(
    title: str,
    condition: str = "",
    doc_id: str = "",
    text: str = "",
) -> int:
    """How well a note supports blood-in-sputum / hemoptysis explanations.

    Returns 0 when the note is not useful for that presentation. Higher values
    prefer notes that discuss coughing blood or related lung conditions without
    treating a bare \"blood\" token (e.g. blood-pressure tablets) as a match.
    Ordinary cough notes that only mention blood in a standard footer score 0.
    """
    head = f"{title or ''} {condition or ''} {doc_id or ''}"
    body = (text or "")[:700]
    clinical = f"{head} {_clinical_note_body(body)}"
    blob = f"{head} {body}"
    if not blob.strip():
        return 0
    if _IRRELEVANT_BLOOD_NOTE.search(head):
        return 0
    if _HEMOPTYSIS_NOTE_STRONG.search(clinical):
        return 3
    if _TB_TITLE.search(head) and _BLOOD_TOKEN.search(clinical):
        return 3
    if re.search(r"\bcough", head, re.I) and _BLOOD_TOKEN.search(head):
        return 2
    if is_warning_sign_note(title, condition, doc_id) and _COUGH_BLOOD_MENTION.search(blob):
        return 2
    return 0


def note_context_fit(query: str, title: str, condition: str = "", text: str = "") -> int:
    """How many reported context cues also appear in the note title or condition.

    Body text is ignored so a warning line like "wake you from sleep" cannot
    outrank a better-fitting explanation.
    """
    del text
    cues = reported_context_cues(query)
    if not cues:
        return 0
    blob = f"{title or ''} {condition or ''}"
    score = 0
    for name in cues:
        for cue_name, pattern in _CONTEXT_CUES:
            if cue_name == name and pattern.search(blob):
                score += 1
                break
    return score


def is_underspecified_medical_query(query: str) -> bool:
    """Single generic complaints should not reuse unrelated pain cards."""
    plain = re.sub(r"\s+", " ", (query or "").strip())
    if not plain or named_disease_phrases(plain) or retrieval_topics(plain):
        return False
    return bool(_VAGUE_MEDICAL.search(plain))


def normalize_retrieval_query(query: str) -> str:
    """
    Build a compact natural-language query for embedding / reranking.

    Does not invent reported symptoms: a bare body location becomes
    '<region> discomfort', not a disease or a specific symptom the user
    never selected.
    """
    free, locations, symptoms = parse_body_map(query)
    parts: list[str] = []
    if free:
        parts.append(free)
    for symptom in symptoms:
        parts.append(symptom)
    for location in locations:
        # If the user already named a symptom for this region, keep location
        # as a short anchor only; otherwise add discomfort phrasing.
        loc_l = location.lower()
        already = any(loc_l in (s or "").lower() or (s or "").lower() in loc_l for s in symptoms)
        if already or (free and loc_l in free.lower()):
            parts.append(location)
        else:
            parts.append(_location_phrase(location) or location)
    combined = " ".join(_dedupe_phrases(parts))
    if not combined:
        combined = re.sub(r"\s+", " ", (query or "").strip())
    from src.pipeline.question_type import is_educational_reference_query, rewrite_educational_search

    combined = rewrite_educational_search(combined, original=query)
    inject = not is_educational_reference_query(query)
    return expand_synonyms(combined, inject_symptoms=inject)[:2000]
