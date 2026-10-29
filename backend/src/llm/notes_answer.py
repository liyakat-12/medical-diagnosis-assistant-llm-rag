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
# Diagnostic "can/may/could be X" only — bare "often/include/such as" grabbed triggers and verbs.
_CAN_BE = re.compile(
    r"\b(?:can be|may be|could be|sometimes called|also called|called)\s+"
    r"(?:(?:a|an|the)\s+)?([a-z][a-z0-9 \-/',]{2,50}?)(?:\.|,|;|$)",
    re.I,
)
_BAD_LABEL_LEAD = re.compile(
    r"^(?:"
    r"called|follows?|following|considered|consider|study|studies|signs? of|"
    r"linked to|often|usually|after|before|with|from|due to|during|"
    r"lasts?|weeks?|days?|extra|helpful|first steps|mentioned|"
    r"less typical|more common|not this|once a"
    r")\b",
    re.I,
)
_GENERIC_CONDITION = re.compile(
    r"^(?:"
    r"(?:knee|chest|head|neck|back|arm|leg|wrist|hand|finger|throat|stomach|abdominal|"
    r"belly button|navel|umbilical|adam'?s apple)\s+"
    r"(?:pain|discomfort|ache)|"
    r"(?:pain|discomfort|ache|possibilities|headache)|"
    r"sore throat"
    r")\s*$",
    re.I,
)
# Note headings / catalog labels — not diagnoses (even when used as condition metadata).
# Keep meaningful labels such as "Exam Headache"; reject thin study/strain topic heads.
_DOCUMENT_TOPIC_OR_WARNING = re.compile(
    r"(?:"
    r"\b(?:possibilities|common reasons|overview|introduction|differential)\b|"
    r"\b(?:warning signs?|red[- ]?flags?)\b|"
    r"^(?:study|exam|school|homework)\s+(?:eye\s+)?(?:strain|ache)\b"
    r")",
    re.I,
)
_WARNING_CATEGORY_SUFFIX = re.compile(
    r"\s+(?:warning signs?|red[- ]?flags?)\s*$",
    re.I,
)
_SYMPTOM_PATTERN_TITLE = re.compile(
    r"\b(when|after|while|during|on the|behind the|with|from)\b",
    re.I,
)
_SELF_CARE = re.compile(
    r"\b(helpful first steps|try |rest|ice|fluids?|hydrate|self-care|over-the-counter|"
    r"paracetamol|ibuprofen|handrail|shorter|supportive|gentle|avoid )\b",
    re.I,
)
_WARNING = re.compile(
    r"\b(see a doctor|seek (?:urgent|emergency)|call \d+|warning|seek care|"
    r"get (?:urgent|emergency)|go to (?:a )?hospital|red flag)\b",
    re.I,
)
_COLLOQUIAL_LEAD = re.compile(
    r"\b(people often say|a common complaint is|my \w+ hurts|why does my)\b",
    re.I,
)
_NON_CONDITION_LABEL = re.compile(
    r"^(?:"
    r"dry air|humid air|cold air|warm drinks?|cool drinks?|"
    r"splint|brace|cast|ice|rest|fluids?|honey|saline|"
    r"other treatment|self-?care|home care|first steps|"
    r"one-sided|pulsing|certain foods|rapidly fatal|"
    r"periods?|bleeding|extra lifting|follows a cough|"
    r"less typical in women|tender chest wall|"
    r"cardiac|neurological|musculoskeletal|"
    r".*\bself-?care\b|"
    r"kneeling knee swelling|knee swelling|swelling"
    r")$",
    re.I,
)
_SHORT_CONDITION_OK = {
    "gout",
    "strep",
    "migraine",
    "asthma",
    "gerd",
    "uti",
    "flu",
    "cold",
    "croup",
    "angina",
    "clot",
    "dvt",
    "sciatica",
}
_LABEL_EXPAND = {
    "viral": "Viral infection",
    "strep": "Strep throat",
    "clot": "Blood clot concern",
    "cervicogenic": "Cervicogenic headache",
}
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
    # Titles are short; do not treat long clinical sentences as pattern labels.
    if len(text) > 80:
        return False
    if _SYMPTOM_PATTERN_TITLE.search(text):
        return True
    if _GENERIC_CONDITION.match(text):
        return True
    if _DOCUMENT_TOPIC_OR_WARNING.search(text):
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
    return len(numbered) >= 2


