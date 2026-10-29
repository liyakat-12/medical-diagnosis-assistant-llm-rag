"""Read-only evaluation results and live retrieval probes for the faculty dashboard.

Metrics are recomputed from the per-query ranks written by
``evaluation/evaluate_kb_phase2.py`` and ``evaluation/evaluate_embeddings.py`` with the
same definitions those scripts use:

- Recall@k: share of labelled queries whose first expected document is ranked <= k.
- MRR: mean of 1 / rank of the first expected document (0 when it is not retrieved).

Nothing here is clinical validation. Missing result files are reported as missing,
never replaced with placeholder numbers.
"""
from __future__ import annotations

import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src import config

RETRIEVAL_DATASET = "kb_expansion_phase2.jsonl"
RETRIEVAL_RUN_GLOB = "kb_phase2_*.json"
RETRIEVAL_K_VALUES = (1, 3, 4)
EMBEDDING_K_VALUES = (1, 3, 5)

RUN_DESCRIPTIONS = {
    "baseline": "Before the Phase 2 knowledge-base expansion.",
    "after": "After the Phase 2 knowledge-base expansion.",
    "batch4": "After the re-ranker batch-size change (batch_size=4).",
    "production": "Production retrieval evaluation against the baked general knowledge-base index.",
}

MISSING_RETRIEVAL_RUNS_MESSAGE = (
    "No stored retrieval evaluation report was found under evaluation/results "
    f"(expected files matching {RETRIEVAL_RUN_GLOB}). "
    "Generate one with `python evaluation/evaluate_kb_phase2.py "
    "--out evaluation/results/kb_phase2_production.json` against the live index, "
    "then include that report in the API image. "
    "Live chat retrieval telemetry is separate and is not used for these metrics."
)

EMBEDDING_RUNS = (
    ("general", "General embeddings (MiniLM)", "Dense vector search only."),
    ("medical", "Biomedical embeddings (PubMedBERT)", "Dense vector search only."),
    ("general_rerank", "General embeddings + cross-encoder re-rank", "The production retrieval path."),
)

QUALITY_SUITES = (
    ("answer_quality_*.json", "answer_quality", "Answer quality"),
    ("conversation_phase4_*.json", "conversation", "Conversation handling"),
    ("semantic_consistency_phase6.json", "semantic_consistency", "Semantic consistency"),
)

GROUNDING_CHECKS = ("faithfulness", "no_fabricated_citation", "citation_url_ok", "no_invented_url", "https_citations")

_json_cache: dict[Path, tuple[float, Any]] = {}


def _mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def _load_json(path: Path) -> Any:
    mtime = path.stat().st_mtime
    cached = _json_cache.get(path)
    if cached and cached[0] == mtime:
        return cached[1]
    data = json.loads(path.read_text(encoding="utf-8"))
    _json_cache[path] = (mtime, data)
    return data


def _ratio(value: int, total: int) -> float | None:
    return value / total if total else None


def rank_metrics(ranks: list[int | None], k_values: tuple[int, ...] = RETRIEVAL_K_VALUES) -> dict:
    """Recall@k and MRR from 1-based ranks, where None means the expected document was not retrieved."""
    n = len(ranks)
    found = [rank for rank in ranks if rank is not None]
    metrics: dict[str, Any] = {"n": n, "found": len(found), "missed": n - len(found)}
    for k in k_values:
        metrics[f"recall_at_{k}"] = _ratio(sum(1 for rank in found if rank <= k), n)
    metrics["mrr"] = sum(1.0 / rank for rank in found) / n if n else None
    return metrics


def rank_distribution(ranks: list[int | None], depth: int) -> dict[str, int]:
    counts = {str(position): 0 for position in range(1, depth + 1)}
    counts["miss"] = 0
    for rank in ranks:
        if rank is None or rank > depth:
            counts["miss"] += 1
        else:
            counts[str(rank)] += 1
    return counts


def _dataset_labels(datasets_dir: Path) -> dict[str, dict]:
    path = datasets_dir / RETRIEVAL_DATASET
    if not path.exists():
        return {}
    labels: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("id"):
            labels[str(row["id"])] = row
    return labels


