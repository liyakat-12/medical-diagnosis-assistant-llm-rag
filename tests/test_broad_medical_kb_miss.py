from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from src.llm.kb_miss import (
    LOOKUP_FAILED_MESSAGE,
    MISSING_KEY_MESSAGE,
    is_broad_unnamed_medical_query,
    parse_kb_miss_payload,
)
from src.pipeline.rag_pipeline import run_pipeline
from src.retrieval.retriever import Evidence
from src.safety.guardrails import classify_intent
from src.safety.guardrails import check_prescription_request

UNNAMED = "What causes a rare disease that is not in my knowledge base?"
NAMED_ABSENT = "What causes Fabry disease?"

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

UNNAMED_JSON = json.dumps(
    {
        "answer": (
            "Diseases can arise in a few broad ways:\n"
            "- Genetic changes may alter a protein the body needs\n"
            "- Infections can damage tissues\n"
            "- Immune activity may miss or over-react\n\n"
            "Please name the specific disease if you want a closer explanation."
        ),
        "triage": "consult_doctor",
        "recommendations": ["Ask a clinician once the disease name is known."],
        "matches": [
            {"condition": "Influenza", "weight": 4, "url": "https://example.test/flu"},
            {"condition": "Common cold", "weight": 3},
        ],
    }
)

NAMED_JSON = json.dumps(
    {
        "answer": (
            "Fabry disease is often linked to a GLA gene change that can affect "
            "how the body handles a fat called globotriaosylceramide.\n\n"
            "- It may be inherited in an X-linked pattern\n"
            "- Symptoms can vary widely"
        ),
        "triage": "consult_doctor",
        "recommendations": ["See a clinician for testing and family advice."],
        "matches": [
            {"condition": "Fabry disease", "weight": 4, "url": "https://pubmed.example/123"},
            {"condition": "Lysosomal storage disorder", "weight": 2, "source": "https://nih.example"},
        ],
    }
)

FAKE_CITATION_JSON = json.dumps(
    {
        "answer": (
            "This may be Fabry disease (Source: Nature 2021, https://doi.org/10.1000/fake).\n"
            "See https://example.test/paper for details."
        ),
        "triage": "consult_doctor",
        "recommendations": ["See a clinician."],
        "matches": [
            {"condition": "Fabry disease", "weight": 3, "url": "https://example.test/a"},
            {"condition": "Alpha-galactosidase deficiency", "weight": 2, "url": "https://example.test/b"},
        ],
    }
)

RARE_COMMON_JSON = json.dumps(
    {
        "answer": "This wording may point to a lysosomal storage disorder rather than a common infection.",
        "triage": "consult_doctor",
        "recommendations": ["See a clinician."],
        "matches": [
            {"condition": "Influenza", "weight": 5},
            {"condition": "Common cold", "weight": 4},
            {"condition": "Fabry disease", "weight": 3},
            {"condition": "Gaucher disease", "weight": 2},
        ],
    }
)

TABLE_JSON = json.dumps(
    {
        "answer": (
            "Broad causes, not a diagnosis:\n\n"
            "| Mechanism | What it can mean |\n"
            "| --- | --- |\n"
            "| Genetic | A gene change may affect a protein |\n"
            "| Infection | A germ may injure tissue |\n\n"
            "Please name the specific disease."
        ),
        "triage": "self_care",
        "recommendations": ["Name the disease for a closer look."],
        "matches": [],
    }
)

MALFORMED_TABLE_JSON = json.dumps(
    {
        "answer": (
            "A rare disease is often defined as affecting fewer than five million people worldwide. "
            "Overview: | Mechanism | Meaning | | --- | --- | | Genetic | A gene change | | Infection | Tissue injury |"
        ),
        "triage": "self_care",
        "recommendations": ["See a clinician."],
        "matches": [],
    }
)

