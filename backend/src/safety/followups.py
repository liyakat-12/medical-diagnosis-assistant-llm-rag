"""
Symptom-aware clarifying questions for weak-match / incomplete descriptions.

Kept deterministic and small so emergency guidance is never delayed by an LLM.
"""
from __future__ import annotations

import re

from src.retrieval.query_normalize import parse_body_map

_CHEST = re.compile(r"\b(chest|heart|breath|breathless|short(ness)? of breath|palpitation|heartbeat)\b", re.I)
_HEAD = re.compile(r"\b(head|headache|migraine|dizzy|dizziness|light.?sensitiv)\b", re.I)
_ABDOMEN = re.compile(r"\b(abdomen|abdominal|stomach|belly|nausea|vomit|acidity|reflux|heartburn)\b", re.I)
_FEVERISH = re.compile(r"\b(fever|chills|infection|flu)\b", re.I)
_JOINT = re.compile(r"\b(knee|ankle|hip|shoulder|wrist|joint|stairs|swelling)\b", re.I)
_THROAT = re.compile(r"\b(throat|cough|cold|sneeze|congestion|runny nose)\b", re.I)
_DIARRHOEA = re.compile(r"\b(diarrh(?:oea|ea)|loose stool|dehydrat)\b", re.I)


def clarifying_questions(query: str, *, limit: int = 2) -> list[str]:
    free, locations, symptoms = parse_body_map(query)
    blob = " ".join([free, *locations, *symptoms, query or ""]).lower()
    questions: list[str] = []

    if _CHEST.search(blob):
        questions.extend(
            [
                "Is the chest pain or tightness new, severe, or getting worse?",
                "Do you also have breathlessness, a rapid heartbeat, sweating, fainting, nausea, or pain spreading to an arm, jaw, back, or shoulder?",
            ]
        )
    elif _HEAD.search(blob):
        questions.extend(
            [
                "How long has the headache lasted, and how severe is it?",
                "Is there neck stiffness, vision change, confusion, vomiting, or the worst headache of your life?",
            ]
        )
    elif _DIARRHOEA.search(blob):
        questions.extend(
            [
                "How many loose stools have you had, and for how long?",
                "Are you dizzy when standing, unable to keep fluids down, or seeing blood in the stool?",
            ]
        )
    elif _ABDOMEN.search(blob):
        questions.extend(
            [
                "Where exactly is the abdominal discomfort, and how long has it lasted?",
                "Is there fever, vomiting, rigidity, black stools, or pain that is rapidly worsening?",
            ]
        )
    elif _THROAT.search(blob):
        questions.extend(
            [
                "How many days have the cold, cough, or sore throat symptoms lasted?",
                "Is there high fever, trouble breathing, or difficulty swallowing fluids?",
            ]
        )
    elif _JOINT.search(blob):
        questions.extend(
            [
                "Did this start after an injury, twist, or sudden load?",
                "Is the area swollen, locking, giving way, red and hot, or paired with fever?",
            ]
        )
    elif _FEVERISH.search(blob):
        questions.extend(
            [
                "How high is the fever and how long has it lasted?",
                "Are there chills, confusion, stiff neck, or a rash?",
            ]
        )
    else:
        questions.extend(
            [
                "How long has this lasted, and how severe is it now?",
                "What associated symptoms are you noticing (onset, location, anything that makes it worse)?",
            ]
        )

    # Deduplicate while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for q in questions:
        if q not in seen:
            seen.add(q)
            out.append(q)
        if len(out) >= limit:
            break
    return out


def weak_match_answer(query: str) -> str:
    qs = clarifying_questions(query, limit=2)
    lines = [
        "I don't have a close enough match in the notes to suggest conditions yet.",
        *qs,
        "Not a diagnosis — see a clinician if needed.",
    ]
    return "\n".join(lines)
