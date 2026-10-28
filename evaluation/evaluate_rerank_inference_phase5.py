"""Phase 5 isolated cross-encoder inference experiment.

Keeps all 12 candidates. Does not change production reranker, config,
embeddings, thresholds, or indexes. Does not overwrite earlier baselines.

Usage:
    .\\venv\\Scripts\\python.exe evaluation/evaluate_rerank_inference_phase5.py --out evaluation/results/performance_phase5_rerank_inference.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import platform
import statistics
import sys
import time
from contextlib import contextmanager
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))
sys.path.insert(0, str(ROOT_DIR / "evaluation" / "datasets"))

DEFAULT_WARM = 30
FIXED_QUERIES = [
    {"id": "ra_short", "query": "pain"},
    {"id": "ra_medium", "query": "I have a dry cough at night"},
    {"id": "ra_knee", "query": "Why does my knee hurt when I climb stairs?"},
    {
        "id": "ra_long",
        "query": "I have a swollen painful calf after a long flight and now I feel breathless",
    },
    {
        "id": "ra_emergency",
        "query": "I have severe crushing chest pain spreading to my jaw",
    },
]
WATCH_IDS = ("c06", "d19")


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


def _time_both(fn):
    wall0 = time.perf_counter()
    cpu0 = time.process_time()
    result = fn()
    return result, round((time.perf_counter() - wall0) * 1000, 3), round((time.process_time() - cpu0) * 1000, 3)


def _doc_ids(chunks) -> list[str]:
    return [str((chunk.metadata or {}).get("doc_id") or "") for chunk in chunks]


def _first_rank(retrieved: list[str], expected: list[str]) -> int | None:
    for index, doc_id in enumerate(retrieved, start=1):
        if doc_id in expected:
            return index
    return None


@contextmanager
def _thread_settings(intra: int, interop: int | None = None):
    import torch

    prev_intra = torch.get_num_threads()
    prev_interop = torch.get_num_interop_threads()
    torch.set_num_threads(intra)
    if interop is not None:
        try:
            torch.set_num_interop_threads(interop)
        except RuntimeError:
            interop = prev_interop
    try:
        yield {"intra": torch.get_num_threads(), "interop": torch.get_num_interop_threads(), "requested_interop": interop}
    finally:
        torch.set_num_threads(prev_intra)


def _inspect() -> dict:
    import torch
    from sentence_transformers import CrossEncoder
    from src.retrieval.reranker import _load_model, _device

    model = _load_model()
    extras = {}
    try:
        import onnxruntime

        extras["onnxruntime"] = onnxruntime.__version__
    except Exception:
        extras["onnxruntime"] = None
    try:
        import optimum

        extras["optimum"] = optimum.__version__
    except Exception:
        extras["optimum"] = None
    extras["psutil"] = None
    try:
        import psutil

        extras["psutil"] = psutil.__version__
    except Exception:
        pass
    return {
        "python": platform.python_version(),
        "os": f"{platform.system()} {platform.release()}",
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "torch": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "device": _device(),
        "default_num_threads": torch.get_num_threads(),
        "default_num_interop_threads": torch.get_num_interop_threads(),
        "mkl": bool(getattr(torch.backends, "mkldnn", None) and torch.backends.mkldnn.is_available()),
        "openmp": bool(getattr(torch.backends, "openmp", None) and torch.backends.openmp.is_available()),
        "sentence_transformers": __import__("sentence_transformers").__version__,
        "transformers": __import__("transformers").__version__,
        "cross_encoder_class": CrossEncoder.__name__,
        "model_max_length": model.tokenizer.model_max_length,
        "cross_encoder_max_length": model.max_length,
        "param_dtype": str(next(model.model.parameters()).dtype),
        "predict_already_uses_no_grad": True,
        "default_predict_batch_size": 32,
        "production_rerank_candidates": 12,
        "production_code_changed": False,
        **extras,
    }


def _token_stats(model, query: str, chunks) -> dict:
    lengths = []
    for chunk in chunks:
        encoded = model.tokenizer(
            query,
            chunk.text,
            truncation="longest_first",
            max_length=model.tokenizer.model_max_length,
        )
        lengths.append(len(encoded["input_ids"]))
    return {
        "n": len(lengths),
        "min": min(lengths) if lengths else None,
        "median": _percentile([float(item) for item in lengths], 50),
        "max": max(lengths) if lengths else None,
        "lengths": lengths,
    }


def _predict(model, pairs, batch_size: int, use_inference_mode: bool):
    import torch

    def _run():
        return model.predict(pairs, batch_size=batch_size, show_progress_bar=False)

    if use_inference_mode:
        with torch.inference_mode():
            return _run()
    return _run()


def _rerank(query: str, chunks, scores):
    from src.retrieval.vector_store import RetrievedChunk

    ranked = sorted(zip(chunks, scores), key=lambda item: float(item[1]), reverse=True)
    reranked = []
    for chunk, score in ranked:
        relevance = 1.0 / (1.0 + math.exp(-float(score)))
        vector_score = (
            float(chunk.vector_score)
            if chunk.vector_score is not None
            else max(0.0, 1.0 - float(chunk.distance))
        )
        reranked.append(
            RetrievedChunk(
                chunk_id=chunk.chunk_id,
                text=chunk.text,
                distance=1.0 - relevance,
                metadata=chunk.metadata,
                rerank_score=relevance,
                vector_score=vector_score,
            )
        )
    return reranked


def _time_config(model, pairs, chunks, query: str, config: dict, warm: int, include_search=None) -> dict:
    import torch

    intra = config.get("threads", torch.get_num_threads())
    interop = config.get("interop")
    batch_size = config.get("batch_size", 32)
    inference_mode = bool(config.get("inference_mode", False))
    with _thread_settings(intra, interop) as applied:
        _predict(model, pairs, batch_size, inference_mode)
        rerank_wall, rerank_cpu = [], []
        retrieve_wall, retrieve_cpu = [], []
        last_top4 = None
        for _ in range(warm):
            scores, wall, cpu = _time_both(lambda: _predict(model, pairs, batch_size, inference_mode))
            rerank_wall.append(wall)
            rerank_cpu.append(cpu)
            last_top4 = _doc_ids(_rerank(query, chunks, scores)[:4])
            if include_search is not None:
                def _retrieve():
                    found = include_search()
                    pred = _predict(model, [(query, chunk.text) for chunk in found], batch_size, inference_mode)
                    return _rerank(query, found, pred)

                _, wall, cpu = _time_both(_retrieve)
                retrieve_wall.append(wall)
                retrieve_cpu.append(cpu)
        return {
            "id": config["id"],
            "threads_requested": intra,
            "threads_applied": applied,
            "batch_size": batch_size,
            "inference_mode": inference_mode,
            "candidate_count": len(pairs),
            "rerank_wall_ms": _stats(rerank_wall),
            "rerank_cpu_ms": _stats(rerank_cpu),
            "retrieve_wall_ms": _stats(retrieve_wall) if include_search is not None else None,
            "retrieve_cpu_ms": _stats(retrieve_cpu) if include_search is not None else None,
            "last_top4": last_top4,
        }


def _score_quality(store, model, config: dict) -> dict:
    from kb_phase2_queries import retrieval_queries
    from src.pipeline.conversation_state import build_conversation_state
    from src.retrieval.reranker import rerank_chunks

    intra = config.get("threads")
    batch_size = config.get("batch_size", 32)
    inference_mode = bool(config.get("inference_mode", False))
    rows = retrieval_queries()
    hits1 = hits4 = 0
    reciprocal = 0.0
    diffs = []
    watch = {}
    with _thread_settings(intra or __import__("torch").get_num_threads()):
        for row in rows:
            expected = list(row.get("expected_doc_ids") or [])
            search = build_conversation_state(row["query"]).search_query
            pool = store.search(search, top_k=12)
            baseline = rerank_chunks(search, pool, top_k=len(pool))
            pairs = [(search, chunk.text) for chunk in pool]
            scores = _predict(model, pairs, batch_size, inference_mode)
            variant = _rerank(search, pool, scores)
            base_top4 = _doc_ids(baseline[:4])
            var_top4 = _doc_ids(variant[:4])
            rank = _first_rank(var_top4, expected)
            if rank == 1:
                hits1 += 1
            if rank is not None and rank <= 4:
                hits4 += 1
                reciprocal += 1.0 / rank
            if base_top4 != var_top4:
                diffs.append({"id": row["id"], "query": row["query"], "baseline": base_top4, "variant": var_top4})
            if row["id"] in WATCH_IDS:
                watch[row["id"]] = {
                    "query": row["query"],
                    "expected": expected,
                    "baseline_top4": base_top4,
                    "variant_top4": var_top4,
                    "rank": rank,
                    "hit4": rank is not None and rank <= 4,
                }
    n = len(rows) or 1
    return {
        "config_id": config["id"],
        "retrieval_n": n,
        "recall@1": hits1 / n,
        "recall@4": hits4 / n,
        "mrr": reciprocal / n,
        "hits1": hits1,
        "hits4": hits4,
        "top4_diffs_vs_production_rerank_chunks": len(diffs),
        "representative_diffs": diffs[:15],
        "all_diffs": diffs,
        "watch_c06_d19": watch,
    }


def evaluate(warm: int) -> dict:
    import torch
    from src import config
    from src.retrieval.reranker import _load_model
    from src.retrieval.retriever import _get_store

    if config.RERANK_CANDIDATES != 12 or not config.RERANK_ENABLED:
        raise SystemExit("Production defaults must remain RERANK_ENABLED=true and RERANK_CANDIDATES=12")

    started_at = time.strftime("%Y-%m-%dT%H:%M:%S")
    inspect = _inspect()
    store = _get_store(config.EMBEDDING_MODE)
    model = _load_model()

    frozen = []
    for item in FIXED_QUERIES:
        chunks = store.search(item["query"], top_k=12)
        frozen.append(
            {
                **item,
                "chunks": chunks,
                "pairs": [(item["query"], chunk.text) for chunk in chunks],
                "tokens": _token_stats(model, item["query"], chunks),
            }
        )

    screen_query = next(item for item in frozen if item["id"] == "ra_knee")
    screen_configs = [
        {"id": "default", "threads": inspect["default_num_threads"], "batch_size": 32, "inference_mode": False},
        {"id": "threads_1", "threads": 1, "batch_size": 32, "inference_mode": False},
        {"id": "threads_2", "threads": 2, "batch_size": 32, "inference_mode": False},
        {"id": "threads_4", "threads": 4, "batch_size": 32, "inference_mode": False},
        {"id": "threads_16", "threads": 16, "batch_size": 32, "inference_mode": False},
        {"id": "interop_1", "threads": inspect["default_num_threads"], "interop": 1, "batch_size": 32, "inference_mode": False},
        {"id": "batch_1", "threads": inspect["default_num_threads"], "batch_size": 1, "inference_mode": False},
        {"id": "batch_4", "threads": inspect["default_num_threads"], "batch_size": 4, "inference_mode": False},
        {"id": "batch_12", "threads": inspect["default_num_threads"], "batch_size": 12, "inference_mode": False},
        {"id": "inference_mode", "threads": inspect["default_num_threads"], "batch_size": 32, "inference_mode": True},
    ]

    screen = []
    for cfg in screen_configs:
        screen.append(
            _time_config(
                model,
                screen_query["pairs"],
                screen_query["chunks"],
                screen_query["query"],
                cfg,
                warm,
            )
        )

    default_median = next(item["rerank_wall_ms"]["median"] for item in screen if item["id"] == "default")
    ranked = sorted(
        [item for item in screen if item["rerank_wall_ms"]["median"] is not None],
        key=lambda item: item["rerank_wall_ms"]["median"],
    )
    confirm_ids = ["default"]
    for item in ranked:
        if item["id"] not in confirm_ids:
            confirm_ids.append(item["id"])
        if len(confirm_ids) == 3:
            break
    confirm_configs = [cfg for cfg in screen_configs if cfg["id"] in confirm_ids]

    confirmed = []
    for item in frozen:
        row = {"id": item["id"], "query": item["query"], "tokens": item["tokens"], "variants": []}
        for cfg in confirm_configs:
            row["variants"].append(
                _time_config(
                    model,
                    item["pairs"],
                    item["chunks"],
                    item["query"],
                    cfg,
                    warm,
                    include_search=lambda q=item["query"]: store.search(q, top_k=12),
                )
            )
        confirmed.append(row)

    quality = []
    for cfg in confirm_configs:
        quality.append(_score_quality(store, model, cfg))

    return {
        "suite": "performance_phase5_rerank_inference",
        "phase": "offline_inference_comparison",
        "started_at": started_at,
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "plan": {
            "kept_fixed": [
                "RERANK_ENABLED=true",
                "RERANK_CANDIDATES=12",
                "cross-encoder/ms-marco-MiniLM-L-6-v2",
                "MiniLM embeddings and Chroma index",
                "thresholds",
                "same 12-candidate pools and pair order",
            ],
            "screened": [cfg["id"] for cfg in screen_configs],
            "not_assumed_faster": ["more threads", "CUDA (unavailable)", "ONNX without Optimum"],
            "excluded": ["answer caching", "user-specific medical-response caching", "candidate-count reduction"],
        },
        "inspect": inspect,
        "frozen_token_stats": {item["id"]: item["tokens"] for item in frozen},
        "screen_query": screen_query["query"],
        "screen": screen,
        "default_screen_median_ms": default_median,
        "confirm_ids": confirm_ids,
        "confirmed": confirmed,
        "quality": quality,
        "limitations": [
            "Isolated experiment; production reranker.py was not modified.",
            "p95 with n=30 is indicative.",
            "Thread changes apply only inside this process.",
            "Phase 3 and Phase 4 were not rerun.",
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
    summary = {
        key: result[key]
        for key in result
        if key not in {"confirmed", "quality"}
    }
    summary["screen_medians_ms"] = {
        item["id"]: {
            "rerank_median": item["rerank_wall_ms"]["median"],
            "rerank_p95": item["rerank_wall_ms"]["p95"],
            "cpu_median": item["rerank_cpu_ms"]["median"],
            "top4": item["last_top4"],
        }
        for item in result["screen"]
    }
    summary["confirm_quality"] = [
        {
            "id": item["config_id"],
            "recall@1": item["recall@1"],
            "recall@4": item["recall@4"],
            "mrr": item["mrr"],
            "top4_diffs": item["top4_diffs_vs_production_rerank_chunks"],
            "watch": item["watch_c06_d19"],
        }
        for item in result["quality"]
    ]
    summary["confirm_latency"] = {
        row["id"]: {
            variant["id"]: {
                "rerank_median": variant["rerank_wall_ms"]["median"],
                "retrieve_median": (variant["retrieve_wall_ms"] or {}).get("median"),
            }
            for variant in row["variants"]
        }
        for row in result["confirmed"]
    }
    print(json.dumps(summary, indent=2))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