def parse_context_blocks(context_blocks: list[str]) -> list[dict[str, str]]:
    notes: list[dict[str, str]] = []
    for block in context_blocks or []:
        match = _SOURCE_LINE.search(block or "")
        title = (match.group(2).strip() if match else "").strip() or "Retrieved medical document"
        source = (match.group(3).strip() if match and match.group(3) else "").strip()
        body = _SOURCE_LINE.sub("", block or "", count=1).strip()
        # Drop leading markdown heading that duplicates the title.
        body = re.sub(r"^#+\s+.+\n+", "", body).strip()
        notes.append({"title": title, "source": source, "text": body})
    return notes


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", (text or "")).strip())
    return [part.strip() for part in parts if len(part.strip()) >= 20]


def _trim_sentence(text: str, limit: int = 220) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "")).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rsplit(" ", 1)[0] + "..."


def _cited_sentence(text: str, title: str) -> str:
    """Keep citation on the same sentence so faithfulness audit does not orphan (Source: ...)."""
    body = re.sub(r"\s+", " ", (text or "")).strip().rstrip(" .")
    cite = (title or "Retrieved medical document").strip()
    return f"{body} (Source: {cite})."


def normalize_condition_label(value: str) -> str | None:
    item = re.sub(r"\s+", " ", (value or "").strip(" .").replace("_", " "))
    item = re.sub(r"^(?:a|an|the)\s+", "", item, flags=re.I)
    item = re.sub(
        r"^(?:relates? to|points? to|suggests?|often (?:from|due to|called)|"
        r"(?:sometimes|also)\s+called|called|include[sd]?)\s+",
        "",
        item,
        flags=re.I,
    )
    item = re.sub(r"^(?:a|an|the)\s+", "", item, flags=re.I)
    # Prefer the diagnosis noun after "… or tension-type headache …"
    or_parts = re.split(r"\s+or\s+", item, maxsplit=1, flags=re.I)
    if len(or_parts) == 2 and len(or_parts[1].split()) >= 2:
        item = or_parts[1].strip()
    # "{Disease} Warning Signs" / "… Red Flag" → keep the disease, drop the category tail.
    stripped = _WARNING_CATEGORY_SUFFIX.sub("", item).strip()
    if stripped and stripped.lower() != item.lower():
        item = stripped
    if len(item) < 3 or len(item) > 60:
        return None
    if _GENERIC_CONDITION.match(item) or is_symptom_pattern_label(item):
        return None
    if re.match(r"^(?:how|what|why|when|where|which|whether)\b", item, re.I):
        return None
    if _BAD_LABEL_LEAD.match(item):
        return None
    if _DOCUMENT_TOPIC_OR_WARNING.search(item):
        return None
    key = item.lower()
    if _NON_CONDITION_LABEL.match(key):
        return None
    # Reject verb-y or fragment labels that are not noun diagnoses.
    if re.search(r"\b(follows?|lifting|considered|burst organ)\b", key):
        return None
    if key in _LABEL_EXPAND:
        item = _LABEL_EXPAND[key]
        key = item.lower()
    tokens = key.split()
    if len(tokens) == 1:
        if key in _SHORT_CONDITION_OK or key.endswith(("itis", "osis", "emia", "oma", "pathy", "algia")):
            pass
        elif len(key) >= 6 and key.isalpha() and not _NON_CONDITION_LABEL.match(key):
            # Allow longer clinical nouns such as sciatica; keep rejecting thin fragments.
            pass
        else:
            return None
    # Drop treatment/process fragments and note-title residue.
    if re.search(r"\b(treatment|self-?care|steps?|drinks?|incense|supportive shoes)\b", key):
        return None
    return item[0].upper() + item[1:] if item else None


def _split_entities(blob: str) -> list[str]:
    parts = re.split(r",|;|\bor\b|\band\b", blob, flags=re.I)
    cleaned: list[str] = []
    seen: set[str] = set()
    for part in parts:
        item = normalize_condition_label(part or "")
        if not item:
            continue
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(item)
    return cleaned


