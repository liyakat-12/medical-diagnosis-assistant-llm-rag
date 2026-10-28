"""Phase 5 offline reranking experiment.

Does not change production retrieval, config, indexes, or thresholds.
Does not overwrite performance_phase5_baseline.json.

Usage:
    .\\venv\\Scripts\\python.exe evaluation/evaluate_rerank_phase5.py --out evaluation/results/performance_phase5_rerank_experiment.json
"""
from __future__ import annotations

import argparse
import inspect
import json
import os
import platform
import statistics
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))
sys.path.insert(0, str(ROOT_DIR / "evaluation" / "datasets"))

DEFAULT_WARM = 30
CANDIDATE_COUNTS = (4, 6, 8, 12)

EXPERIMENT_A_QUERIES = [
    {"id": "ra_short", "label": "short", "query": "pain"},
    {"id": "ra_medium", "label": "medium", "query": "I have a dry cough at night"},
    {"id": "ra_knee", "label": "medium_multi", "query": "Why does my knee hurt when I climb stairs?"},
    {
        "id": "ra_long",
        "label": "long",
        "query": "I have a swollen painful calf after a long flight and now I feel breathless",
    },
    {
        "id": "ra_emergency",
        "label": "long_emergency",
        "query": "I have severe crushing chest pain spreading to my jaw",
    },
]


def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 3)
    rank = (len(ordered) - 1) * (p / 100.0)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    if low == high:
        return round(ordered[low], 3)
    frac = rank - low
    return round(ordered[low] + (ordered[high] - ordered[low]) * frac, 3)


def _stats(values: list[float]) -> dict:
    clean = [float(item) for item in values if item is not None]
    if not clean:
        return {"n": 0, "min": None, "median": None, "p95": None, "max": None, "mean": None}
    return {
        "n": len(clean),
        "min": round(min(clean), 3),
        "median": _percentile(clean, 50),
        "p95": _percentile(clean, 95),
        "max": round(max(clean), 3),
        "mean": round(statistics.fmean(clean), 3),
        "p95_note": (
            "Indicative interpolation only; n<100 so p95 is not a precise tail estimate."
            if len(clean) < 100
            else ""
        ),
    }


def _time_ms(fn):
    started = time.perf_counter()
    result = fn()
    return result, round((time.perf_counter() - started) * 1000, 3)


def _doc_ids(chunks) -> list[str]:
    ids = []
    for chunk in chunks:
        doc_id = str((chunk.metadata or {}).get("doc_id") or "")
        ids.append(doc_id)
    return ids


def _unique(ids: list[str]) -> list[str]:
    seen = []
    for item in ids:
        if item and item not in seen:
            seen.append(item)
    return seen


def _passage_stats(chunks) -> dict:
    texts = [str(chunk.text or "") for chunk in chunks]
    chars = [len(text) for text in texts]
    words = [len(text.split()) for text in texts]
    return {
        "n": len(chunks),
        "chars_total": sum(chars),
        "chars_median": _percentile([float(item) for item in chars], 50) if chars else None,
        "words_total": sum(words),
        "words_median": _percentile([float(item) for item in words], 50) if words else None,
    }


def _first_rank(retrieved: list[str], expected: list[str]) -> int | None:
    for index, doc_id in enumerate(retrieved, start=1):
        if doc_id in expected:
            return index
    return None


def _environment() -> dict:
    from src import config
    from src.retrieval.reranker import _device

    uname = platform.uname()
    return {
        "os": f"{uname.system} {uname.release}",
        "machine": uname.machine,
        "processor": uname.processor,
        "python": platform.python_version(),
        "cpu_count": os.cpu_count(),
        "rerank_device": _device(),
        "embedding_mode": config.EMBEDDING_MODE,
        "rerank_enabled_config": config.RERANK_ENABLED,
        "rerank_candidates_config": config.RERANK_CANDIDATES,
        "rerank_model": config.RERANK_MODEL,
        "top_k_config": config.TOP_K,
        "min_relevance_score": config.MIN_RELEVANCE_SCORE,
        "min_vector_score": config.MIN_VECTOR_SCORE,
        "production_config_changed": False,
        "layer": "offline_rerank_only",
        "excluded": [
            "Full pipeline wall time",
            "FastAPI / Mongo / SSE / browser",
            "Query embedding and Chroma latency in Experiment A timings",
            "Live LLM provider",
        ],
    }


