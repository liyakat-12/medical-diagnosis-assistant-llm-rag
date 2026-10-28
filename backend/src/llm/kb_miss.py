"""Structured LLM fallback when local notes are a weak or empty match.

Used only when a real provider (Groq / OpenAI / Ollama) is configured.
Mock mode stays on clarifying questions so tests do not invent conditions.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from src import config
from src.llm.generator import _call_llm, _history_block
from src.llm.markdown_format import (
    RARE_DISEASE_US_DEFINITION,
    UNNAMED_RARE_FOLLOWUP,
    correct_rare_disease_prevalence,
    ensure_unnamed_rare_followup,
    normalize_markdown_tables,
)
from src.safety.guardrails import check_prescription_request
from src.safety.triage import TRIAGE_GUIDANCE, TRIAGE_LABELS, TriageResult

_MATCH_LIMIT = 4

_JSON_BLOCK = re.compile(r"\{.*\}", re.S)
_URL_RE = re.compile(r"https?://\S+", re.I)
_FAKE_SOURCE_RE = re.compile(r"\(Source:\s*[^)]+\)", re.I)
_SELF_SYMPTOM = re.compile(
    r"\b(i have|i've got|i am having|i'm having|my \w+ (hurts|aches?|pain)|"
    r"pain|cough|fever|rash|vomit|nause|dizz)\b",
    re.I,
)
_BROAD_UNNAMED = re.compile(
    r"\b((a|an) rare disease|rare diseases?( in general)?|"
    r"what causes (a |an )?(rare )?disease|"
    r"disease that is not in|not in (my |the )?(knowledge base|kb|notes|database))\b",
    re.I,
)
_NAMED_CONDITION = re.compile(
    r"\b(?:called|named)\s+[\w'-]+|"
    r"\b(?!a\b|an\b|the\b|this\b|that\b|some\b|any\b|rare\b|my\b|your\b)"
    r"[\w'-]+\s+disease\b",
    re.I,
)
_COMMON_NOT_RARE = {
    "common cold",
    "cold",
    "flu",
    "influenza",
    "covid",
    "covid-19",
    "asthma",
    "type 2 diabetes",
    "diabetes",
    "hypertension",
    "high blood pressure",
    "migraine",
    "tension headache",
    "allergic rhinitis",
    "hay fever",
    "gerd",
    "acid reflux",
}
_DISCLAIMER_LINE = "This is general information, not a diagnosis."
ALLOWED_TRIAGE = {"self_care", "consult_doctor"}
GENERAL_AI_SOURCE_TITLE = "General medical knowledge was used and was not verified against the knowledge base"
GENERAL_AI_SOURCE_NOTE = "not verified against the MediAssist knowledge base"
NO_KB_SOURCE_TITLE = "No matching sources were found in the MediAssist knowledge base"
LOOKUP_FAILED_MESSAGE = (
    "I could not finish this medical lookup right now. Please try again in a moment, "
    "or see a clinician if you are worried. Not a diagnosis — see a clinician if needed."
)
MISSING_KEY_MESSAGE = (
    "This medical lookup is not available on this server, and no close match "
    "was found in the local notes. Please try again later or see a clinician if you "
    "are worried. Not a diagnosis — see a clinician if needed."
)

KB_MISS_SYSTEM = """You are MediAssist, a careful medical information assistant. \
The local knowledge notes did not contain a close match. Use general medical \
knowledge only. Return ONLY valid JSON, no extra text.

JSON shape:
{
  "answer": "markdown allowed; short bullets preferred over tables; may-be language; no drug names or doses",
  "triage": "self_care" or "consult_doctor",
  "recommendations": ["next step 1", "next step 2"],
  "matches": [
    {"condition": "Common name", "weight": 3}
  ]
}

Rules:
- Never invent a citation, document name, paper title, or URL.
- Never use triage "emergency". Never give a dose, tablet, or prescription.
- Do not claim this is a diagnosis, a retrieved note, or that you examined the user.
- Do not answer travel, coding, weather, shopping, or other non-medical requests.
- If the user did not name a specific disease and is asking a broad question:
  set matches to [] ; explain general disease mechanisms in 4-8 short bullet lines; \
  do not list named diseases as "rare" examples.
  If the topic is rare disease, say that in the United States a rare disease generally \
  affects fewer than 200,000 people. Do not claim a worldwide threshold of five million people.
  End the answer with exactly: Which specific rare disease would you like to know more about?
- If the user named a specific disease or described personal symptoms:
  give 2 to 4 possible related condition names. Weights are relative fit, not diagnosis chance.
