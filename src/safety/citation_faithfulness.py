"""
Citation faithfulness audit.

Runs AFTER the LLM answer is generated. For every claim-like sentence it
checks:

  1. Does the sentence carry a (Source: ...) citation?
  2. Does that cited title actually appear in the retrieved evidence?

Sentences with no citation, or a citation that was never retrieved, are
flagged. Disclaimer / preamble lines are ignored so they do not inflate
or deflate the score.

This is the inspectable anti-hallucination layer: RAG retrieves documents,
the model writes an answer, and this audit verifies the answer did not
invent unsupported claims.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

CITATION_RE = re.compile(r"\(Source:\s*([^)]+)\)", re.IGNORECASE)
NUMBERED_PREFIX_RE = re.compile(r"^\d+\.\s*")
CLAIM_HINT_RE = re.compile(
    r"\b(could be|may be|might be|is (a )?sign|suggests?|"
    r"possible (cause|condition|explanation)|consistent with|"
    r"indicat\w+|likely|associated with|related to)\b",
    re.IGNORECASE,
)
NON_CLAIM_RE = re.compile(
    r"not a diagnosis|consult a (qualified )?(healthcare|doctor|clinician)|"
    r"possible explanations include|based on the retrieved|"
    r"i could not find enough|please rephrase|"
    r"without retrieval|no documents retrieved",
    re.IGNORECASE,
)


@dataclass
class ClaimAudit:
    text: str
    cited_source: str | None
    status: str  # supported | unsupported | fabricated_citation | not_a_claim
    matched_title: str | None = None


@dataclass
class FaithfulnessAudit:
    coverage: float
    claim_count: int
    supported_count: int
    unsupported_count: int
    fabricated_count: int
    verdict: str  # pass | partial | fail | n_a
    summary: str
    claims: list[ClaimAudit] = field(default_factory=list)

    def to_dict(self) -> dict:
        data = asdict(self)
        return data


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _split_units(answer: str) -> list[str]:
    units: list[str] = []
    for raw_line in (answer or "").splitlines():
        line = NUMBERED_PREFIX_RE.sub("", raw_line.strip())
        if not line:
            continue
        for part in re.split(r"(?<=[.!?])\s+", line):
            part = part.strip()
            if part:
                units.append(part)
    if not units and (answer or "").strip():
        units.append(answer.strip())
    return units


def _extract_citation(sentence: str) -> str | None:
    match = CITATION_RE.search(sentence)
    if not match:
        return None
    return match.group(1).strip()


def _is_claim(sentence: str, cited_source: str | None) -> bool:
    if NON_CLAIM_RE.search(sentence) and not cited_source:
        return False
    if cited_source:
        return True
    if CLAIM_HINT_RE.search(sentence):
        return True
    return False


def _match_retrieved(cited: str, retrieved_titles: list[str]) -> str | None:
    cited_norm = _normalize(cited)
    if not cited_norm:
        return None
    for title in retrieved_titles:
        title_norm = _normalize(title)
        if not title_norm:
            continue
        if cited_norm == title_norm:
            return title
        if cited_norm in title_norm or title_norm in cited_norm:
            return title
    return None


def _retrieved_titles(retrieved: list) -> list[str]:
    titles: list[str] = []
    for item in retrieved:
        if isinstance(item, dict):
            for key in ("title", "condition", "source"):
                value = (item.get(key) or "").strip()
                if value and value not in titles:
                    titles.append(value)
        else:
            for attr in ("title", "condition", "source"):
                value = str(getattr(item, attr, "") or "").strip()
                if value and value not in titles:
                    titles.append(value)
    return titles


def _verdict(supported: int, unsupported: int, fabricated: int, claims: int) -> tuple[str, str]:
    if claims == 0:
        return "n_a", "No medical claims to audit in this answer."
    if unsupported == 0 and fabricated == 0:
        return (
            "pass",
            f"All {supported} claim(s) are cited and match retrieved documents.",
        )
    problems = unsupported + fabricated
    if supported == 0:
        return (
            "fail",
            f"None of {claims} claim(s) could be tied to a retrieved source.",
        )
    return (
        "partial",
        f"{supported} supported, {problems} not faithful "
        f"({unsupported} uncited, {fabricated} citation not in retrieval).",
    )


def audit_citation_faithfulness(answer: str, retrieved: list) -> FaithfulnessAudit:
    """Score whether every claim in `answer` is backed by `retrieved` evidence."""
    allowed_titles = _retrieved_titles(retrieved)
    claims: list[ClaimAudit] = []

    for sentence in _split_units(answer):
        cited = _extract_citation(sentence)
        if not _is_claim(sentence, cited):
            claims.append(
                ClaimAudit(
                    text=sentence,
                    cited_source=cited,
                    status="not_a_claim",
                )
            )
            continue

        if not cited:
            claims.append(
                ClaimAudit(text=sentence, cited_source=None, status="unsupported")
            )
            continue

        matched = _match_retrieved(cited, allowed_titles)
        if matched:
            claims.append(
                ClaimAudit(
                    text=sentence,
                    cited_source=cited,
                    status="supported",
                    matched_title=matched,
                )
            )
        else:
            claims.append(
                ClaimAudit(
                    text=sentence,
                    cited_source=cited,
                    status="fabricated_citation",
                )
            )

    medical = [c for c in claims if c.status != "not_a_claim"]
    supported = sum(1 for c in medical if c.status == "supported")
    unsupported = sum(1 for c in medical if c.status == "unsupported")
    fabricated = sum(1 for c in medical if c.status == "fabricated_citation")
    claim_count = len(medical)
    coverage = (supported / claim_count) if claim_count else 0.0
    verdict, summary = _verdict(supported, unsupported, fabricated, claim_count)

    return FaithfulnessAudit(
        coverage=round(coverage, 4),
        claim_count=claim_count,
        supported_count=supported,
        unsupported_count=unsupported,
        fabricated_count=fabricated,
        verdict=verdict,
        summary=summary,
        claims=claims,
    )