def _inspect_predict() -> dict:
    from src.retrieval.reranker import _load_model

    model = _load_model()
    predict = getattr(model, "predict", None)
    signature = ""
    defaults = {}
    if predict is not None:
        try:
            signature = str(inspect.signature(predict))
            for name, param in inspect.signature(predict).parameters.items():
                if param.default is not inspect.Parameter.empty and name in {"batch_size", "show_progress_bar"}:
                    defaults[name] = param.default
        except (TypeError, ValueError):
            signature = "unavailable"
    return {
        "model_class": type(model).__name__,
        "predict_signature": signature,
        "predict_defaults": defaults,
        "production_call": "model.predict(pairs, show_progress_bar=False) once per request",
        "one_chunk_short_circuit": "rerank_chunks skips predict when len(chunks) <= 1",
        "persists_state": False,
    }


def experiment_a(store, warm: int) -> dict:
    from src.retrieval.reranker import _load_model, rerank_chunks

    _, load_ms = _time_ms(_load_model)
    rows = []
    for item in EXPERIMENT_A_QUERIES:
        chunks, search_ms = _time_ms(lambda q=item["query"]: store.search(q, top_k=12))
        if chunks:
            rerank_chunks(item["query"], chunks, top_k=len(chunks))
        samples = []
        for _ in range(warm):
            _, elapsed = _time_ms(lambda q=item["query"], c=chunks: rerank_chunks(q, c, top_k=len(c)))
            samples.append(elapsed)
        rows.append(
            {
                "id": item["id"],
                "label": item["label"],
                "query": item["query"],
                "query_chars": len(item["query"]),
                "query_words": len(item["query"].split()),
                "candidate_count": len(chunks),
                "candidate_doc_ids": _unique(_doc_ids(chunks)),
                "passages": _passage_stats(chunks),
                "chroma_fetch_ms_once": search_ms,
                "warm_n_requested": warm,
                "rerank_ms": _stats(samples),
                "note": "Rerank-only on frozen Chroma hits. chroma_fetch_ms_once is not included in rerank_ms.",
            }
        )
    return {
        "warm_repeats": warm,
        "model_init_ms": load_ms,
        "model_init_note": (
            "Second _load_model() after any earlier load is cache-hit time, not a cold Hugging Face download. "
            "See experiment_c.cold_or_cached_init_ms for the first timed load in this process."
        ),
        "queries": rows,
    }


def _score_pool(search_query: str, pool, n: int, expected: list[str]) -> dict:
    from src.retrieval.reranker import rerank_chunks

    subset = list(pool[:n])
    pool_ids = _unique(_doc_ids(subset))
    disappeared = [doc_id for doc_id in expected if doc_id and doc_id not in pool_ids]
    ranked = rerank_chunks(search_query, subset, top_k=len(subset)) if subset else []
    top4 = _doc_ids(ranked[:4])
    rank = _first_rank(top4, expected)
    return {
        "candidate_count": n,
        "actual_candidates": len(subset),
        "pool_doc_ids": pool_ids,
        "top4_doc_ids": top4,
        "rank": rank,
        "expected_missing_from_pool": disappeared,
        "hit1": rank == 1,
        "hit4": rank is not None and rank <= 4,
        "rr": (1.0 / rank) if rank else 0.0,
    }


