"""Build readable answers from retrieved note bodies (never dump document titles as diagnoses)."""
from __future__ import annotations

import re
from typing import Any

_TITLE_DUMP = re.compile(
    r"^\s*(?:#{1,3}\s*)?possible explanations\s*:\s*(?:\n|\r\n)"
    r"(?:\s*\d+\.\s+.+\smay fit these symptoms.*(?:\n|\r\n)?)+",
    re.I,
)
_SOURCE_LINE = re.compile(r"^\[(\d+)\]\s*Source:\s*(.+?)(?:\s*\(([^)]*)\))?\s*$", re.I | re.M)
_POSSIBILITY_LIST = re.compile(
    r"(?:common )?(?:possibilities|possible causes|causes|reasons)\s+include\s+([^.]+)\.",
    re.I,
)
_RELATES_TO = re.compile(
    r"(?:relates? to|point(?:s)? to|suggest(?:s)?|often (?:from|due to))\s+([^.]+)\.",
    re.I,
)
_CAN_BE = re.compile(
    r"\b(?:can be|may be|often|include|such as)\s+([a-z][a-z0-9 \-/',]{3,80}?)(?:\.|,|;|$)",
    re.I,
)
_GENERIC_CONDITION = re.compile(
    r"^(?:knee|chest|head|back|arm|leg|wrist|hand|finger|throat|stomach|abdominal)?\s*"
    r"(?:pain|discomfort|ache|possibilities)\s*$",
    re.I,
)
_SYMPTOM_PATTERN_TITLE = re.compile(
    r"\b(when|after|while|during|on the|behind the|with|from)\b",
    re.I,
)
_FOLLOWUP_HINTS = (
    "Did this start after an injury or twist?",
    "Is the area swollen, locking, giving way, or red and hot?",
)
_BODY_ANCHORS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("knee", ("knee", "kneecap", "patella")),
    ("finger", ("finger", "fingertip", "digit")),
    ("wrist", ("wrist",)),
    ("hand", ("hand", "palm")),
    ("chest", ("chest", "breastbone", "sternum")),
    ("head", ("headache", "head pain", "migraine", "temple")),
    ("throat", ("throat", "tonsil")),
    ("back", ("back pain", "lower back", "spine", "lumbar")),
    ("abdomen", ("abdomen", "abdominal", "stomach", "belly", "tummy")),
)


def body_anchors(text: str) -> set[str]:
    lowered = (text or "").lower()
    found: set[str] = set()
    for label, terms in _BODY_ANCHORS:
        if any(re.search(rf"\b{re.escape(term)}\w*\b", lowered) for term in terms):
            found.add(label)
    return found


def evidence_matches_body_anchors(query: str, title: str, condition: str, text: str) -> bool:
    """When the user names a specific body area, keep only notes that mention it."""
    needed = body_anchors(query)
    if not needed:
        return True
    blob = f"{title} {condition} {text[:900]}".lower()
    present = body_anchors(blob)
    return bool(needed & present)


def is_symptom_pattern_label(value: str) -> bool:
    text = (value or "").strip()
    if not text:
        return False
    if _SYMPTOM_PATTERN_TITLE.search(text):
        return True
    if _GENERIC_CONDITION.match(text):
        return True
    return False


def is_title_dump_answer(answer: str | None) -> bool:
    text = (answer or "").strip()
    if not text:
        return False
    if _TITLE_DUMP.search(text):
        return True
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return False
    numbered = [line for line in lines if re.match(r"^\d+\.\s+.+\smay fit these symptoms", line, re.I)]
    return len(numbered) >= 2 and numbered[0].lower().find("may fit these symptoms") >= 0


def parse_context_blocks(context_blocks: list[str]) -> list[dict[str, str]]:
    notes: list[dict[str, str]] = []
    for block in context_blocks or []:
        match = _SOURCE_LINE.search(block or "")
        title = (match.group(2).strip() if match else "").strip() or "Retrieved medical document"
        source = (match.group(3).strip() if match and match.group(3) else "").strip()
        body = _SOURCE_LINE.sub("", block or "", count=1).strip()
        notes.append({"title": title, "source": source, "text": body})
    return notes


