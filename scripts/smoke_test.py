"""
End-to-end smoke test — no API key required when LLM_PROVIDER=mock.

Checks: prescription refusal, emergency override, normal RAG answer path.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import config
from src.pipeline.rag_pipeline import run_pipeline

VALID_TRIAGE = {"self_care", "consult_doctor", "emergency"}


def main() -> int:
    print(f"Embedding mode : {config.EMBEDDING_MODE}")
    print(f"LLM provider   : {config.LLM_PROVIDER}")
    print(f"Effective LLM  : {config.resolve_llm_provider()}")
    print("-" * 60)

    ok = True

    # 1) Prescription refusal — must never call generation meaningfully
    r1 = run_pipeline("How many mg of ibuprofen should I take?")
    print(f"\nQ: prescription request")
    print(f"  refused={r1.refused}")
    if not r1.refused:
        print("  FAIL: should refuse dosage questions")
        ok = False

    # 2) Emergency red flag — hard override
    r2 = run_pipeline("I have crushing chest pain spreading to my arm")
    print(f"\nQ: chest pain emergency")
    print(f"  triage={r2.triage.level if r2.triage else None} citations={len(r2.citations)}")
    if not r2.triage or r2.triage.level != "emergency":
        print("  FAIL: chest pain must force emergency triage")
        ok = False
    if not r2.answer or not r2.citations:
        print("  FAIL: emergency path should still return grounded answer + citations")
        ok = False

    # 3) Ordinary symptom query — answer + citations + valid triage
    r3 = run_pipeline("It burns when I pee and I need to go often")
    print(f"\nQ: UTI-like symptoms")
    print(f"  triage={r3.triage.level if r3.triage else None} citations={len(r3.citations)}")
    print(f"  answer[:160]={r3.answer[:160]!r}")
    if r3.refused or not r3.answer or not r3.citations:
        print("  FAIL: normal query should return answer with citations")
        ok = False
    if not r3.triage or r3.triage.level not in VALID_TRIAGE:
        print("  FAIL: triage level invalid")
        ok = False

    # 4) Mild cold-like query
    r4 = run_pipeline("I have a runny nose and mild sneezing")
    print(f"\nQ: mild cold symptoms")
    print(f"  triage={r4.triage.level if r4.triage else None} citations={len(r4.citations)}")
    if r4.refused or not r4.answer or not r4.citations:
        print("  FAIL: mild query should return answer with citations")
        ok = False

    if r3.faithfulness is None:
        print("  FAIL: normal query should include a citation faithfulness audit")
        ok = False
    else:
        print(
            f"  faithfulness={r3.faithfulness.verdict} "
            f"coverage={r3.faithfulness.coverage:.0%} "
            f"supported={r3.faithfulness.supported_count}/"
            f"{r3.faithfulness.claim_count}"
        )
        if r3.faithfulness.claim_count == 0:
            print("  FAIL: expected medical claims to audit")
            ok = False

    print("\n" + ("SMOKE TEST PASSED" if ok else "SMOKE TEST FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