def _run_files(results_dir: Path) -> list[Path]:
    return sorted(results_dir.glob(RETRIEVAL_RUN_GLOB), key=lambda path: path.stat().st_mtime)


def _run_id(path: Path) -> str:
    return path.stem.removeprefix("kb_phase2_")


def _clean_rank(value: Any) -> int | None:
    return value if isinstance(value, int) and value > 0 else None


def _summarize_run(path: Path) -> dict:
    data = _load_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} is not a JSON object")
    rows = data.get("per_query")
    if not isinstance(rows, list):
        raise ValueError(f"{path.name} is missing a per_query list")
    ranks = [_clean_rank(row.get("rank") if isinstance(row, dict) else None) for row in rows]
    depth = max(
        (len(row.get("retrieved") or []) for row in rows if isinstance(row, dict)),
        default=0,
    ) or max(RETRIEVAL_K_VALUES)
    categories: dict[str, list[int | None]] = {}
    for row, rank in zip(rows, ranks):
        if not isinstance(row, dict):
            continue
        categories.setdefault(str(row.get("category") or "uncategorised"), []).append(rank)
    run_id = _run_id(path)
    report_config = data.get("config") if isinstance(data.get("config"), dict) else {}
    return {
        "id": run_id,
        "label": run_id.replace("_", " ").title(),
        "description": RUN_DESCRIPTIONS.get(run_id, "Stored retrieval evaluation run."),
        "file": path.name,
        "generated_at": _mtime_iso(path),
        "dataset": report_config.get("dataset") or data.get("dataset") or RETRIEVAL_DATASET,
        "corpus_docs": data.get("corpus_docs"),
        "query_count": data.get("query_count"),
        "depth": depth,
        "config": {
            "embedding_mode": report_config.get("embedding_mode"),
            "embedding_backend": report_config.get("embedding_backend"),
            "rerank_enabled": report_config.get("rerank_enabled"),
            "top_k": report_config.get("top_k"),
        },
        "metrics": rank_metrics(ranks),
        "stored_metrics": {
            "recall_at_1": data.get("recall@1"),
            "recall_at_4": data.get("recall@4"),
            "mrr": data.get("mrr"),
        },
        "rank_distribution": rank_distribution(ranks, depth),
        "categories": {name: rank_metrics(values) for name, values in sorted(categories.items())},
        "safety": data.get("safety") or {},
    }


def retrieval_runs(results_dir: Path | None = None) -> list[dict]:
    """Load valid kb_phase2_*.json reports. Malformed files are skipped, not invented."""
    results_dir = results_dir or config.EVAL_RESULTS_DIR
    runs: list[dict] = []
    for path in _run_files(results_dir):
        try:
            runs.append(_summarize_run(path))
        except (OSError, ValueError, TypeError, json.JSONDecodeError, KeyError):
            continue
    return runs


def retrieval_cases(run_id: str | None = None, results_dir: Path | None = None, datasets_dir: Path | None = None) -> dict | None:
    results_dir = results_dir or config.EVAL_RESULTS_DIR
    datasets_dir = datasets_dir or config.EVAL_DATASETS_DIR
    runs = retrieval_runs(results_dir)
    if not runs:
        return None
    summary = next((item for item in runs if item["id"] == run_id), None) if run_id else runs[-1]
    if summary is None:
        return None
    path = results_dir / summary["file"]
    if not path.exists():
        return None
    labels = _dataset_labels(datasets_dir)
    cases = []
    for row in _load_json(path).get("per_query") or []:
        rank = _clean_rank(row.get("rank"))
        label = labels.get(str(row.get("id")), {})
        cases.append(
            {
                "id": row.get("id"),
                "category": row.get("category") or label.get("category") or "uncategorised",
                "query": row.get("query") or label.get("query") or "",
                "expected_doc_ids": list(label.get("expected_doc_ids") or []),
                "retrieved_doc_ids": list(row.get("retrieved") or []),
                "rank": rank,
                "reciprocal_rank": 1.0 / rank if rank else 0.0,
            }
        )
    return {"run": summary, "dataset": RETRIEVAL_DATASET if labels else None, "cases": cases}


