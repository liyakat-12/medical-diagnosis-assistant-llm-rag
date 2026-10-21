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
    (re.compile(r"\b(stomach|belly|tummy)\s+(pain|ache|discomfort|hurt)\b", re.I), "abdominal pain"),
    (re.compile(r"\babdominal\s+(pain|ache|discomfort)\b", re.I), "abdomen stomach pain"),
    (re.compile(r"\bhead\s+(pain|ache|discomfort)\b", re.I), "headache"),
    (re.compile(r"\bchest\s+(discomfort|tightness|pressure)\b", re.I), "chest pain"),
]


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


def expand_synonyms(text: str) -> str:
    expanded = text
    extras: list[str] = []
    lowered = expanded.lower()
    for pattern, phrase in _SYNONYM_EXPAND:
        if not pattern.search(expanded):
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
    return expand_synonyms(combined)[:2000]