ONE_ROW_TABLE_JSON = json.dumps(
    {
        "answer": "Causes: | Genetic changes | Infections |",
        "triage": "self_care",
        "recommendations": ["See a clinician."],
        "matches": [],
    }
)


def test_unnamed_rare_disease_question_is_medical():
    assert classify_intent(UNNAMED) == "medical"
    assert is_broad_unnamed_medical_query(UNNAMED) is True
    assert is_broad_unnamed_medical_query(NAMED_ABSENT) is False
    assert is_broad_unnamed_medical_query("I have pain from a rare disease") is False


def test_unnamed_query_keeps_general_answer_and_drops_fake_cards():
    bundle = parse_kb_miss_payload(UNNAMED_JSON, UNNAMED)
    assert bundle is not None
    assert bundle.possible_conditions == []
    assert bundle.triage is None
    assert "Which specific rare disease would you like to know more about?" in bundle.answer
    assert "200,000" in bundle.answer
    assert "five million" not in bundle.answer.lower()
    assert "influenza" not in bundle.answer.lower()
    assert "common cold" not in bundle.answer.lower()
    assert "https://" not in bundle.answer
    assert "chroma" not in bundle.answer.lower()
    assert "groq" not in bundle.answer.lower()
    assert "openai" not in bundle.answer.lower()
    assert all(not row.get("url") for row in bundle.citations)
    assert any("not verified" in (row.get("title") or "").lower() for row in bundle.citations)
    assert any("knowledge base" in (row.get("title") or "").lower() for row in bundle.citations)
    assert bundle.answer.lower().count("this is general information, not a diagnosis") == 1
    assert "this explanation is general medical information" not in bundle.answer.lower()
    assert "not verified against the knowledge base" not in bundle.answer.lower()
    assert bundle.disclaimer == "This is general information, not a diagnosis."


def test_kb_miss_evidence_disclosure_is_not_repeated_in_the_answer():
    raw = json.dumps(
        {
            "answer": (
                "Diseases can arise in several broad ways.\n\n"
                "This is general information, not a diagnosis. "
                "This explanation is general medical information, not retrieved from "
                "the MediAssist knowledge base, and was not verified against it."
            ),
            "triage": "self_care",
            "recommendations": ["Name the disease for a closer look."],
            "matches": [],
        }
    )
    bundle = parse_kb_miss_payload(raw, UNNAMED)
    assert bundle is not None
    titles = [row["title"] for row in bundle.citations]
    assert "No matching sources were found in the MediAssist knowledge base" in titles
    assert "General medical knowledge was used and was not verified against the knowledge base" in titles
    assert bundle.answer.lower().count("this is general information, not a diagnosis") == 1
    assert "this explanation is general medical information" not in bundle.answer.lower()
    assert "not verified against the knowledge base" not in bundle.answer.lower()
    combined = "\n".join([bundle.answer, *titles])
    assert combined.lower().count("not verified against the knowledge base") == 1
    assert bundle.disclaimer == "This is general information, not a diagnosis."


def test_named_absent_disease_keeps_labeled_general_matches():
    bundle = parse_kb_miss_payload(NAMED_JSON, NAMED_ABSENT)
    assert bundle is not None
    assert bundle.triage is not None
    assert bundle.triage.level == "consult_doctor"
    names = [row["condition"].lower() for row in bundle.possible_conditions]
    assert "fabry disease" in names
    assert all(not row.get("url") for row in bundle.possible_conditions)
    assert all(not row.get("url") for row in bundle.citations)
    assert all("not verified" in (row.get("source") or "") for row in bundle.possible_conditions)


def test_missing_citations_are_labeled_not_fabricated():
    bundle = parse_kb_miss_payload(FAKE_CITATION_JSON, NAMED_ABSENT)
    assert bundle is not None
    assert "https://" not in bundle.answer
    assert "nature 2021" not in bundle.answer.lower()
    assert "(source:" not in bundle.answer.lower()
    titles = [row["title"] for row in bundle.citations]
    assert "No matching sources were found in the MediAssist knowledge base" in titles
    assert any("not verified against the knowledge base" in title.lower() for title in titles)
    assert all(not row.get("url") for row in bundle.citations)