def _csv_rank(value: str | None) -> int | None:
    try:
        rank = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return rank if rank > 0 else None


def embedding_comparison(results_dir: Path | None = None) -> list[dict]:
    results_dir = results_dir or config.EVAL_RESULTS_DIR
    runs = []
    for run_id, label, description in EMBEDDING_RUNS:
        path = results_dir / f"embedding_eval_{run_id}.csv"
        if not path.exists():
            continue
        with path.open(encoding="utf-8", newline="") as handle:
            ranks = [_csv_rank(row.get("rank_of_correct_doc")) for row in csv.DictReader(handle)]
        runs.append(
            {
                "id": run_id,
                "label": label,
                "description": description,
                "file": path.name,
                "generated_at": _mtime_iso(path),
                "depth": max(EMBEDDING_K_VALUES),
                "metrics": rank_metrics(ranks, EMBEDDING_K_VALUES),
            }
        )
    return runs


def _suite_summary(path: Path, suite: str, label: str) -> dict:
    data = _load_json(path)
    if suite == "conversation":
        total, passed, failed = data.get("pipeline_n"), data.get("pipeline_passed"), data.get("pipeline_failed")
    else:
        total, passed, failed = data.get("case_count"), data.get("passed"), data.get("failed")
    return {
        "id": path.stem,
        "suite": suite,
        "label": label,
        "file": path.name,
        "generated_at": _mtime_iso(path),
        "cases": total,
        "passed": passed,
        "failed": failed,
        "method": data.get("method"),
    }


def quality_reports(results_dir: Path | None = None) -> list[dict]:
    results_dir = results_dir or config.EVAL_RESULTS_DIR
    reports = []
    for pattern, suite, label in QUALITY_SUITES:
        for path in sorted(results_dir.glob(pattern), key=lambda item: item.stat().st_mtime):
            reports.append(_suite_summary(path, suite, label))
    return reports


def grounding_summary(results_dir: Path | None = None) -> dict | None:
    """Evidence availability and citation checks from the newest answer-quality report."""
    results_dir = results_dir or config.EVAL_RESULTS_DIR
    files = sorted(results_dir.glob("answer_quality_*.json"), key=lambda item: item.stat().st_mtime)
    if not files:
        return None
    path = files[-1]
    data = _load_json(path)
    cases = data.get("cases") or []
    origins: dict[str, int] = {}
    faithfulness: dict[str, int] = {}
    with_citations = 0
    total_citations = 0
    without_evidence = []
    for case in cases:
        origin = str(case.get("origin") or "none")
        origins[origin] = origins.get(origin, 0) + 1
        status = str(case.get("faithfulness") or "not_audited")
        faithfulness[status] = faithfulness.get(status, 0) + 1
        titles = case.get("citation_titles") or []
        total_citations += len(titles)
        if titles:
            with_citations += 1
        if origin == "none":
            without_evidence.append(
                {
                    "id": case.get("id"),
                    "category": case.get("category"),
                    "query": case.get("query"),
                    "refused": bool(case.get("refused")),
                    "triage": case.get("triage"),
                    "passed": bool(case.get("passed")),
                }
            )
    check_n = data.get("check_n") or {}
    check_failures = data.get("check_fail_counts") or {}
    return {
        "report": path.name,
        "generated_at": _mtime_iso(path),
        "cases": len(cases),
        "cases_with_citations": with_citations,
        "citations_total": total_citations,
        "origin_counts": origins,
        "faithfulness_counts": faithfulness,
        "checks": {
            name: {"n": int(check_n.get(name, 0)), "failed": int(check_failures.get(name, 0))}
            for name in GROUNDING_CHECKS
            if name in check_n
        },
        "without_evidence": without_evidence,
        "method": data.get("method"),
    }


