"""
Objective 4: measure the reduction in hallucination achieved by grounding
the model in retrieved documents (RAG) versus the same LLM answering with
no retrieval at all.

We report two complementary metrics for each question:

1. Citation coverage (automatic, no LLM needed): the fraction of
   condition-like claims in the RAG answer that carry a "(Source: ...)"
   citation. The no-RAG answer is measured too, and should be ~0 since it
   was never asked to cite anything and has nothing to cite from.

2. LLM-judge groundedness score (optional, requires OPENAI_API_KEY):
   a separate LLM call scores each answer 1-5 on whether every factual
   claim it makes is actually supported by the retrieved context (for the
   RAG answer) or is unsupported speculation (expected to score low for
   the no-RAG answer, since it has no context to be grounded in).

Usage:
    python evaluation/evaluate_hallucination.py
    python evaluation/evaluate_hallucination.py --no-judge   # skip the LLM-judge step
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src import config
from src.pipeline.rag_pipeline import run_pipeline, run_no_rag_baseline

CITATION_RE = re.compile(r"\(Source:\s*[^)]+\)", re.IGNORECASE)
# crude heuristic for "sentence that names a condition": a sentence containing
# common diagnostic language.
CLAIM_HINT_RE = re.compile(
    r"\b(could be|may be|might be|is (a )?sign|suggests?|possible (cause|condition)|"
    r"consistent with|indicat\w+|likely)\b",
    re.IGNORECASE,
)


def citation_coverage(answer: str) -> float:
    """Fraction of claim-like sentences that carry a (Source: ...) citation."""
    sentences = re.split(r"(?<=[.!?])\s+", answer.strip())
    claim_sentences = [s for s in sentences if CLAIM_HINT_RE.search(s)]
    if not claim_sentences:
        return 0.0
    cited = [s for s in claim_sentences if CITATION_RE.search(s)]
    return len(cited) / len(claim_sentences)


JUDGE_PROMPT_TEMPLATE = """You are grading whether an AI-generated medical answer is \
GROUNDED strictly in the reference context provided, or whether it makes claims not \
supported by that context (hallucination).

Reference context (may be empty):
{context}

AI answer to grade:
{answer}

Score the AI answer's groundedness from 1 to 5:
5 = every claim is directly supported by the context, nothing invented
3 = mostly supported, but some minor unsupported claims
1 = mostly or entirely unsupported by the context (hallucinated)

Respond with ONLY the integer score, nothing else.
"""


def llm_judge_score(answer: str, context: str) -> float | None:
    try:
        from src.llm.generator import _call_llm
    except Exception:
        return None
    prompt = JUDGE_PROMPT_TEMPLATE.format(context=context or "(none provided)", answer=answer)
    try:
        # Judge with whichever provider is configured as the main LLM_PROVIDER,
        # so this works out of the box with Groq's free tier too.
        raw = _call_llm("You are a strict, terse grading assistant.", prompt)
        match = re.search(r"\d", raw)
        return float(match.group()) if match else None
    except Exception as exc:
        print(f"  [judge skipped: {exc}]")
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-judge", action="store_true", help="Skip the LLM-as-judge scoring step")
    args = parser.parse_args()

    df = pd.read_csv(config.EVAL_DATASETS_DIR / "hallucination_test_questions.csv")
    print(f"Loaded {len(df)} test questions\n")

    rows = []
    for _, row in df.iterrows():
        query = row["query"]
        print(f"Query: {query}")

        rag_result = run_pipeline(query)
        rag_answer = rag_result.answer
        context = "\n\n".join(f"{c['title']} ({c['source']})" for c in rag_result.citations)

        no_rag_answer = run_no_rag_baseline(query)

        rag_cov = citation_coverage(rag_answer)
        no_rag_cov = citation_coverage(no_rag_answer)

        record = {
            "query": query,
            "rag_citation_coverage": rag_cov,
            "no_rag_citation_coverage": no_rag_cov,
            "rag_answer": rag_answer,
            "no_rag_answer": no_rag_answer,
        }

        if not args.no_judge:
            record["rag_judge_score"] = llm_judge_score(rag_answer, context)
            record["no_rag_judge_score"] = llm_judge_score(no_rag_answer, "")

        rows.append(record)

    results_df = pd.DataFrame(rows)
    out_path = config.EVAL_RESULTS_DIR / "hallucination_eval.csv"
    results_df.to_csv(out_path, index=False)

    print("\n=== Hallucination reduction summary (Objective 4) ===\n")
    print(f"Mean citation coverage  - RAG: {results_df['rag_citation_coverage'].mean():.2%} | "
          f"No-RAG: {results_df['no_rag_citation_coverage'].mean():.2%}")
    if "rag_judge_score" in results_df and results_df["rag_judge_score"].notna().any():
        print(f"Mean LLM-judge groundedness (1-5) - RAG: {results_df['rag_judge_score'].mean():.2f} | "
              f"No-RAG: {results_df['no_rag_judge_score'].mean():.2f}")
    print(f"\nFull per-question results saved to {out_path}")


if __name__ == "__main__":
    main()