def test_markdown_lists_and_tables_keep_structure():
    unnamed = parse_kb_miss_payload(TABLE_JSON, UNNAMED)
    assert unnamed is not None
    assert "| --- |" in unnamed.answer
    assert "| Genetic |" in unnamed.answer
    assert "\n" in unnamed.answer
    listed = parse_kb_miss_payload(UNNAMED_JSON, UNNAMED)
    assert listed is not None
    assert "- Genetic changes" in listed.answer


def test_malformed_tables_and_rare_disease_definition_are_corrected():
    from src.llm.markdown_format import normalize_markdown_tables

    repaired = parse_kb_miss_payload(MALFORMED_TABLE_JSON, UNNAMED)
    assert repaired is not None
    assert "five million" not in repaired.answer.lower()
    assert "200,000" in repaired.answer
    assert "Which specific rare disease would you like to know more about?" in repaired.answer
    assert "| Mechanism | Meaning |" in repaired.answer
    assert "| --- |" in repaired.answer
    assert repaired.answer.split("| Genetic |")[0].count("\n") >= 1

    listed = parse_kb_miss_payload(ONE_ROW_TABLE_JSON, UNNAMED)
    assert listed is not None
    assert "| Genetic changes |" not in listed.answer
    assert "**Genetic changes**" in listed.answer

    valid = normalize_markdown_tables(
        "| Mechanism | Meaning |\n| --- | --- |\n| Genetic | A gene change |"
    )
    assert valid.splitlines()[0].startswith("| Mechanism |")
    assert valid.splitlines()[1].startswith("| --- |")


def test_common_infections_are_not_kept_as_rare_examples():
    bundle = parse_kb_miss_payload(RARE_COMMON_JSON, "What causes Fabry disease, a rare disease?")
    assert bundle is not None
    names = {row["condition"].lower() for row in bundle.possible_conditions}
    assert "influenza" not in names
    assert "common cold" not in names
    assert "fabry disease" in names
    assert "gaucher disease" in names


def test_groq_success_for_unnamed_and_named_absent(monkeypatch):
    from src.llm import kb_miss as kb
    from src.pipeline import rag_pipeline as rp

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: (WEAK_HITS, WEAK_HITS))
    monkeypatch.setattr(rp, "can_use_llm_kb_fallback", lambda: True)
    monkeypatch.setattr(kb, "can_use_llm_kb_fallback", lambda: True)
    monkeypatch.setattr(kb, "medical_llm_status", lambda: "ready")
    monkeypatch.setattr(kb, "_call_llm", lambda *_a, **_k: UNNAMED_JSON)
    monkeypatch.setattr(rp, "generate_kb_miss_bundle", kb.generate_kb_miss_bundle)

    unnamed = run_pipeline(UNNAMED)
    assert unnamed.evidence_origin == "llm"
    assert unnamed.possible_conditions == []
    assert unnamed.triage is None
    assert "Which specific rare disease would you like to know more about?" in unnamed.answer
    assert "200,000" in unnamed.answer
    assert check_prescription_request(UNNAMED).triggered is False

    monkeypatch.setattr(kb, "_call_llm", lambda *_a, **_k: NAMED_JSON)
    named = run_pipeline(NAMED_ABSENT)
    assert named.evidence_origin == "llm"
    assert named.question_type == "POSSIBLE_CAUSES"
    assert named.triage is None
    assert named.possible_conditions == []
    assert "fabry" in named.answer.lower()
    assert all(not row.get("url") for row in named.citations)