def experiment_b(store) -> dict:
    from kb_phase2_queries import QUERIES, retrieval_queries
    from src.pipeline.conversation_state import build_conversation_state
    from src.safety.guardrails import check_emergency, check_prescription_request, classify_intent

    retrieval_rows = retrieval_queries()
    per_config = {
        n: {
            "hits1": 0,
            "hits4": 0,
            "reciprocal": 0.0,
            "pool_losses": [],
            "ranking_diffs_vs_12": [],
            "new_misses_vs_12": [],
            "new_hits_vs_12": [],
            "per_query": [],
        }
        for n in CANDIDATE_COUNTS
    }
    vector_ref = {"hits1": 0, "hits4": 0, "reciprocal": 0.0, "per_query": []}

    for row in retrieval_rows:
        expected = list(row.get("expected_doc_ids") or [])
        search = build_conversation_state(row["query"]).search_query
        pool = store.search(search, top_k=12)
        vector_top4 = _doc_ids(pool[:4])
        vector_rank = _first_rank(vector_top4, expected)
        if vector_rank == 1:
            vector_ref["hits1"] += 1
        if vector_rank is not None and vector_rank <= 4:
            vector_ref["hits4"] += 1
            vector_ref["reciprocal"] += 1.0 / vector_rank
        vector_ref["per_query"].append({"id": row["id"], "rank": vector_rank, "top4": vector_top4})

        scored = {n: _score_pool(search, pool, n, expected) for n in CANDIDATE_COUNTS}
        baseline_top4 = scored[12]["top4_doc_ids"]
        baseline_hit4 = scored[12]["hit4"]
        baseline_hit1 = scored[12]["hit1"]
        for n, result in scored.items():
            bucket = per_config[n]
            if result["hit1"]:
                bucket["hits1"] += 1
            if result["hit4"]:
                bucket["hits4"] += 1
                bucket["reciprocal"] += result["rr"]
            if result["expected_missing_from_pool"]:
                bucket["pool_losses"].append(
                    {
                        "id": row["id"],
                        "query": row["query"],
                        "expected_missing_from_pool": result["expected_missing_from_pool"],
                        "expected": expected,
                        "pool_doc_ids": result["pool_doc_ids"],
                    }
                )
            if n != 12 and result["top4_doc_ids"] != baseline_top4:
                bucket["ranking_diffs_vs_12"].append(
                    {
                        "id": row["id"],
                        "query": row["query"],
                        "top4_n": result["top4_doc_ids"],
                        "top4_12": baseline_top4,
                        "rank_n": result["rank"],
                        "rank_12": scored[12]["rank"],
                    }
                )
            if n != 12 and baseline_hit4 and not result["hit4"]:
                bucket["new_misses_vs_12"].append({"id": row["id"], "query": row["query"], "top4": result["top4_doc_ids"]})
            if n != 12 and result["hit4"] and not baseline_hit4:
                bucket["new_hits_vs_12"].append({"id": row["id"], "query": row["query"], "top4": result["top4_doc_ids"]})
            bucket["per_query"].append(
                {
                    "id": row["id"],
                    "category": row["category"],
                    "rank": result["rank"],
                    "top4": result["top4_doc_ids"],
                    "expected_missing_from_pool": result["expected_missing_from_pool"],
                }
            )

    n_ret = len(retrieval_rows) or 1
    summary = {}
    for n, bucket in per_config.items():
        summary[str(n)] = {
            "candidate_count": n,
            "retrieval_n": n_ret,
            "recall@1": bucket["hits1"] / n_ret,
            "recall@4": bucket["hits4"] / n_ret,
            "mrr": bucket["reciprocal"] / n_ret,
            "hits1": bucket["hits1"],
            "hits4": bucket["hits4"],
            "pool_loss_queries": len(bucket["pool_losses"]),
            "ranking_diff_queries_vs_12": len(bucket["ranking_diffs_vs_12"]),
            "new_misses_vs_12": [item["id"] for item in bucket["new_misses_vs_12"]],
            "new_hits_vs_12": [item["id"] for item in bucket["new_hits_vs_12"]],
            "representative_pool_losses": bucket["pool_losses"][:12],
            "representative_ranking_diffs": bucket["ranking_diffs_vs_12"][:15],
            "all_pool_losses": bucket["pool_losses"],
            "all_ranking_diffs": bucket["ranking_diffs_vs_12"],
        }

    isolation = []
    for row in QUERIES:
        if row["eval_mode"] != "isolation":
            continue
        state = build_conversation_state(row["query"], row.get("history") or [])
        pool = store.search(state.search_query, top_k=12)
        expected = list(row.get("expected_doc_ids") or [])
        forbidden = set(row.get("forbidden_doc_ids") or [])
        by_n = {}
        for n in CANDIDATE_COUNTS:
            scored = _score_pool(state.search_query, pool, n, expected)
            retrieved = set(scored["top4_doc_ids"])
            by_n[str(n)] = {
                "status": state.status,
                "status_ok": state.status == row.get("expected_status"),
                "top4": scored["top4_doc_ids"],
                "expected_hit": bool(retrieved & set(expected)),
                "forbidden_ok": not (retrieved & forbidden),
            }
        isolation.append({"id": row["id"], "query": row["query"], "by_n": by_n})

    safety = {
        "emergency": [
            {"id": row["id"], "ok": check_emergency(row["query"]).triggered}
            for row in QUERIES
            if row["eval_mode"] == "emergency"
        ],
        "prescription": [
            {"id": row["id"], "ok": check_prescription_request(row["query"]).triggered}
            for row in QUERIES
            if row["eval_mode"] == "prescription"
        ],
        "out_of_scope": [
            {
                "id": row["id"],
                "intent": (intent := classify_intent(row["query"])),
                "ok": intent != "medical",
            }
            for row in QUERIES
            if row["eval_mode"] == "out_of_scope"
        ],
        "note": "Emergency, prescription, and out-of-scope checks do not call the reranker.",
    }

    return {
        "method": (
            "One Chroma fetch of 12 hits per Phase 2 retrieval query. "
            "Each candidate-count alternative reranks only the first N vector hits, then takes top 4. "
            "Production RERANK_CANDIDATES was not changed."
        ),
        "retrieval_n": n_ret,
        "reference_phase2_after_file": {
            "path": "evaluation/results/kb_phase2_after.json",
            "recall@1": 0.8349514563106796,
            "recall@4": 1.0,
            "mrr": 0.9101941747572816,
            "note": "Prior production retrieve() result. This experiment re-scores offline and may differ slightly if the live index changed.",
        },
        "by_candidate_count": summary,
        "reference_vector_top4_no_rerank": {
            "recall@1": vector_ref["hits1"] / n_ret,
            "recall@4": vector_ref["hits4"] / n_ret,
            "mrr": vector_ref["reciprocal"] / n_ret,
            "note": "First 4 Chroma hits with no cross-encoder. Not a production change; reference only.",
        },
        "isolation": isolation,
        "safety_independent_of_rerank": {
            key: {
                "n": len(rows),
                "passed": sum(1 for item in rows if item.get("ok")),
                "failed": [item["id"] for item in rows if item.get("ok") is False],
            }
            if key != "note"
            else rows
            for key, rows in safety.items()
        },
    }


