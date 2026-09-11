"""
End-to-end evaluation of the full pipeline's condition suggestions
(addresses the gap flagged during project scoping: Objectives 3-4 test
components in isolation, but nothing checks the final answer quality).

For each labeled query in symptom_condition_testset.csv, we check whether
the expected condition's title appears anywhere in the generated answer
text (top-k "mentioned accuracy"), and whether the triage level assigned
matches the expected triage level.

Usage:
    python evaluation/evaluate_e2e.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from src import config
from src.pipeline.rag_pipeline import run_pipeline


def main() -> None:
    df = pd.read_csv(config.EVAL_DATASETS_DIR / "symptom_condition_testset.csv")
    print(f"Loaded {len(df)} labeled queries\n")

    rows = []
    condition_mentioned_count = 0
    triage_match_count = 0

    for _, row in df.iterrows():
        query = row["query"]
        expected_condition = row["expected_condition"]
        expected_triage = row["expected_triage_level"]

        result = run_pipeline(query)

        condition_mentioned = expected_condition.lower() in result.answer.lower() or any(
            expected_condition.lower() in c["condition"].lower() for c in result.citations
        )
        triage_match = (result.triage.level == expected_triage) if result.triage else False

        condition_mentioned_count += int(condition_mentioned)
        triage_match_count += int(triage_match)

        rows.append(
            {
                "query": query,
                "expected_condition": expected_condition,
                "expected_triage": expected_triage,
                "predicted_triage": result.triage.level if result.triage else None,
                "condition_mentioned_or_cited": condition_mentioned,
                "triage_correct": triage_match,
                "answer": result.answer,
            }
        )

    n = len(df)
    print("=== End-to-end pipeline evaluation ===\n")
    print(f"Condition correctly surfaced (cited or in answer): {condition_mentioned_count}/{n} ({condition_mentioned_count/n:.2%})")
    print(f"Triage level exactly correct                     : {triage_match_count}/{n} ({triage_match_count/n:.2%})")

    out_path = config.EVAL_RESULTS_DIR / "e2e_eval.csv"
    pd.DataFrame(rows).to_csv(out_path, index=False)
    print(f"\nFull per-query results saved to {out_path}")


if __name__ == "__main__":
    main()
