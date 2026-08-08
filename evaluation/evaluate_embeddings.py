"""
Objective 3: quantitatively compare general-purpose sentence embeddings
(all-MiniLM-L6-v2) against domain-specific medical embeddings (PubMedBERT,
via pritamdeka/S-PubMedBert-MS-MARCO) on retrieval accuracy.

For every labeled query in evaluation/datasets/symptom_condition_testset.csv
we check whether the correct document appears in the top-k results (Hit
Rate / Recall@k) and how highly it is ranked (Mean Reciprocal Rank).

Usage:
    python evaluation/evaluate_embeddings.py [--k 1 3 5]

Requires both indexes to already be built:
    python scripts/build_index.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src import config
from src.retrieval.vector_store import VectorStore


def load_testset() -> pd.DataFrame:
    return pd.read_csv(config.EVAL_DATASETS_DIR / "symptom_condition_testset.csv")


def evaluate_mode(mode: str, df: pd.DataFrame, k_values: list[int]) -> dict:
    store = VectorStore(mode)
    max_k = max(k_values)

    hits_at_k = {k: 0 for k in k_values}
    reciprocal_ranks = []
    per_query_rows = []

    for _, row in df.iterrows():
        query = row["query"]
        expected_doc_id = row["expected_doc_id"]

        results = store.search(query, top_k=max_k)
        retrieved_doc_ids = [r.metadata["doc_id"] for r in results]

        rank = None
        if expected_doc_id in retrieved_doc_ids:
            rank = retrieved_doc_ids.index(expected_doc_id) + 1  # 1-indexed

        for k in k_values:
            if rank is not None and rank <= k:
                hits_at_k[k] += 1

        reciprocal_ranks.append(1.0 / rank if rank else 0.0)
        per_query_rows.append(
            {
                "query": query,
                "expected_doc_id": expected_doc_id,
                "rank_of_correct_doc": rank if rank else f">{max_k}",
                "top1_doc_id": retrieved_doc_ids[0] if retrieved_doc_ids else None,
            }
        )

    n = len(df)
    metrics = {f"recall@{k}": hits_at_k[k] / n for k in k_values}
    metrics["mrr"] = sum(reciprocal_ranks) / n
    return {"metrics": metrics, "per_query": per_query_rows}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", nargs="+", type=int, default=[1, 3, 5])
    args = parser.parse_args()

    df = load_testset()
    print(f"Loaded {len(df)} labeled test queries\n")

    all_results = {}
    for mode in ["general", "medical"]:
        print(f"Evaluating '{mode}' embeddings ({config.GENERAL_EMBEDDING_MODEL if mode == 'general' else config.MEDICAL_EMBEDDING_MODEL})...")
        result = evaluate_mode(mode, df, args.k)
        all_results[mode] = result

    # ---- Print comparison table ----
    print("\n=== Retrieval accuracy: general vs. medical embeddings (Objective 3) ===\n")
    header = ["Metric", "General (MiniLM)", "Medical (PubMedBERT)", "Delta (medical - general)"]
    rows = []
    for k in args.k:
        g = all_results["general"]["metrics"][f"recall@{k}"]
        m = all_results["medical"]["metrics"][f"recall@{k}"]
        rows.append([f"Recall@{k}", f"{g:.2%}", f"{m:.2%}", f"{(m - g):+.2%}"])
    g_mrr = all_results["general"]["metrics"]["mrr"]
    m_mrr = all_results["medical"]["metrics"]["mrr"]
    rows.append(["MRR", f"{g_mrr:.3f}", f"{m_mrr:.3f}", f"{(m_mrr - g_mrr):+.3f}"])

    try:
        from tabulate import tabulate

        print(tabulate(rows, headers=header, tablefmt="github"))
    except ImportError:
        print(header)
        for r in rows:
            print(r)

    # ---- Save detailed per-query results ----
    out_dir = config.EVAL_RESULTS_DIR
    for mode in ["general", "medical"]:
        pd.DataFrame(all_results[mode]["per_query"]).to_csv(
            out_dir / f"embedding_eval_{mode}.csv", index=False
        )
    print(f"\nDetailed per-query results saved to {out_dir}")


if __name__ == "__main__":
    main()