def _split_entities(blob: str) -> list[str]:
    parts = re.split(r",|;|\bor\b|\band\b", blob, flags=re.I)
    cleaned: list[str] = []
    seen: set[str] = set()
    for part in parts:
        item = re.sub(r"\s+", " ", (part or "").strip(" ."))
        item = re.sub(r"^(?:a|an|the)\s+", "", item, flags=re.I)
        if len(item) < 3 or len(item) > 60:
            continue
        if _GENERIC_CONDITION.match(item):
            continue
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(item[0].upper() + item[1:] if item else item)
    return cleaned


def clinical_ideas_from_notes(notes: list[dict[str, str]], *, limit: int = 4) -> list[dict[str, str]]:
    """Extract clinical ideas from note bodies; never return bare document titles as diagnoses."""
    ideas: list[dict[str, str]] = []
    seen: set[str] = set()
    for note in notes:
        text = note.get("text") or ""
        found: list[str] = []
        for match in _POSSIBILITY_LIST.finditer(text):
            found.extend(_split_entities(match.group(1)))
        for match in _RELATES_TO.finditer(text):
            found.extend(_split_entities(match.group(1)))
        if not found:
            for match in _CAN_BE.finditer(text[:500]):
                found.extend(_split_entities(match.group(1)))
        for name in found:
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            ideas.append(
                {
                    "condition": name,
                    "title": note.get("title") or "",
                    "source": note.get("source") or "",
                    "why": f"Mentioned in the note “{note.get('title') or 'retrieved reference'}”.",
                }
            )
            if len(ideas) >= limit:
                return ideas
    return ideas


def synthesize_notes_answer(
    query: str,
    context_blocks: list[str],
    *,
    mode: str = "symptom",
) -> str:
    """Readable overview grounded in note text, with citations by source title."""
    notes = parse_context_blocks(context_blocks)
    if not notes:
        return (
            "Not enough matching documents for a confident answer. "
            "Please rephrase, or see a doctor.\n"
            "Not a diagnosis — see a clinician if needed."
        )

    ideas = clinical_ideas_from_notes(notes, limit=4)
    cite = notes[0]["title"]
    lines: list[str] = []

    if mode in {"education", "symptom_education", "causes", "treatment"}:
        snippet = re.sub(r"\s+", " ", notes[0].get("text") or "").strip()
        if len(snippet) > 320:
            snippet = snippet[:317].rsplit(" ", 1)[0] + "..."
        lines.append(f"{snippet} (Source: {cite})")
        lines.append("Not a diagnosis — this is general information from reference notes.")
        return "\n".join(lines)

    topic = re.sub(r"\s+", " ", (query or "").strip()) or "these symptoms"
    lines.append(
        f"For “{topic}”, the retrieved notes describe common patterns rather than a single diagnosis."
    )
    if ideas:
        lines.append("Possible explanations supported by those notes:")
        for idea in ideas[:4]:
            source_title = idea.get("title") or cite
            lines.append(
                f"- {idea['condition']} — a possibility discussed in the notes "
                f"(Source: {source_title})."
            )
    else:
        # Fall back to a short paraphrase of the top note body, still citing the title.
        body = re.sub(r"\s+", " ", notes[0].get("text") or "").strip()
        first = re.split(r"(?<=[.!?])\s+", body)[0] if body else ""
        if first:
            lines.append(f"{first} (Source: {cite})")
        lines.append(
            "The note titles describe symptom situations (for example when walking or using stairs); "
            "they are not confirmed conditions."
        )

    lines.append(_FOLLOWUP_HINTS[0])
    lines.append(_FOLLOWUP_HINTS[1])
    lines.append("Not a diagnosis — see a clinician if needed.")
    return "\n".join(lines)


def rewrite_if_title_dump(answer: str | None, query: str, context_blocks: list[str], *, mode: str = "symptom") -> str:
    text = (answer or "").strip()
    if not is_title_dump_answer(text):
        return text
    return synthesize_notes_answer(query, context_blocks, mode=mode)
