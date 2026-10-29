"""Regression: document titles must not be presented as medical explanations."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from src.ai.providers.mock import MockProvider
from src.llm.generator import _build_user_prompt, generate_notes_fallback_answer
from src.llm.notes_answer import (
    clinical_ideas_from_notes,
    is_title_dump_answer,
    rewrite_if_title_dump,
    synthesize_notes_answer,
)
from src.pipeline.rag_pipeline import (
    build_possible_conditions,
    citations_from_evidence,
    run_pipeline,
)
from src.retrieval.retriever import Evidence


def _blocks_from_titles(titles: list[str], bodies: list[str]) -> list[str]:
    return [
        f"[{i}] Source: {title} (NHS - Knee pain)\n{body}"
        for i, (title, body) in enumerate(zip(titles, bodies), start=1)
    ]


KNEE_TITLES = [
    "Knee Pain When Walking",
    "Knee Pain When Climbing Stairs",
    "Pain Behind the Knee",
    "Muscle Cramp",
]
KNEE_BODIES = [
    "Common possibilities include early osteoarthritis, a simple strain, or irritation of the kneecap.",
    "Pain under the kneecap often relates to how the kneecap tracks, weak thigh muscles, or early cartilage wear.",
    "A tight ache behind the knee can be a strained tendon or a Baker's cyst.",
    "A muscle cramp is a sudden painful tightening of a muscle, often in the calf after exercise.",
]


def test_is_title_dump_detects_mock_style_list():
    dump = (
        "Possible explanations:\n"
        "1. Knee Pain When Walking may fit these symptoms (Source: Knee Pain When Walking).\n"
        "2. Knee Pain When Climbing Stairs may fit these symptoms (Source: Knee Pain When Climbing Stairs).\n"
        "Not a diagnosis — see a clinician if needed."
    )
    assert is_title_dump_answer(dump)
    assert not is_title_dump_answer(
        "For knee pain, notes mention early osteoarthritis (Source: Knee Pain When Walking).\n"
        "Not a diagnosis — see a clinician if needed."
    )


def test_mock_provider_does_not_list_document_titles_as_diagnoses():
    blocks = _blocks_from_titles(KNEE_TITLES[:3], KNEE_BODIES[:3])
    prompt = _build_user_prompt("knee pain", blocks, mode="symptom")
    answer = MockProvider().generate(
        "You are a careful medical information assistant.",
        prompt,
        grounded=True,
    )
    lowered = answer.lower()
    assert "may fit these symptoms" not in lowered
    assert "osteoarthritis" in lowered or "strain" in lowered or "baker" in lowered
    assert not is_title_dump_answer(answer)


def test_synthesize_rewrites_title_dump():
    blocks = _blocks_from_titles(KNEE_TITLES[:3], KNEE_BODIES[:3])
    dump = (
        "Possible explanations:\n"
        "1. Knee Pain When Walking may fit these symptoms (Source: Knee Pain When Walking).\n"
        "2. Knee Pain When Climbing Stairs may fit these symptoms (Source: Knee Pain When Climbing Stairs).\n"
    )
    fixed = rewrite_if_title_dump(dump, "knee pain", blocks)
    assert not is_title_dump_answer(fixed)
    assert "osteoarthritis" in fixed.lower() or "strain" in fixed.lower()


def test_clinical_ideas_ignore_titles_and_extract_body_terms():
    notes = [
        {"title": title, "source": "NHS", "text": body}
        for title, body in zip(KNEE_TITLES[:3], KNEE_BODIES[:3])
    ]
    ideas = clinical_ideas_from_notes(notes, limit=6)
    names = [item["condition"].lower() for item in ideas]
    assert names
    assert not any("when walking" in name or "climbing stairs" in name for name in names)
    assert any("osteoarthritis" in name or "strain" in name or "baker" in name for name in names)


def test_citations_keep_sibling_notes_sharing_url():
    evidence = [
        Evidence(
            text="a",
            title="Knee Pain When Walking",
            source="NHS",
            url="https://www.nhs.uk/conditions/knee-pain/",
            condition="Knee Pain",
            triage_level="self_care",
            relevance_score=0.9,
        ),
        Evidence(
            text="b",
            title="Knee Pain When Climbing Stairs",
            source="NHS",
            url="https://www.nhs.uk/conditions/knee-pain/",
            condition="Knee Pain",
            triage_level="self_care",
            relevance_score=0.8,
        ),
        Evidence(
            text="c",
            title="Muscle Cramp",
            source="Mayo",
            url="https://www.mayoclinic.org/diseases-conditions/muscle-cramp/symptoms-causes/syc-20350820",
            condition="Muscle Cramp",
            triage_level="self_care",
            relevance_score=0.5,
        ),
    ]
    citations = citations_from_evidence(evidence)
    titles = [item["title"] for item in citations]
    assert len(titles) == len(set(titles))
    assert len(citations) == 3
    assert "Knee Pain When Climbing Stairs" in titles


def test_possible_conditions_use_clinical_labels_not_titles():
    evidence = [
        Evidence(
            text=KNEE_BODIES[0],
            title=KNEE_TITLES[0],
            source="NHS",
            url="https://www.nhs.uk/conditions/knee-pain/",
            condition="Knee Pain",
            triage_level="self_care",
            relevance_score=0.9,
        ),
        Evidence(
            text=KNEE_BODIES[2],
            title=KNEE_TITLES[2],
            source="NHS",
            url="https://www.nhs.uk/conditions/knee-pain/",
            condition="Pain Behind Knee",
            triage_level="consult_doctor",
            relevance_score=0.85,
        ),
    ]
    citations = citations_from_evidence(evidence)
    rows = build_possible_conditions(citations, evidence=evidence, query="knee pain")
    labels = [row["condition"].lower() for row in rows]
    assert labels
    assert not any("when walking" in label for label in labels)
    assert not any(label == "knee pain" for label in labels)


def test_pipeline_knee_pain_answer_not_title_dump():
    result = run_pipeline("knee pain")
    assert result.refused is False
    assert not is_title_dump_answer(result.answer)
    assert "may fit these symptoms" not in (result.answer or "").lower()
    conditions = [str(item.get("condition") or "").lower() for item in (result.possible_conditions or [])]
    assert not any("when walking" in name or "climbing stairs" in name for name in conditions)
    assert "muscle cramp" not in conditions
    titles = [str(item.get("title") or "") for item in (result.citations or []) if item.get("title")]
    assert len(titles) == len(set(titles))
    assert len(titles) >= 2


def test_pipeline_knee_stairs_and_behind_knee():
    for query in ("knee pain when climbing stairs", "pain behind the knee"):
        result = run_pipeline(query)
        assert not is_title_dump_answer(result.answer)
        blob = (result.answer or "").lower()
        assert "may fit these symptoms" not in blob
        assert result.evidence_origin in {"knowledge_base", "mixed", "llm", "none"}


def test_pipeline_knee_fever_swelling_keeps_triage():
    result = run_pipeline("knee pain with fever and swelling")
    assert result.refused is False
    assert result.triage is not None
    assert result.triage.level in {"consult_doctor", "emergency"}
    assert not is_title_dump_answer(result.answer)


def test_finger_after_knee_does_not_reuse_knee_titles():
    history = [
        {"role": "user", "content": "knee pain"},
        {
            "role": "assistant",
            "content": "Knee notes mention strain.",
            "possible_conditions": [{"condition": "Early osteoarthritis", "title": "Knee Pain When Walking"}],
            "citations": [{"title": "Knee Pain When Walking", "url": "https://www.nhs.uk/conditions/knee-pain/"}],
        },
    ]
    result = run_pipeline("finger injury", chat_history=history)
    names = " ".join(
        str(item.get("condition") or item.get("title") or "")
        for item in (result.possible_conditions or []) + (result.citations or [])
    ).lower()
    assert "knee" not in names
    assert "osteoarthritis" not in names
    assert not is_title_dump_answer(result.answer)


def test_similar_title_documents_dedupe_and_clinical_answer():
    result = run_pipeline("knee pain when walking")
    titles = [str(item.get("title") or "") for item in (result.citations or [])]
    assert len(titles) == len(set(t.lower() for t in titles)) or len(
        {str(item.get("url") or "").lower() for item in (result.citations or []) if item.get("url")}
    ) == len([item for item in (result.citations or []) if item.get("url")])
    assert not is_title_dump_answer(result.answer)
    fallback = generate_notes_fallback_answer(
        "knee pain when walking",
        _blocks_from_titles(KNEE_TITLES[:2], KNEE_BODIES[:2]),
    )
    assert "osteoarthritis" in fallback.lower() or "strain" in fallback.lower()
    assert synthesize_notes_answer("knee pain", _blocks_from_titles(KNEE_TITLES[:1], KNEE_BODIES[:1]))
