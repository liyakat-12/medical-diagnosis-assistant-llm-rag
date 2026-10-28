"""Phase 5 in-process performance benchmark.

Measures cold-start and warm pipeline latency. Does not change application
code and does not score Phase 3 / Phase 4 quality.

This is not an end-to-end API or browser benchmark.

Usage:
    python evaluation/evaluate_performance.py
    python evaluation/evaluate_performance.py --warm 25 --out evaluation/results/performance_phase5_baseline.json
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
import time
import traceback
import tracemalloc
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))
sys.path.insert(0, str(ROOT_DIR / "evaluation" / "datasets"))

DEFAULT_WARM = 25


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


def _rss_mb() -> float | None:
    try:
        import psutil

        return round(psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024), 2)
    except Exception:
        return None


def _memory_snapshot(label: str, traced: int | None = None) -> dict:
    return {
        "label": label,
        "rss_mb": _rss_mb(),
        "tracemalloc_current_mb": None if traced is None else round(traced / (1024 * 1024), 2),
        "rss_available": _rss_mb() is not None,
    }


def _environment() -> dict:
    from src import config

    uname = platform.uname()
    rss_total = None
    try:
        import psutil

        rss_total = round(psutil.virtual_memory().total / (1024 * 1024), 1)
    except Exception:
        rss_total = None
    return {
        "os": f"{uname.system} {uname.release}",
        "machine": uname.machine,
        "processor": uname.processor,
        "python": platform.python_version(),
        "cpu_count": os.cpu_count(),
        "ram_mb": rss_total,
        "llm_provider_requested": config.LLM_PROVIDER,
        "llm_provider_resolved": config.resolve_llm_provider(),
        "embedding_mode": config.EMBEDDING_MODE,
        "general_embedding_model": config.GENERAL_EMBEDDING_MODEL,
        "rerank_enabled": config.RERANK_ENABLED,
        "rerank_model": config.RERANK_MODEL,
        "rerank_candidates": config.RERANK_CANDIDATES,
        "top_k": config.TOP_K,
        "min_relevance_score": config.MIN_RELEVANCE_SCORE,
        "min_vector_score": config.MIN_VECTOR_SCORE,
        "llm_kb_fallback": config.LLM_KB_FALLBACK,
        "chat_history_window": config.CHAT_HISTORY_WINDOW,
        "layer": "in_process_pipeline",
        "excluded": [
            "FastAPI HTTP stack",
            "MongoDB / auth / JWT",
            "SSE queue and network transport",
            "browser rendering and ChatContext",
            "live LLM provider network (unless --live is used and a key is present)",
        ],
    }


def _time_ms(fn):
    started = time.perf_counter()
    result = fn()
    return result, round((time.perf_counter() - started) * 1000, 3)


def _cold_start() -> dict:
    from src import config
    from src.embeddings.embedding_models import get_embedding_model
    from src.pipeline.rag_pipeline import run_pipeline
    from src.retrieval.reranker import _load_model, rerank_chunks
    from src.retrieval.retriever import _get_store

    probe = "headache"
    cold: dict = {}

    model, cold["embed_model_load_ms"] = _time_ms(lambda: get_embedding_model(config.EMBEDDING_MODE))
    _vec, cold["first_query_embed_ms"] = _time_ms(lambda: model.encode_one(probe))

    store, cold["chroma_open_ms"] = _time_ms(lambda: _get_store(config.EMBEDDING_MODE))

    def chroma_only():
        return store.collection.query(query_embeddings=[_vec.tolist()], n_results=max(config.TOP_K, config.RERANK_CANDIDATES))

    _, cold["first_chroma_query_ms"] = _time_ms(chroma_only)
    chunks, cold["first_vector_search_ms"] = _time_ms(lambda: store.search(probe, top_k=max(config.TOP_K, config.RERANK_CANDIDATES)))
    if config.RERANK_ENABLED:
        _, cold["rerank_model_load_ms"] = _time_ms(_load_model)
        _, cold["first_rerank_ms"] = _time_ms(lambda: rerank_chunks(probe, chunks, top_k=len(chunks)))
    else:
        cold["rerank_model_load_ms"] = None
        cold["first_rerank_ms"] = None

    result, cold["first_pipeline_ms"] = _time_ms(lambda: run_pipeline(probe))
    cold["first_pipeline_stage_ms"] = dict(result.timings or {})
    cold["first_pipeline_origin"] = result.evidence_origin
    return cold


def _time_stream(query: str, history: list[dict] | None) -> dict:
    from src.pipeline.rag_pipeline import iter_pipeline_stream

    started = time.perf_counter()
    first_token_ms = None
    done_result = None
    token_events = 0
    for event in iter_pipeline_stream(query, chat_history=history):
        kind = event.get("type")
        if kind == "token" and first_token_ms is None:
            first_token_ms = round((time.perf_counter() - started) * 1000, 3)
        if kind == "token":
            token_events += 1
        if kind == "done":
            done_result = event.get("result") or {}
    wall_ms = round((time.perf_counter() - started) * 1000, 3)
    timings = (done_result or {}).get("timings") or {}
    return {
        "wall_ms": wall_ms,
        "first_token_ms": first_token_ms,
        "stream_complete_ms": wall_ms,
        "token_events": token_events,
        "classify_ms": timings.get("classify_ms"),
        "retrieve_ms": timings.get("retrieve_ms"),
        "generate_ms": timings.get("generate_ms"),
        "pipeline_total_ms": timings.get("total_ms"),
        "origin": (done_result or {}).get("evidence_origin"),
        "triage": ((done_result or {}).get("triage") or {}).get("level") if done_result else None,
        "refused": bool((done_result or {}).get("refused")),
    }


def _warm_stage_sample(query: str) -> dict:
    from src import config
    from src.embeddings.embedding_models import get_embedding_model
    from src.retrieval.reranker import rerank_chunks
    from src.retrieval.retriever import _get_store

    model = get_embedding_model(config.EMBEDDING_MODE)
    store = _get_store(config.EMBEDDING_MODE)
    vec, embed_ms = _time_ms(lambda: model.encode_one(query))
    _, chroma_ms = _time_ms(
        lambda: store.collection.query(
            query_embeddings=[vec.tolist()],
            n_results=max(config.TOP_K, config.RERANK_CANDIDATES),
        )
    )
    chunks, search_ms = _time_ms(lambda: store.search(query, top_k=max(config.TOP_K, config.RERANK_CANDIDATES)))
    rerank_ms = None
    if config.RERANK_ENABLED and chunks:
        _, rerank_ms = _time_ms(lambda: rerank_chunks(query, chunks, top_k=len(chunks)))
    return {
        "query_embed_ms": embed_ms,
        "chroma_query_ms": chroma_ms,
        "vector_search_includes_embed_ms": search_ms,
        "rerank_ms": rerank_ms,
    }


def evaluate(warm: int, live: bool) -> dict:
    from performance_phase5 import SCENARIOS, dump_jsonl
    from src import config

    resolved = config.resolve_llm_provider()
    if live and resolved == "mock":
        raise SystemExit("--live requested but resolve_llm_provider() is mock (missing or placeholder key).")
    if not live and resolved != "mock":
        raise SystemExit(
            f"Baseline lane is mock-only; resolved provider is {resolved!r}. "
            "Re-run without a live LLM_PROVIDER or pass --live for a separate file."
        )

    dump_jsonl(ROOT_DIR / "evaluation" / "datasets" / "performance_phase5.jsonl")
    tracemalloc.start()
    warnings: list[str] = []
    started_at = time.strftime("%Y-%m-%dT%H:%M:%S")

    import_started = time.perf_counter()
    from src.pipeline.rag_pipeline import run_pipeline  # noqa: F401

    import_ms = round((time.perf_counter() - import_started) * 1000, 3)

    memory_before = _memory_snapshot("before_model_load", tracemalloc.get_traced_memory()[0])
    cold = _cold_start()
    cold["import_ms"] = import_ms
    memory_after_cold = _memory_snapshot("after_cold_start", tracemalloc.get_traced_memory()[0])

    scenarios_out = []
    for row in SCENARIOS:
        samples = []
        stage_samples = []
        errors = []
        for index in range(warm):
            try:
                samples.append(_time_stream(row["query"], row.get("history")))
            except Exception as exc:
                errors.append({"index": index, "error_type": type(exc).__name__, "detail": str(exc)[:200]})
                warnings.append(f"{row['id']} warm[{index}] {type(exc).__name__}")
        if row["category"] not in {"general_chat", "safety_refusal"}:
            for index in range(min(5, max(warm, 1))):
                try:
                    stage_samples.append(_warm_stage_sample(row["query"]))
                except Exception as exc:
                    warnings.append(f"{row['id']} stage[{index}] {type(exc).__name__}: {exc}")
        def column(name: str) -> list[float]:
            return [item[name] for item in samples if item.get(name) is not None]

        stage_stats = {
            key: _stats([item[key] for item in stage_samples if item.get(key) is not None])
            for key in ("query_embed_ms", "chroma_query_ms", "vector_search_includes_embed_ms", "rerank_ms")
        }
        scenarios_out.append(
            {
                "id": row["id"],
                "category": row["category"],
                "query": row["query"],
                "has_history": bool(row.get("history")),
                "notes": row.get("notes") or "",
                "warm_n_requested": warm,
                "warm_n_ok": len(samples),
                "errors": errors,
                "last_origin": samples[-1]["origin"] if samples else None,
                "last_triage": samples[-1]["triage"] if samples else None,
                "last_refused": samples[-1]["refused"] if samples else None,
                "wall_ms": _stats(column("wall_ms")),
                "first_token_ms": _stats(column("first_token_ms")),
                "stream_complete_ms": _stats(column("stream_complete_ms")),
                "classify_ms": _stats(column("classify_ms")),
                "retrieve_ms": _stats(column("retrieve_ms")),
                "generate_ms": _stats(column("generate_ms")),
                "pipeline_total_ms": _stats(column("pipeline_total_ms")),
                "stage_samples_n": len(stage_samples),
                "stage_ms": stage_stats,
            }
        )

    memory_after = _memory_snapshot("after_warm_runs", tracemalloc.get_traced_memory()[0])
    tracemalloc.stop()

    by_category: dict[str, dict] = {}
    for item in scenarios_out:
        bucket = by_category.setdefault(item["category"], {"scenario_ids": [], "wall_ms_medians": []})
        bucket["scenario_ids"].append(item["id"])
        if item["wall_ms"]["median"] is not None:
            bucket["wall_ms_medians"].append(item["wall_ms"]["median"])
    for key, bucket in by_category.items():
        bucket["median_of_scenario_medians_ms"] = _percentile(bucket["wall_ms_medians"], 50)

    return {
        "suite": "performance_phase5",
        "phase": "baseline",
        "started_at": started_at,
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "environment": _environment(),
        "warm_repeats_requested": warm,
        "live_provider": live,
        "provider_lane": "live" if live else "mock",
        "method": (
            "In-process iter_pipeline_stream timings after isolated cold model loads. "
            "first_pipeline_ms is the first assembled pipeline after those loads, so models are already cached. "
            "Warm p95 uses linear interpolation on the measured sample; with n<100 it is indicative. "
            "Mock LLM first-token is local generation plus word yield, not a network TTFB. "
            "Stage embed/chroma/rerank probes run after the warm stream loop and do not change those n timings. "
            "This is not clinical validation and not an API/browser benchmark."
        ),
        "cold_start": cold,
        "memory": {
            "before_model_load": memory_before,
            "after_cold_start": memory_after_cold,
            "after_warm_runs": memory_after,
            "limitation": (
                "RSS requires psutil. tracemalloc only tracks Python allocations, "
                "not native MiniLM / Chroma / torch heaps."
            ),
        },
        "by_category": by_category,
        "scenarios": scenarios_out,
        "warnings": warnings,
        "limitations": [
            "Default LLM_PROVIDER=mock: generate/first-token numbers are not Groq/OpenAI latency.",
            "FastAPI, Mongo, cookies, SSE transport, and the React client are excluded.",
            "p95 with 25 samples is interpolated and not a precise tail estimate.",
            "Cold-start is one process-local sample.",
            "Stage embed/chroma/rerank samples are 5 extra probes per retrieving scenario, not 25.",
            "No application code, embeddings, thresholds, or indexes were changed for this baseline.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warm", type=int, default=DEFAULT_WARM)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Use the configured non-mock provider. Default is mock-only.",
    )
    args = parser.parse_args()
    if args.warm < 1:
        raise SystemExit("--warm must be >= 1")
    if not args.live:
        os.environ["LLM_PROVIDER"] = "mock"
    try:
        result = evaluate(warm=args.warm, live=args.live)
    except Exception:
        traceback.print_exc()
        raise
    summary = {
        key: result[key]
        for key in result
        if key not in {"scenarios"}
    }
    summary["scenario_medians_ms"] = {
        item["id"]: {
            "category": item["category"],
            "n": item["warm_n_ok"],
            "wall_median": item["wall_ms"]["median"],
            "wall_p95": item["wall_ms"]["p95"],
            "first_token_median": item["first_token_ms"]["median"],
            "retrieve_median": item["retrieve_ms"]["median"],
            "generate_median": item["generate_ms"]["median"],
        }
        for item in result["scenarios"]
    }
    print(json.dumps(summary, indent=2))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