def knowledge_base_status() -> dict:
    documents = len(list(config.KNOWLEDGE_BASE_DIR.glob("*.md"))) if config.KNOWLEDGE_BASE_DIR.exists() else None
    status: dict[str, Any] = {
        "documents": documents,
        "chunks_indexed": None,
        "index_ready": False,
        "embedding_mode": config.EMBEDDING_MODE,
        "rerank_enabled": config.RERANK_ENABLED,
        "top_k": config.TOP_K,
        "rerank_candidates": config.RERANK_CANDIDATES,
        "error": None,
    }
    try:
        from src.retrieval.retriever import _get_store

        chunks = _get_store(config.EMBEDDING_MODE).count()
        status["chunks_indexed"] = chunks
        status["index_ready"] = chunks > 0
        if not chunks:
            status["error"] = "The retrieval index is empty. Run `python scripts/build_index.py general`."
    except Exception:
        status["error"] = "The retrieval index could not be opened."
    return status


def retrieval_report_status(results_dir: Path | None = None) -> dict:
    """Explain whether packaged retrieval evaluation reports are available."""
    results_dir = results_dir or config.EVAL_RESULTS_DIR
    files = [path.name for path in _run_files(results_dir)]
    valid = retrieval_runs(results_dir)
    return {
        "directory": str(results_dir),
        "directory_exists": results_dir.exists(),
        "expected_glob": RETRIEVAL_RUN_GLOB,
        "dataset": RETRIEVAL_DATASET,
        "report_files": files,
        "valid_runs": len(valid),
        "missing_message": None if valid else MISSING_RETRIEVAL_RUNS_MESSAGE,
    }


def overview() -> dict:
    runs = retrieval_runs()
    return {
        "knowledge_base": knowledge_base_status(),
        "retrieval_runs": runs,
        "retrieval_report_status": retrieval_report_status(),
        "embedding_comparison": embedding_comparison(),
        "quality_reports": quality_reports(),
        "grounding": grounding_summary(),
        "test_suite": None,
        "definitions": {
            "recall_at_k": "Share of labelled queries whose first expected document is ranked within the top k results.",
            "mrr": "Mean of 1 / rank of the first expected document; a query whose expected document is not retrieved scores 0.",
        },
    }


def live_retrieval(query: str, top_k: int | None = None) -> dict:
    """Run the production query preparation and retriever without generating an answer or saving anything."""
    from src.pipeline.conversation_state import build_conversation_state
    from src.retrieval.retriever import retrieve_candidates
    from src.safety.guardrails import check_prescription_request

    top_k = top_k or config.TOP_K
    started = time.perf_counter()
    state = build_conversation_state(query)
    prepare_ms = round((time.perf_counter() - started) * 1000, 2)

    retrieve_started = time.perf_counter()
    evidence, _pool = retrieve_candidates(state.search_query, top_k=top_k, mode=config.EMBEDDING_MODE)
    retrieve_ms = round((time.perf_counter() - retrieve_started) * 1000, 2)

    if check_prescription_request(query).triggered:
        skip_reason = "The chat pipeline refuses prescription or dosage requests before retrieval."
    elif state.intent != "medical":
        skip_reason = "The chat pipeline classifies this as a non-medical message and does not retrieve notes for it."
    else:
        skip_reason = None
    return {
        "query": query,
        "search_query": state.search_query,
        "intent": state.intent,
        "question_type": state.question_type,
        "pipeline_retrieves": skip_reason is None,
        "pipeline_skip_reason": skip_reason,
        "rerank_enabled": config.RERANK_ENABLED,
        "top_k": top_k,
        "timings": {"prepare_ms": prepare_ms, "retrieve_ms": retrieve_ms},
        "results": [
            {
                "rank": index,
                "doc_id": item.doc_id,
                "title": item.title,
                "source": item.source,
                "url": item.url,
                "condition": item.condition,
                "relevance_score": round(float(item.relevance_score), 4),
                "vector_score": round(float(item.vector_score), 4),
            }
            for index, item in enumerate(evidence, start=1)
        ],
    }