def _why_for_idea(name: str, note_text: str, title: str) -> str:
    lowered = name.lower()
    tokens = [tok for tok in re.split(r"\s+", lowered) if len(tok) > 3]
    for sentence in _sentences(note_text):
        blob = sentence.lower()
        if lowered not in blob and not (tokens and all(tok in blob for tok in tokens[:2])):
            continue
        # Avoid repeating the same multi-item list on every card.
        if blob.count(",") >= 2 and re.search(r"\binclude\b|\bor\b", sentence, re.I):
            return "Mentioned in the notes as a possible explanation for this symptom pattern."
        return _trim_sentence(sentence, 160)
    # Do not attach an unrelated first sentence (e.g. viral overview on a strep card).
    return f'Mentioned in the retrieved note "{title or "medical reference"}" as a possible explanation.'


def clinical_ideas_from_notes(notes: list[dict[str, str]], *, limit: int = 4) -> list[dict[str, str]]:
    """Extract clinical ideas from note bodies; never return bare document titles as diagnoses."""
    ideas: list[dict[str, str]] = []
    seen: set[str] = set()
    for note in notes:
        text = note.get("text") or ""
        title = note.get("title") or ""
        found: list[str] = []
        for match in _POSSIBILITY_LIST.finditer(text):
            found.extend(_split_entities(match.group(1)))
        for match in _RELATES_TO.finditer(text):
            found.extend(_split_entities(match.group(1)))
        if not found:
            for match in _CAN_BE.finditer(text[:700]):
                found.extend(_split_entities(match.group(1)))
        for name in found:
            label = normalize_condition_label(name)
            if not label:
                continue
            key = label.lower()
            if key in seen:
                continue
            seen.add(key)
            why = _why_for_idea(label, text, title)
            ideas.append(
                {
                    "condition": label,
                    "title": title,
                    "source": note.get("source") or "",
                    "why": why,
                    "explanation": why,
                }
            )
            if len(ideas) >= limit:
                return ideas
    return ideas


def _pick_sentences(notes: list[dict[str, str]], predicate, *, limit: int = 2) -> list[tuple[str, str]]:
    picked: list[tuple[str, str]] = []
    seen: set[str] = set()
    for note in notes:
        title = note.get("title") or "Retrieved medical document"
        for sentence in _sentences(note.get("text") or ""):
            if not predicate(sentence):
                continue
            key = sentence.lower()[:80]
            if key in seen:
                continue
            seen.add(key)
            picked.append((_trim_sentence(sentence, 240), title))
            if len(picked) >= limit:
                return picked
    return picked


