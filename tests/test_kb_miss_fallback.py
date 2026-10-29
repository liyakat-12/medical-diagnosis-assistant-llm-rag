from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from src.llm.kb_miss import parse_kb_miss_payload
from src.pipeline.rag_pipeline import run_pipeline
from src.retrieval.retriever import Evidence


WEAK_HITS = [
    Evidence(
        text="unrelated furniture notes about oak tables",
        title="Table Care",
        source="Sample",
        url="",
        condition="table",
        triage_level="self_care",
        relevance_score=0.01,
        doc_id="table",
        vector_score=0.1,
    )
]

SAMPLE_JSON = json.dumps(
    {
        "answer": "This may be a common cold or allergic rhinitis after dust exposure.",
        "triage": "self_care",
        "recommendations": [
            "Rest and drink fluids.",
            "See a doctor if breathing becomes hard or fever lasts.",
        ],
        "matches": [
            {"condition": "Common cold", "weight": 4, "source": "NHS"},
            {"condition": "Allergic rhinitis", "weight": 2, "source": "MedlinePlus"},
            {"condition": "Sinus irritation", "weight": 1, "source": "CDC"},
        ],
    }
)


def test_parse_kb_miss_payload_builds_same_cards():
    bundle = parse_kb_miss_payload(SAMPLE_JSON, "itchy nose after dust")
    assert bundle is not None
    assert bundle.triage.level == "self_care"
    assert len(bundle.possible_conditions) == 3
    assert all("match_percent" not in row for row in bundle.possible_conditions)
    assert any("knowledge base" in (row.get("title") or "").lower() for row in bundle.citations)
    assert any("not verified" in f"{row.get('title') or ''} {row.get('source') or ''}".lower() for row in bundle.citations)
    assert all(not (row.get("url") or "").startswith("http") for row in bundle.citations)
    assert "not a diagnosis" in bundle.answer.lower()
    assert bundle.triage.level != "emergency"


def test_parse_rejects_emergency_triage_from_model():
    raw = json.dumps(
        {
            "answer": "This may be a sprain.",
            "triage": "emergency",
            "recommendations": ["Rest the joint.", "See a doctor if it swells more."],
            "matches": [
                {"condition": "Ankle sprain", "weight": 3, "source": "NHS"},
                {"condition": "Soft tissue strain", "weight": 2, "source": "MedlinePlus"},
            ],
        }
    )
    bundle = parse_kb_miss_payload(raw, "twisted my ankle yesterday")
    assert bundle is not None
    assert bundle.triage.level == "consult_doctor"


def test_mock_provider_still_asks_clarifying_questions(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: (WEAK_HITS, WEAK_HITS))
    monkeypatch.setattr(rp, "can_use_llm_kb_fallback", lambda: False)
    result = run_pipeline("I have a mild cough that is hard to pin down further")
    assert result.possible_conditions == []
    assert result.citations == []
    assert result.evidence_origin == "none"
    assert "close enough match" in result.answer.lower() or "how long" in result.answer.lower()


def test_groq_fallback_fills_structured_cards_when_notes_miss(monkeypatch):
    from src.llm import kb_miss as kb
    from src.pipeline import rag_pipeline as rp

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: (WEAK_HITS, WEAK_HITS))
    monkeypatch.setattr(rp, "can_use_llm_kb_fallback", lambda: True)
    monkeypatch.setattr(kb, "can_use_llm_kb_fallback", lambda: True)
    monkeypatch.setattr(kb, "medical_llm_status", lambda: "ready")
    monkeypatch.setattr(kb, "_call_llm", lambda *_a, **_k: SAMPLE_JSON)
    monkeypatch.setattr(rp, "generate_kb_miss_bundle", kb.generate_kb_miss_bundle)

    result = run_pipeline("itchy nose and sneezing after dusting")
    assert result.evidence_origin == "llm"
    assert result.triage is not None
    assert result.triage.level == "self_care"
    assert len(result.possible_conditions) >= 2
    assert result.citations
    assert "local notes" in result.answer.lower()
    assert result.recommendations


def test_emergency_still_skips_llm_match_cards(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    def boom(*_a, **_k):
        raise AssertionError("emergency weak path must not call Groq fallback")

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: ([], []))
    monkeypatch.setattr(rp, "can_use_llm_kb_fallback", lambda: True)
    monkeypatch.setattr(rp, "generate_kb_miss_bundle", boom)
    result = run_pipeline("crushing chest pain spreading to my jaw with sweating")
    assert result.triage is not None
    assert result.triage.level == "emergency"
    assert result.possible_conditions == []
    assert result.citations == []
    assert "112" in (result.answer + " " + (result.triage.guidance or ""))
    assert "call 112" not in (result.answer or "").lower()