def test_provider_failure_and_missing_key_for_unnamed_query(monkeypatch):
    from src.llm import kb_miss as kb
    from src.pipeline import rag_pipeline as rp

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: (WEAK_HITS, WEAK_HITS))
    monkeypatch.setattr(rp, "can_use_llm_kb_fallback", lambda: True)
    monkeypatch.setattr(kb, "medical_llm_status", lambda: "ready")
    monkeypatch.setattr(kb, "_call_llm", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("429 rate limit")))
    monkeypatch.setattr(rp, "generate_kb_miss_bundle", kb.generate_kb_miss_bundle)

    failed = run_pipeline(UNNAMED)
    assert LOOKUP_FAILED_MESSAGE in failed.answer
    assert failed.possible_conditions == []
    assert failed.evidence_origin == "none"
    assert "Groq" not in failed.answer
    assert "gsk_" not in failed.answer

    monkeypatch.setattr(kb, "medical_llm_status", lambda: "missing_key")
    missing = run_pipeline(UNNAMED)
    assert missing.answer == MISSING_KEY_MESSAGE
    assert missing.possible_conditions == []
    assert missing.evidence_origin == "none"


def test_empty_llm_answer_still_explains_unnamed_question(monkeypatch):
    from src.llm import kb_miss as kb
    from src.pipeline import rag_pipeline as rp

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: (WEAK_HITS, WEAK_HITS))
    monkeypatch.setattr(rp, "can_use_llm_kb_fallback", lambda: True)
    monkeypatch.setattr(kb, "can_use_llm_kb_fallback", lambda: True)
    monkeypatch.setattr(kb, "medical_llm_status", lambda: "ready")
    monkeypatch.setattr(kb, "_call_llm", lambda *_a, **_k: "")
    monkeypatch.setattr(rp, "generate_kb_miss_bundle", kb.generate_kb_miss_bundle)

    result = run_pipeline(UNNAMED)
    assert "genetic" in result.answer.lower()
    assert "200,000" in result.answer
    assert "Which specific rare disease would you like to know more about?" in result.answer
    assert "symptom detail" not in result.answer.lower()
    assert result.possible_conditions == []
    assert result.triage is None
    assert result.evidence_origin == "llm"


def test_stream_keeps_final_unnamed_answer(monkeypatch):
    from src.llm import kb_miss as kb
    from src.pipeline import rag_pipeline as rp
    from src.pipeline.rag_pipeline import iter_pipeline_stream

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: (WEAK_HITS, WEAK_HITS))
    monkeypatch.setattr(rp, "can_use_llm_kb_fallback", lambda: True)
    monkeypatch.setattr(kb, "can_use_llm_kb_fallback", lambda: True)
    monkeypatch.setattr(kb, "medical_llm_status", lambda: "ready")
    monkeypatch.setattr(kb, "_call_llm", lambda *_a, **_k: UNNAMED_JSON)
    monkeypatch.setattr(rp, "generate_kb_miss_bundle", kb.generate_kb_miss_bundle)

    events = list(iter_pipeline_stream(UNNAMED))
    tokens = [event.get("content") or "" for event in events if event.get("type") == "token"]
    done = next(event for event in events if event.get("type") == "done")
    answer = (done.get("result") or {}).get("answer") or ""
    assert "".join(tokens) == answer
    assert "genetic" in answer.lower()
    assert (done.get("result") or {}).get("triage") is None
    assert "symptom detail" not in answer.lower()
    token_at = next(index for index, event in enumerate(events) if event.get("type") == "token")
    done_at = next(index for index, event in enumerate(events) if event.get("type") == "done")
    assert token_at < done_at


def test_emergency_symptom_questions_still_use_triage(monkeypatch):
    from src.pipeline import rag_pipeline as rp

    monkeypatch.setattr(rp, "retrieve_candidates", lambda *_a, **_k: ([], []))
    monkeypatch.setattr(rp, "can_use_llm_kb_fallback", lambda: True)
    monkeypatch.setattr(rp, "generate_kb_miss_bundle", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no groq")))
    result = run_pipeline("crushing chest pain spreading to my jaw")
    assert result.triage is not None
    assert result.triage.level == "emergency"
    assert "112" in result.answer