def _education_answer(query: str, notes: list[dict[str, str]], *, mode: str) -> str:
    """Structured general-information answer from one or more notes."""
    primary = notes[0]
    cite = primary["title"]
    body_sents = _sentences(primary.get("text") or "")
    lines: list[str] = []

    if mode == "causes":
        lines.append("Possible causes supported by the reference notes:")
        ideas = clinical_ideas_from_notes(notes, limit=4)
        if ideas:
            for idea in ideas:
                lines.append(
                    _cited_sentence(
                        f"- {idea['condition']}: {idea.get('explanation') or idea.get('why')}",
                        idea.get("title") or cite,
                    )
                )
        elif body_sents:
            for sentence, title in _pick_sentences(notes, lambda s: True, limit=3):
                lines.append(_cited_sentence(f"- {sentence}", title))
        else:
            lines.append(_cited_sentence("The notes are limited on causes for this topic", cite))
    elif mode == "treatment":
        lines.append("General management options mentioned in the notes:")
        care = _pick_sentences(notes, lambda s: bool(_SELF_CARE.search(s)), limit=3)
        if not care:
            care = _pick_sentences(notes, lambda s: True, limit=2)
        for sentence, title in care:
            lines.append(_cited_sentence(f"- {sentence}", title))
        warn = _pick_sentences(notes, lambda s: bool(_WARNING.search(s)), limit=2)
        if warn:
            lines.append("Warning signs from the notes:")
            for sentence, title in warn:
                lines.append(_cited_sentence(f"- {sentence}", title))
    elif mode == "symptom_education":
        lines.append("Common symptoms and warning signs from the notes:")
        for sentence, title in _pick_sentences(notes, lambda s: True, limit=4):
            lines.append(_cited_sentence(f"- {sentence}", title))
    else:
        # education / what-is
        topic = re.sub(r"\s+", " ", (query or "").strip()) or "this topic"
        definition = body_sents[0] if body_sents else ""
        if definition:
            lines.append(_cited_sentence(definition, cite))
        else:
            lines.append(
                _cited_sentence(
                    f'The notes discuss "{topic}" but do not give a clear short definition',
                    cite,
                )
            )
        extra = _pick_sentences(notes[1:] or notes, lambda s: True, limit=2)
        for sentence, title in extra:
            if definition and sentence.startswith(definition[:40]):
                continue
            lines.append(_cited_sentence(sentence, title))
        warn = _pick_sentences(notes, lambda s: bool(_WARNING.search(s)), limit=1)
        for sentence, title in warn:
            lines.append(_cited_sentence(f"Important: {sentence}", title))

    lines.append("Not a diagnosis — this is general information from reference notes.")
    return "\n".join(lines)


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

    if mode in {"education", "symptom_education", "causes", "treatment"}:
        return _education_answer(query, notes, mode=mode)

    from src.safety.followups import clarifying_questions

    ideas = clinical_ideas_from_notes(notes, limit=4)
    cite = notes[0]["title"]
    topic = re.sub(r"\s+", " ", (query or "").strip()) or "these symptoms"
    lines: list[str] = []

    # Keep rare/alarm titles available for cards, but do not lead the overview with them.
    _rare_title = re.compile(
        r"\b(tumou?r|cancer|heart attack|stroke|aneurysm|meningitis|sepsis)\b",
        re.I,
    )
    overview_notes = [note for note in notes if not _rare_title.search(note.get("title") or "")] or notes

    overview = _pick_sentences(
        overview_notes,
        lambda s: not _WARNING.search(s) and not _COLLOQUIAL_LEAD.search(s),
        limit=2,
    )
    if not overview:
        overview = _pick_sentences(overview_notes, lambda s: not _WARNING.search(s), limit=2)
    if overview:
        first, first_title = overview[0]
        lines.append(_cited_sentence(f'About "{topic}": {first}', first_title))
        if len(overview) > 1:
            second, second_title = overview[1]
            lines.append(_cited_sentence(second, second_title or first_title))
    else:
        lines.append(
            _cited_sentence(
                f'For "{topic}", the retrieved notes describe common patterns rather than a single diagnosis',
                cite,
            )
        )

    if ideas:
        lines.append("Possible explanations supported by those notes:")
        for idea in ideas[:4]:
            source_title = idea.get("title") or cite
            explanation = idea.get("explanation") or idea.get("why") or ""
            brief = _trim_sentence(explanation, 140)
            lines.append(_cited_sentence(f"- **{idea['condition']}**: {brief}", source_title))
    else:
        lines.append(
            "The notes describe symptom patterns rather than naming a confirmed condition. "
            "Titles such as activity-related pain situations are not diagnoses."
        )

    care = _pick_sentences(notes, lambda s: bool(_SELF_CARE.search(s)), limit=2)
    if care:
        lines.append("Self-care ideas mentioned in the notes:")
        for sentence, title in care:
            lines.append(_cited_sentence(f"- {sentence}", title))

    warn = _pick_sentences(notes, lambda s: bool(_WARNING.search(s)), limit=2)
    if warn:
        lines.append("When to seek care (from the notes):")
        for sentence, title in warn:
            lines.append(_cited_sentence(f"- {sentence}", title))

    for question in clarifying_questions(query, limit=2):
        lines.append(question)

    lines.append("Not a diagnosis — see a clinician if needed.")
    return "\n".join(lines)


def rewrite_if_title_dump(answer: str | None, query: str, context_blocks: list[str], *, mode: str = "symptom") -> str:
    text = (answer or "").strip()
    if not is_title_dump_answer(text):
        return text
    return synthesize_notes_answer(query, context_blocks, mode=mode)


def polish_grounded_answer(answer: str | None, *, mode: str = "symptom") -> str:
    """Light cleanup that keeps citations and mode-specific disclaimers intact."""
    text = (answer or "").strip()
    if not text:
        return text
    # Collapse accidental triple blank lines from some model outputs.
    text = re.sub(r"\n{3,}", "\n\n", text)
    if mode == "symptom" and "not a diagnosis" not in text.lower():
        text = text.rstrip() + "\nNot a diagnosis — see a clinician if needed."
    if mode != "symptom" and "not a diagnosis" not in text.lower():
        text = text.rstrip() + "\nNot a diagnosis — this is general information from reference notes."
    return text