def experiment_b_latency(store, warm: int) -> dict:
    from src.retrieval.reranker import rerank_chunks

    query = "Why does my knee hurt when I climb stairs?"
    chunks = store.search(query, top_k=12)
    if chunks:
        rerank_chunks(query, chunks, top_k=len(chunks))
    by_n = {}
    for n in CANDIDATE_COUNTS:
        subset = list(chunks[:n])
        samples = []
        for _ in range(warm):
            _, elapsed = _time_ms(lambda q=query, c=subset: rerank_chunks(q, c, top_k=len(c)))
            samples.append(elapsed)
        by_n[str(n)] = {
            "candidate_count": n,
            "actual_candidates": len(subset),
            "passages": _passage_stats(subset),
            "rerank_ms": _stats(samples),
        }
    return {
        "query": query,
        "warm_repeats": warm,
        "note": "Same frozen Chroma pool; only the first N passages are scored. Rerank-only, not pipeline latency.",
        "by_candidate_count": by_n,
    }


def experiment_c(store, warm: int) -> dict:
    from src.retrieval.reranker import _load_model, rerank_chunks

    init_ms = None
    if _load_model.cache_info().currsize == 0:
        _, init_ms = _time_ms(_load_model)
    else:
        init_ms = 0.0
    model = _load_model()
    query = "I have a dry cough at night"
    chunks = store.search(query, top_k=12)
    pairs = [(query, chunk.text) for chunk in chunks]
    rerank_chunks(query, chunks, top_k=len(chunks))
    model.predict(pairs, show_progress_bar=False)

    batched = []
    for _ in range(warm):
        _, elapsed = _time_ms(lambda: model.predict(pairs, show_progress_bar=False))
        batched.append(elapsed)

    sequential = []
    for _ in range(warm):
        def _one_by_one():
            return [model.predict([pair], show_progress_bar=False) for pair in pairs]

        _, elapsed = _time_ms(_one_by_one)
        sequential.append(elapsed)

    slice4 = []
    full12 = []
    for _ in range(warm):
        _, elapsed = _time_ms(lambda: rerank_chunks(query, chunks, top_k=4))
        slice4.append(elapsed)
        _, elapsed = _time_ms(lambda: rerank_chunks(query, chunks, top_k=12))
        full12.append(elapsed)

    return {
        "cold_or_cached_init_ms": init_ms,
        "inspect": _inspect_predict(),
        "redundant_work": {
            "retrieve_candidates": (
                "One store.search and one rerank_chunks per retrieve_candidates call. "
                "_to_evidence is applied twice (top slice and full pool) after rerank; that is formatting, not a second model pass."
            ),
            "rerank_top_k": (
                "Production calls rerank_chunks(..., top_k=len(results)), so every fetched candidate is scored. "
                "Passing a smaller top_k still scores every pair because predict() runs on the full list first."
            ),
            "pipeline": "Emergency regex and classify_triage can run before retrieval; they do not rerank.",
            "user_answer_cache": "Not present and not added. Personalized medical answers must not be cached.",
        },
        "query": query,
        "pair_count": len(pairs),
        "warm_repeats": warm,
        "batched_predict_ms": _stats(batched),
        "sequential_predict_ms": _stats(sequential),
        "rerank_chunks_top_k_4_on_12_pairs_ms": _stats(slice4),
        "rerank_chunks_top_k_12_on_12_pairs_ms": _stats(full12),
        "finding": (
            "Production already batches pairs in one predict() call. "
            "Reducing the returned top_k without shrinking the pair list does not remove model work."
        ),
    }


