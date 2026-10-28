"""Baseline multi-turn conversation evaluation (Phase 4).

Scores pipeline scenarios with run_pipeline + build_conversation_state.
Does not score frontend/streaming UI scenarios and does not modify Phase 3 files.

Usage:
    python evaluation/evaluate_conversation_phase4.py
    python evaluation/evaluate_conversation_phase4.py --out evaluation/results/conversation_phase4_baseline.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))
sys.path.insert(0, str(ROOT_DIR / "evaluation" / "datasets"))

from conversation_phase4 import FRONTEND_SCENARIOS, SCENARIOS, dump_jsonl  # noqa: E402
from src.pipeline.conversation_state import build_conversation_state  # noqa: E402
from src.pipeline.rag_pipeline import run_pipeline  # noqa: E402
from src.safety.guardrails import check_emergency, check_prescription_request  # noqa: E402
from src.safety.public_text import contains_provider_leak as public_leak  # noqa: E402

_VENDOR = re.compile(r"\b(groq|openai|ollama|chatgpt|gpt-4o|gpt-oss)\b", re.I)
_UNCERTAIN = re.compile(
    r"not (enough|a close|sure)|could not (find|rely)|i don't have a close|"
    r"general medical knowledge|please rephrase|clarif|"
    r"not a close enough match|no close match|need a bit more detail",
    re.I,
)
_DISCLAIMER = re.compile(r"not a diagnosis|see a clinician|ask a doctor or pharmacist", re.I)


def _has_any(text: str, needles) -> bool:
    if not needles:
        return True
    lowered = (text or "").lower()
    return any(str(needle).lower() in lowered for needle in needles)


def _blob(result) -> str:
    parts = [result.answer or ""]
    for item in result.citations or []:
        parts.append(" ".join(str(item.get(key) or "") for key in ("title", "source", "condition")))
    for item in result.possible_conditions or []:
        parts.append(" ".join(str(item.get(key) or "") for key in ("condition", "title")))
    return " ".join(parts)


def _condition_text(result) -> str:
    names = []
    for item in (result.possible_conditions or []) + (result.citations or []):
        names.append(str(item.get("condition") or item.get("title") or ""))
    return " ".join(names)


def _history_row(role: str, content: str, result=None) -> dict:
    row = {"role": role, "content": content or "", "possible_conditions": [], "triage": None}
    if result is not None:
        row["possible_conditions"] = list(result.possible_conditions or [])
        row["triage"] = (
            {"level": result.triage.level, "label": result.triage.label, "guidance": result.triage.guidance}
            if result.triage
            else None
        )
    return row


def score_turn(user: str, history: list[dict], expect: dict) -> dict:
    state = build_conversation_state(user, history)
    result = run_pipeline(user, chat_history=history)
    origin = result.evidence_origin or "none"
    triage = result.triage.level if result.triage else None
    blob = _blob(result)
    conds = _condition_text(result)
    checks: dict[str, bool] = {}

    if "intent" in expect:
        checks["intent"] = state.intent == expect["intent"]
    if "status" in expect:
        checks["status"] = state.status == expect["status"]
    if "reuse" in expect:
        checks["reuse"] = state.reuse_history is bool(expect["reuse"])
    if expect.get("search_contains"):
        checks["search_contains"] = _has_any(state.search_query, expect["search_contains"])
    if expect.get("search_forbids"):
        checks["search_forbids"] = not _has_any(state.search_query, expect["search_forbids"])
    if expect.get("origin"):
        checks["origin"] = origin in set(expect["origin"])
    if "refused" in expect:
        checks["refusal"] = bool(result.refused) is bool(expect["refused"])
    if expect.get("prescription_guard"):
        checks["prescription_guard"] = check_prescription_request(user).triggered and bool(result.refused)
    wanted_triage = expect.get("triage", "__absent__")
    if wanted_triage == "emergency":
        checks["triage"] = triage == "emergency"
    elif wanted_triage == "not_emergency":
        checks["triage"] = triage != "emergency"
    elif wanted_triage is None and "triage" in expect:
        checks["triage"] = triage is None
    if "emergency_guard" in expect:
        triggered = check_emergency(user, history).triggered
        checks["emergency_guard"] = triggered is bool(expect["emergency_guard"])
        if expect["emergency_guard"]:
            checks["emergency_independent"] = triggered and triage == "emergency"
    if expect.get("must_mention"):
        checks["must_mention"] = _has_any(blob, expect["must_mention"])
    if expect.get("answer_contains"):
        checks["answer_contains"] = _has_any(result.answer or "", expect["answer_contains"])
    if expect.get("answer_forbids"):
        checks["answer_forbids"] = not _has_any(result.answer or "", expect["answer_forbids"])
    if expect.get("forbid_conditions"):
        checks["forbid_conditions"] = not _has_any(conds + " " + (result.answer or ""), expect["forbid_conditions"])
    if expect.get("no_cards"):
        checks["no_cards"] = not (result.possible_conditions or []) and result.triage is None
    if expect.get("empty_matches"):
        checks["empty_matches"] = not (result.possible_conditions or [])
    if expect.get("require_uncertainty"):
        checks["uncertainty"] = bool(_UNCERTAIN.search(result.answer or "")) or origin in {"none", "llm"}
    if expect.get("require_disclaimer"):
        checks["disclaimer"] = bool(_DISCLAIMER.search(result.answer or "") or _DISCLAIMER.search(result.disclaimer or ""))
    checks["no_provider_leak"] = not public_leak(result.answer or "") and not _VENDOR.search(result.answer or "")

    failed = [name for name, ok in checks.items() if not ok]
    return {
        "user": user,
        "intent": state.intent,
        "status": state.status,
        "reuse": state.reuse_history,
        "search_query": state.search_query,
        "origin": origin,
        "triage": triage,
        "refused": result.refused,
        "answer_preview": (result.answer or "")[:220],
        "conditions": [str(item.get("condition") or "") for item in (result.possible_conditions or [])],
        "checks": checks,
        "failed_checks": failed,
        "passed": not failed,
        "result": result,
    }


def evaluate() -> dict:
    details = []
    for row in SCENARIOS:
        history = list(row.get("seed_history") or [])
        turn_rows = []
        ok = True
        for turn in row["turns"]:
            scored = score_turn(turn["user"], history, turn.get("expect") or {})
            result = scored.pop("result")
            turn_rows.append(scored)
            ok = ok and scored["passed"]
            history.append(_history_row("user", turn["user"]))
            history.append(_history_row("assistant", result.answer or "", result))
        details.append(
            {
                "id": row["id"],
                "category": row["category"],
                "layer": "pipeline",
                "notes": row.get("notes") or "",
                "ambiguity": row.get("ambiguity") or "",
                "passed": ok,
                "turns": turn_rows,
                "failed_checks": [item["failed_checks"] for item in turn_rows if item["failed_checks"]],
            }
        )

    by_category: dict[str, dict] = defaultdict(lambda: {"n": 0, "passed": 0})
    check_fails: Counter[str] = Counter()
    for item in details:
        by_category[item["category"]]["n"] += 1
        by_category[item["category"]]["passed"] += int(item["passed"])
        for group in item["failed_checks"]:
            for name in group:
                check_fails[name] += 1

    n = len(details) or 1
    passed = sum(1 for item in details if item["passed"])
    return {
        "pipeline_n": len(details),
        "pipeline_passed": passed,
        "pipeline_failed": len(details) - passed,
        "pipeline_pass_rate": passed / n,
        "by_category": {
            key: {
                "n": val["n"],
                "passed": val["passed"],
                "failed": val["n"] - val["passed"],
                "pass_rate": val["passed"] / val["n"] if val["n"] else 0.0,
            }
            for key, val in sorted(by_category.items())
        },
        "check_fail_counts": dict(check_fails),
        "fail_ids": [item["id"] for item in details if not item["passed"]],
        "failures": [item for item in details if not item["passed"]],
        "frontend_n": len(FRONTEND_SCENARIOS),
        "frontend_scored": False,
        "frontend_ids": [row["id"] for row in FRONTEND_SCENARIOS],
        "ambiguities": [
            {"id": row["id"], "ambiguity": row["ambiguity"]}
            for row in SCENARIOS
            if row.get("ambiguity")
        ],
        "cases": details,
        "method": (
            "Deterministic assertions on build_conversation_state and run_pipeline "
            "(mock LLM). Frontend/streaming abort/retry/refresh/switch scenarios "
            "are listed but not scored. This is not clinical validation."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    dump_jsonl(ROOT_DIR / "evaluation" / "datasets" / "conversation_phase4.jsonl")
    result = evaluate()
    summary = {key: result[key] for key in result if key not in {"cases", "failures"}}
    print(json.dumps(summary, indent=2))
    print("\nPipeline failures:")
    for item in result["failures"]:
        print(f"  {item['id']} [{item['category']}]")
        for turn in item["turns"]:
            if turn["failed_checks"]:
                print(f"    {turn['user']!r}")
                print(
                    f"      intent={turn['intent']} status={turn['status']} reuse={turn['reuse']} "
                    f"origin={turn['origin']} triage={turn['triage']} failed={turn['failed_checks']}"
                )
                print(f"      search={turn['search_query'][:120]!r}")
        if item.get("ambiguity"):
            print(f"    ambiguity: {item['ambiguity']}")
    print("\nFrontend scenarios listed, not scored:", ", ".join(result["frontend_ids"]))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