- Do not call common conditions rare (for example influenza, common cold, type 2 diabetes, asthma).
- Prefer bullet lists. If you use a table, it must be valid GitHub-flavored markdown: a blank line before the table, a header row, a separator row of dashes, then data rows, each on its own line.
"""

KB_MISS_DISCLAIMER = "This is general information, not a diagnosis."


@dataclass
class KbMissBundle:
    answer: str
    triage: TriageResult | None
    recommendations: list[str]
    citations: list[dict]
    possible_conditions: list[dict]
    disclaimer: str = KB_MISS_DISCLAIMER
    failed: bool = False
    failure_kind: str | None = None


def medical_llm_status() -> str:
    if not config.LLM_KB_FALLBACK:
        return "disabled"
    wanted = (config.LLM_PROVIDER or "").strip().lower()
    effective = config.resolve_llm_provider()
    if wanted in {"groq", "openai"} and effective == "mock":
        return "missing_key"
    if effective == "mock":
        return "mock"
    return "ready"


def can_use_llm_kb_fallback() -> bool:
    return medical_llm_status() in {"ready", "missing_key"}


def is_broad_unnamed_medical_query(text: str) -> bool:
    raw = text or ""
    if _SELF_SYMPTOM.search(raw):
        return False
    if _NAMED_CONDITION.search(raw):
        return False
    return bool(_BROAD_UNNAMED.search(raw))


def general_ai_citation() -> dict:
    return {
        "title": GENERAL_AI_SOURCE_TITLE,
        "source": "",
        "url": "",
        "condition": "",
        "relevance_score": 0.0,
    }


def no_kb_citation() -> dict:
    return {
        "title": NO_KB_SOURCE_TITLE,
        "source": "",
        "url": "",
        "condition": "",
        "relevance_score": 0.0,
    }


def unnamed_general_answer(query: str = "") -> str:
    rare = bool(re.search(r"\brare\b", query or "", re.I))
    body = (
        "Diseases can arise in several broad ways:\n"
        "- Genetic changes may affect a protein the body needs\n"
        "- Infections can injure tissues\n"
        "- Immune activity may miss the target or over-react\n"
        "- Environment, injury, and chance can also play a part\n"
    )
    if rare:
        body = f"{RARE_DISEASE_US_DEFINITION}\n\n{body}"
        body = ensure_unnamed_rare_followup(body)
    else:
        body = f"{body}\nPlease name the specific disease if you want a closer explanation."
    return (
        "I did not find a close match in the local notes, so this uses general "
        f"medical knowledge.\n\n{body}\n\n{_DISCLAIMER_LINE}"
    )


def _unnamed_info_bundle(query: str) -> KbMissBundle:
    rare = bool(re.search(r"\brare\b", query or "", re.I))
    recs = [
        "This uses general AI medical knowledge, not retrieved MediAssist notes.",
        UNNAMED_RARE_FOLLOWUP if rare else "Name the specific disease if you want a closer explanation.",
    ]
    return KbMissBundle(
        answer=unnamed_general_answer(query),
        triage=None,
        recommendations=recs,
        citations=[no_kb_citation(), general_ai_citation()],
        possible_conditions=[],
    )


def _failure_bundle(kind: str, message: str) -> KbMissBundle:
    return KbMissBundle(
        answer=message,
        triage=None,
        recommendations=["Try sending the same health question again, or see a clinician if you are worried."],
        citations=[no_kb_citation()],
        possible_conditions=[],
        failed=True,
        failure_kind=kind,
    )


def _extract_json(text: str) -> dict | None:
    raw = (text or "").strip()
    if not raw:
        return None
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.I)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        match = _JSON_BLOCK.search(raw)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None


def _pretty(value: str) -> str:
    text = re.sub(r"\s+", " ", (value or "").strip())
    if not text:
        return ""
    if "_" in text and " " not in text:
        text = text.replace("_", " ")
    return text[:80]


def _strip_invented_sources(text: str) -> str:
    cleaned = _FAKE_SOURCE_RE.sub("", text or "")
    cleaned = _URL_RE.sub("", cleaned)
    return cleaned


def _clean_text(value: str, *, flatten: bool = True, limit: int = 320) -> str:
    text = _strip_invented_sources(value or "")
    if flatten:
        text = re.sub(r"\s+", " ", text).strip()
    else:
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text or check_prescription_request(text).triggered:
        return ""
    if len(text) > limit:
        cut = text[: limit - 1]
        text = (cut.rsplit(" ", 1)[0] if " " in cut else cut) + "…"
    return text


def parse_kb_miss_payload(raw: str, query: str) -> KbMissBundle | None:
    data = _extract_json(raw)
    if not data:
        return None

    unnamed = is_broad_unnamed_medical_query(query)
    matches: list[dict] = []
    seen: set[str] = set()
    if not unnamed:
        for item in data.get("matches") or []:
            if not isinstance(item, dict):
                continue
            name = _pretty(str(item.get("condition") or item.get("title") or ""))
            key = name.lower()
            if not name or key in seen:
                continue
            if "rare" in (query or "").lower() and key in _COMMON_NOT_RARE:
                continue
            seen.add(key)
            try:
                weight = float(item.get("weight") or item.get("relevance_score") or 1.0)
            except (TypeError, ValueError):
                weight = 1.0
            matches.append(
                {
                    "condition": name,
                    "title": name,
                    "source": GENERAL_AI_SOURCE_NOTE,
                    "url": "",
                    "relevance_score": max(0.1, weight),
                }
            )
            if len(matches) >= _MATCH_LIMIT:
                break
    if not unnamed and len(matches) < 2:
        return None

    if matches:
        from src.pipeline.rag_pipeline import match_percents

        percents = match_percents([float(row["relevance_score"]) for row in matches])
        for row, percent in zip(matches, percents):
            row["match_percent"] = percent

    answer = _clean_text(str(data.get("answer") or ""), flatten=False, limit=1800)
    if not answer and matches:
        names = ", ".join(row["condition"] for row in matches[:3])
        answer = (
            f"The local notes did not have a close match. From general knowledge, "
            f"this may relate to {names}."
        )
    if not answer:
        return None
    answer = normalize_markdown_tables(answer)
    rare_topic = bool(re.search(r"\brare\b", query or "", re.I))
    if unnamed or rare_topic:
        answer = correct_rare_disease_prevalence(answer)
        if unnamed and rare_topic and "200,000" not in answer:
            answer = f"{RARE_DISEASE_US_DEFINITION}\n\n{answer}".strip()
    if "i did not find" not in answer.lower():
        answer = (
            "I did not find a close match in the local notes, so this uses general "
            f"medical knowledge.\n\n{answer}"
        )
    if unnamed and rare_topic:
        answer = ensure_unnamed_rare_followup(answer)
    answer = re.sub(
        r"(?is)\s*this explanation is general medical information[^.!\n]*[.!]?",
        "",
        answer,
    )
    answer = re.sub(
        rf"(?im)^\s*(?:not a diagnosis[^\n]*|{re.escape(NO_KB_SOURCE_TITLE)}|{re.escape(GENERAL_AI_SOURCE_TITLE)})\s*$",
        "",
        answer,
    )
    answer = re.sub(r"\n{3,}", "\n\n", answer).strip()
    if _DISCLAIMER_LINE.lower() not in answer.lower():
        answer = f"{answer}\n\n{_DISCLAIMER_LINE}"

    recs: list[str] = []
    for item in data.get("recommendations") or []:
        text = _clean_text(str(item))
        if text and text not in recs:
            recs.append(text)
        if len(recs) >= 3:
            break
    if not recs:
        recs = [
            "See a doctor if this lasts, worsens, or you are unsure what it is.",
            "Seek urgent care for sudden severe symptoms, collapse, or trouble breathing.",
        ]
    if unnamed:
        recs = [
            (
                "Which specific rare disease would you like to know more about?"
                if rare_topic
                else "Name the specific disease if you want a closer explanation."
            ),
            *recs,
        ]
    recs = [
        "This uses general AI medical knowledge, not retrieved MediAssist notes.",
        *recs,
    ][:4]

    triage = None
    if not unnamed:
        level = str(data.get("triage") or "consult_doctor").strip().lower()
        if level not in ALLOWED_TRIAGE:
            level = "consult_doctor"
        triage = TriageResult(
            level=level,
            label=TRIAGE_LABELS[level],
            guidance=TRIAGE_GUIDANCE[level],
            reason=(
                "Local notes had no close match; urgency uses MediAssist general medical knowledge "
                f"for: {query[:120]}"
            ),
            matched_emergency_terms=[],
        )
    citations = [no_kb_citation(), general_ai_citation()]
    return KbMissBundle(
        answer=answer,
        triage=triage,
        recommendations=recs,
        citations=citations,
        possible_conditions=matches,
    )


def generate_kb_miss_bundle(query: str, history: list[dict] | None = None) -> KbMissBundle | None:
    status = medical_llm_status()
    if status in {"mock", "disabled"}:
        return None
    if status == "missing_key":
        return _failure_bundle("missing_key", MISSING_KEY_MESSAGE)
    prefix = _history_block(history)
    unnamed_note = ""
    if is_broad_unnamed_medical_query(query):
        unnamed_note = (
            "The user did not name a specific disease. Keep matches empty. "
            "Give a concise general explanation of how diseases can arise and use a short bullet list. "
            "If this is about rare disease, use the U.S. definition of fewer than 200,000 affected people "
            "and do not mention a worldwide five-million-person threshold. "
            "End with: Which specific rare disease would you like to know more about? "
            "Do not invent rare-disease examples, papers, URLs, or sources.\n\n"
        )
    user_prompt = (
        f"{prefix}"
        f"{unnamed_note}"
        f"User question: {query}\n\n"
        "The local knowledge base had no close match. "
        "Return the JSON object described in the system prompt."
    )
    try:
        raw = _call_llm(KB_MISS_SYSTEM, user_prompt, grounded=False, max_tokens=700)
    except Exception as exc:
        text = str(exc).lower()
        kind = "rate_limit" if "429" in text or "rate limit" in text else "error"
        return _failure_bundle(kind, LOOKUP_FAILED_MESSAGE)
    parsed = parse_kb_miss_payload(raw, query)
    if parsed is None or not (parsed.answer or "").strip():
        if is_broad_unnamed_medical_query(query):
            return _unnamed_info_bundle(query)
        return _failure_bundle("invalid", LOOKUP_FAILED_MESSAGE)
    return parsed
