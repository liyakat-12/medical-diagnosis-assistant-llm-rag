"""
Evaluates the rule-based emergency-detection safety layer (src.safety.guardrails)
against a labeled test set of emergency / non-emergency symptom descriptions.

This is the most important safety metric in the whole project: a false
negative here means a real emergency was NOT flagged. We therefore report
recall (sensitivity) on the emergency class front and center, not just
overall accuracy.

Usage:
    python evaluation/evaluate_triage.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import confusion_matrix, precision_score, recall_score, f1_score

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src import config
from src.safety.guardrails import check_emergency


def main() -> None:
    df = pd.read_csv(config.EVAL_DATASETS_DIR / "emergency_test_set.csv")
    print(f"Loaded {len(df)} labeled emergency/non-emergency examples\n")

    predictions = []
    matched_terms_col = []
    for text in df["text"]:
        result = check_emergency(text)
        predictions.append(int(result.triggered))
        matched_terms_col.append("; ".join(result.matched_terms))

    df["predicted_is_emergency"] = predictions
    df["matched_terms"] = matched_terms_col

    y_true = df["is_emergency"].tolist()
    y_pred = df["predicted_is_emergency"].tolist()

    recall = recall_score(y_true, y_pred, zero_division=0)  # sensitivity on emergencies - THE key metric
    precision = precision_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

    print("=== Emergency safety-layer evaluation ===\n")
    print(f"Recall (sensitivity) on true emergencies : {recall:.2%}  <-- most critical metric")
    print(f"Precision                                : {precision:.2%}")
    print(f"F1 score                                  : {f1:.3f}")
    print(f"\nConfusion matrix:")
    print(f"  True Positives  (caught emergencies)     : {tp}")
    print(f"  False Negatives (MISSED emergencies)     : {fn}  <-- should be 0 or as close as possible")
    print(f"  True Negatives  (correctly not flagged)  : {tn}")
    print(f"  False Positives (over-cautious flags)    : {fp}")

    if fn > 0:
        print("\nMissed emergency cases (false negatives) - review these for new red-flag patterns to add:")
        missed = df[(df["is_emergency"] == 1) & (df["predicted_is_emergency"] == 0)]
        for _, row in missed.iterrows():
            print(f"  - {row['text']!r}")

    out_path = config.EVAL_RESULTS_DIR / "triage_eval.csv"
    df.to_csv(out_path, index=False)
    print(f"\nFull results saved to {out_path}")


if __name__ == "__main__":
    main()