def evaluate(warm: int) -> dict:
    from src import config
    from src.retrieval.reranker import _load_model
    from src.retrieval.retriever import _get_store

    if config.RERANK_CANDIDATES != 12 or not config.RERANK_ENABLED:
        raise SystemExit(
            f"Expected production defaults RERANK_ENABLED=true RERANK_CANDIDATES=12; "
            f"got enabled={config.RERANK_ENABLED} candidates={config.RERANK_CANDIDATES}"
        )

    started_at = time.strftime("%Y-%m-%dT%H:%M:%S")
    store = _get_store(config.EMBEDDING_MODE)
    _, first_init_ms = _time_ms(_load_model)
    part_c = experiment_c(store, warm)
    part_c["cold_or_cached_init_ms"] = first_init_ms
    part_a = experiment_a(store, warm)
    part_b = experiment_b(store)
    part_b_lat = experiment_b_latency(store, warm)
    return {
        "suite": "performance_phase5_rerank_experiment",
        "phase": "offline_comparison",
        "started_at": started_at,
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "environment": _environment(),
        "checkpoint": {
            "baseline_isolated_rerank_n": 5,
            "baseline_isolated_rerank_is_not_pipeline_latency": True,
            "production_fetch_k": "max(TOP_K, RERANK_CANDIDATES) = 12",
            "production_scores_all_fetched": True,
            "rerank_is_in_memory_only": True,
            "can_repeat_without_changing_results_or_indexes": True,
        },
        "experiment_a": part_a,
        "experiment_b": part_b,
        "experiment_b_latency": part_b_lat,
        "experiment_c": part_c,
        "phase3_phase4_commands_after_any_future_change": [
            r".\venv\Scripts\python.exe evaluation/evaluate_answer_quality.py --out evaluation/results/answer_quality_after.json",
            r".\venv\Scripts\python.exe evaluation/evaluate_conversation_phase4.py --out evaluation/results/conversation_phase4_after.json",
            r".\venv\Scripts\python.exe evaluation/evaluate_kb_phase2.py --out evaluation/results/kb_phase2_after.json",
        ],
        "limitations": [
            "Rerank timings exclude embed, Chroma, FastAPI, SSE, and the browser.",
            "p95 with n=30 is interpolated and not a precise tail estimate.",
            "Candidate-count quality uses the first N of one 12-hit Chroma fetch, matching what production would score if RERANK_CANDIDATES were N.",
            "Phase 3 and Phase 4 suites were not run in this increment.",
            "Production retrieval behavior was not changed.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warm", type=int, default=DEFAULT_WARM)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    if args.warm < 1:
        raise SystemExit("--warm must be >= 1")
    os.environ["LLM_PROVIDER"] = "mock"
    result = evaluate(warm=args.warm)
    summary = {key: result[key] for key in result if key not in {"experiment_b"}}
    summary["experiment_b_metrics"] = {
        n: {
            "recall@1": row["recall@1"],
            "recall@4": row["recall@4"],
            "mrr": row["mrr"],
            "pool_loss_queries": row["pool_loss_queries"],
            "ranking_diff_queries_vs_12": row["ranking_diff_queries_vs_12"],
            "new_misses_vs_12": row["new_misses_vs_12"],
        }
        for n, row in result["experiment_b"]["by_candidate_count"].items()
    }
    summary["experiment_b_vector_ref"] = result["experiment_b"]["reference_vector_top4_no_rerank"]
    summary["experiment_b_isolation"] = result["experiment_b"]["isolation"]
    summary["experiment_b_safety"] = result["experiment_b"]["safety_independent_of_rerank"]
    print(json.dumps(summary, indent=2))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
