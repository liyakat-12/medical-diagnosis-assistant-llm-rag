"""Evaluate the Phase 2 labeled query set against the live general index.

Usage:
    python evaluation/evaluate_kb_phase2.py
    python evaluation/evaluate_kb_phase2.py --out evaluation/results/kb_phase2_baseline.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))
sys.path.insert(0, str(ROOT_DIR / "evaluation" / "datasets"))

from kb_phase2_queries import QUERIES, dump_jsonl, retrieval_queries  # noqa: E402
from src.ingestion.loader import load_documents  # noqa: E402
from src.pipeline.conversation_state import build_conversation_state  # noqa: E402
from src.retrieval.retriever import retrieve  # noqa: E402
from src.safety.guardrails import check_emergency, check_prescription_request, classify_intent  # noqa: E402


def _rank(retrieved: list[str], expected: list[str]) -> int | None:
    for index, doc_id in enumerate(retrieved, start=1):
        if doc_id in expected:
            return index
    return None


def evaluate(k: int = 4) -> dict:
    docs = load_documents()
    corpus_ids = {doc.id for doc in docs}
    missing_labels = sorted(
        {
            doc_id
            for row in QUERIES
            for doc_id in row.get("expected_doc_ids") or []
            if doc_id not in corpus_ids
        }
    )

    retrieval_rows = retrieval_queries()
    hits_at_1 = 0
    hits_at_k = 0
    reciprocal = 0.0
    misses: list[dict] = []
    citation_ok = 0
    per_query: list[dict] = []

    for row in retrieval_rows:
        search = build_conversation_state(row["query"]).search_query
        hits = retrieve(search, top_k=k, mode="general")
        retrieved = [hit.doc_id for hit in hits]
        rank = _rank(retrieved, row["expected_doc_ids"])
        if rank == 1:
            hits_at_1 += 1
        if rank is not None and rank <= k:
            hits_at_k += 1
            reciprocal += 1.0 / rank
        else:
            misses.append({"id": row["id"], "query": row["query"], "retrieved": retrieved, "expected": row["expected_doc_ids"]})
        sourced = all(bool(hit.source) and str(hit.url or "").startswith("https://") for hit in hits) if hits else False
        if sourced:
            citation_ok += 1
        per_query.append(
            {
                "id": row["id"],
                "category": row["category"],
                "query": row["query"],
                "rank": rank,
                "retrieved": retrieved,
            }
        )

    n = len(retrieval_rows) or 1
    safety = {"emergency": [], "prescription": [], "out_of_scope": [], "isolation": [], "absent": [], "gap": []}
    for row in QUERIES:
        mode = row["eval_mode"]
        query = row["query"]
        if mode == "emergency":
            result = check_emergency(query)
            safety["emergency"].append({"id": row["id"], "ok": result.triggered, "query": query})
        elif mode == "prescription":
            result = check_prescription_request(query)
            safety["prescription"].append({"id": row["id"], "ok": result.triggered, "query": query})
        elif mode == "out_of_scope":
            intent = classify_intent(query)
            safety["out_of_scope"].append({"id": row["id"], "ok": intent != "medical", "intent": intent, "query": query})
        elif mode == "isolation":
            state = build_conversation_state(query, row.get("history") or [])
            status_ok = state.status == row.get("expected_status")
            hits = retrieve(state.search_query, top_k=k, mode="general")
            retrieved = [hit.doc_id for hit in hits]
            expected_hit = bool(set(retrieved) & set(row.get("expected_doc_ids") or []))
            forbidden = set(row.get("forbidden_doc_ids") or [])
            forbidden_ok = not (set(retrieved) & forbidden)
            safety["isolation"].append(
                {
                    "id": row["id"],
                    "ok": status_ok and expected_hit and forbidden_ok,
                    "status": state.status,
                    "retrieved": retrieved,
                }
            )
        elif mode == "absent":
            safety["absent"].append({"id": row["id"], "ok": not (set(row.get("expected_doc_ids") or []) & corpus_ids), "query": query})
        elif mode == "gap":
            safety["gap"].append({"id": row["id"], "query": query, "weak_ids": row.get("expected_doc_ids") or []})

    by_category = defaultdict(lambda: {"n": 0, "hit4": 0})
    for row, detail in zip(retrieval_rows, per_query):
        by_category[row["category"]]["n"] += 1
        if detail["rank"] is not None:
            by_category[row["category"]]["hit4"] += 1

    from src import config as app_config

    return {
        "corpus_docs": len(docs),
        "query_count": len(QUERIES),
        "retrieval_n": len(retrieval_rows),
        "dataset": "kb_expansion_phase2.jsonl",
        "config": {
            "embedding_mode": app_config.EMBEDDING_MODE,
            "embedding_backend": getattr(app_config, "EMBEDDING_BACKEND", "sentence_transformers"),
            "rerank_enabled": app_config.RERANK_ENABLED,
            "top_k": k,
            "dataset": "kb_expansion_phase2.jsonl",
        },
        "missing_labels": missing_labels,
        "recall@1": hits_at_1 / n,
        "recall@4": hits_at_k / n,
        "mrr": reciprocal / n,
        "citation_rate": citation_ok / n,
        "retrieval_misses": misses,
        "category_recall@4": {
            key: (val["hit4"] / val["n"] if val["n"] else 0.0) for key, val in sorted(by_category.items())
        },
        "safety": {
            key: {
                "n": len(rows),
                "passed": sum(1 for item in rows if item.get("ok")),
                "failed": [item for item in rows if item.get("ok") is False],
            }
            for key, rows in safety.items()
            if key != "gap"
        },
        "gaps": safety["gap"],
        "counts": dict(Counter(row["eval_mode"] for row in QUERIES)),
        "per_query": per_query,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=4)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    dump_jsonl(ROOT_DIR / "evaluation" / "datasets" / "kb_expansion_phase2.jsonl")
    result = evaluate(k=args.k)
    summary = {key: result[key] for key in result if key not in {"per_query", "retrieval_misses"}}
    summary["miss_count"] = len(result["retrieval_misses"])
    print(json.dumps(summary, indent=2))
    print("\nRetrieval misses:")
    for miss in result["retrieval_misses"]:
        print(f"  {miss['id']}: {miss['query']!r}")
        print(f"    got {miss['retrieved']}")
        print(f"    want {miss['expected']}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
