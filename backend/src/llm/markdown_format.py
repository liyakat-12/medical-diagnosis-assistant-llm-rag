"""Normalize assistant markdown so GFM tables render, and correct rare-disease wording."""
from __future__ import annotations

import re

RARE_DISEASE_US_DEFINITION = (
    "In the United States, a rare disease is generally a condition that affects fewer than "
    "200,000 people. Other regions use different cutoffs, and there is no single worldwide "
    "person-count threshold."
)
UNNAMED_RARE_FOLLOWUP = "Which specific rare disease would you like to know more about?"

_FIVE_MILLION = re.compile(r"five million|5\s*million|5,000,000", re.I)
_SEP_CELL = re.compile(r"^:?-{3,}:?$")
_WEAK_FOLLOWUP = re.compile(
    r"(?im)^(?:please )?(?:name|tell me) the specific disease[^\n]*$",
)


def _cells(row: str) -> list[str]:
    return [part.strip() for part in row.strip().strip("|").split("|")]


def _is_separator(row: str) -> bool:
    cells = [cell.replace(" ", "") for cell in _cells(row)]
    return bool(cells) and all(_SEP_CELL.fullmatch(cell or "") for cell in cells)


def _separator_row(count: int) -> str:
    return "| " + " | ".join("---" for _ in range(max(count, 1))) + " |"


def _row_to_bullet(row: str) -> str:
    cells = [cell for cell in _cells(row) if cell and not _SEP_CELL.fullmatch(cell.replace(" ", ""))]
    if len(cells) >= 2:
        return f"- **{cells[0]}**: {' — '.join(cells[1:])}"
    if cells:
        return f"- {cells[0]}"
    return ""


def _split_concatenated_rows(line: str) -> list[str]:
    text = line.strip()
    if text.count("|") < 4:
        return [text] if "|" in text else []
    parts = [part.strip() for part in re.split(r"(?<=\|)\s+(?=\|)", text) if part.strip()]
    if len(parts) >= 2:
        return parts
    return [text]


def _format_table(rows: list[str]) -> str:
    rows = [row.strip() for row in rows if row.strip()]
    if not rows:
        return ""
    columns = len(_cells(rows[0]))
    if columns < 2 or len(rows) == 1:
        bullets = [item for item in (_row_to_bullet(row) for row in rows) if item]
        return "\n".join(bullets)
    header = rows[0]
    body = rows[1:]
    formatted = [header]
    if body and _is_separator(body[0]):
        formatted.append(_separator_row(columns))
        body = body[1:]
    else:
        formatted.append(_separator_row(columns))
    if not body:
        bullets = [item for item in (_row_to_bullet(row) for row in rows) if item]
        return "\n".join(bullets)
    formatted.extend(body)
    return "\n".join(formatted)


def normalize_markdown_tables(text: str) -> str:
    """Turn concatenated or incomplete pipe tables into GFM, or into a bullet list."""
    if not text or "|" not in text:
        return text or ""
    cleaned = text.replace("\r\n", "\n")
    if "\\n" in cleaned and cleaned.count("\n") < 2:
        cleaned = cleaned.replace("\\n", "\n")
    lines = cleaned.split("\n")
    rebuilt: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if "|" not in line:
            rebuilt.append(line)
            index += 1
            continue
        prefix = ""
        table_line = line
        pipe_at = line.find("|")
        if pipe_at > 0:
            prefix = line[:pipe_at].rstrip()
            table_line = line[pipe_at:]
        if prefix:
            rebuilt.append(prefix)
        rows = _split_concatenated_rows(table_line)
        index += 1
        while index < len(lines) and "|" in lines[index]:
            rows.extend(_split_concatenated_rows(lines[index]))
            index += 1
        table = _format_table(rows)
        if rebuilt and rebuilt[-1].strip():
            rebuilt.append("")
        rebuilt.append(table)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(rebuilt)).strip()


def correct_rare_disease_prevalence(text: str) -> str:
    """Replace unsupported global five-million thresholds with the U.S. definition."""
    if not text:
        return text
    lines: list[str] = []
    removed_claim = False
    for line in text.split("\n"):
        if not _FIVE_MILLION.search(line):
            lines.append(line)
            continue
        removed_claim = True
        if line.strip().startswith("|"):
            lines.append(
                _FIVE_MILLION.sub("fewer than 200,000 people in the United States", line)
            )
            continue
        kept = [
            piece.strip()
            for piece in re.split(r"(?<=[.!?])\s+", line)
            if piece.strip() and not _FIVE_MILLION.search(piece)
        ]
        if kept:
            lines.append(" ".join(kept))
    result = "\n".join(lines).strip()
    if removed_claim and "200,000" not in result.replace(" ", ""):
        result = f"{RARE_DISEASE_US_DEFINITION}\n\n{result}".strip()
    return result


def ensure_unnamed_rare_followup(text: str) -> str:
    answer = _WEAK_FOLLOWUP.sub("", text or "").strip()
    if UNNAMED_RARE_FOLLOWUP.lower() in answer.lower():
        return answer
    return f"{answer}\n\n{UNNAMED_RARE_FOLLOWUP}"


def polish_assistant_markdown(text: str, query: str = "", *, unnamed_rare: bool = False) -> str:
    polished = normalize_markdown_tables(text)
    if unnamed_rare or re.search(r"rare disease", f"{query} {text}", re.I):
        polished = correct_rare_disease_prevalence(polished)
    if unnamed_rare:
        if "200,000" not in polished.replace(" ", ""):
            polished = f"{RARE_DISEASE_US_DEFINITION}\n\n{polished}".strip()
        polished = ensure_unnamed_rare_followup(polished)
    return polished
