# MediAssist Phase 5 — batch_size=4 validation

Date: 28 October 2026. Only the cross-encoder `predict` batch size in `rerank_chunks` was changed (32 → 4). All 12 candidates are still scored. Thread count, model weights, embeddings, thresholds, and the Chroma index were not changed.

This is not a deployment or production-readiness claim. It is not clinical validation.

## Change

```51:51:backend/src/retrieval/reranker.py
    scores = model.predict(pairs, batch_size=4, show_progress_bar=False)
```

`tests/test_pipeline.py` FakeModel now accepts `**_kwargs` so the unit test can call the new keyword. Ranking logic, sort, sigmoid, and return shape are unchanged.

Preserved: `evaluation/results/performance_phase5_baseline.json`, `performance_phase5_rerank_*.json`, Phase 3/4 `*_after.json`, `kb_phase2_after.json`.

## Commands

```powershell
.\venv\Scripts\python.exe -m pytest tests -q --tb=short
npm test
.\venv\Scripts\python.exe evaluation/evaluate_kb_phase2.py --out evaluation/results/kb_phase2_batch4.json
.\venv\Scripts\python.exe evaluation/evaluate_answer_quality.py --out evaluation/results/answer_quality_batch4.json
.\venv\Scripts\python.exe evaluation/evaluate_conversation_phase4.py --out evaluation/results/conversation_phase4_batch4.json
.\venv\Scripts\python.exe evaluation/evaluate_performance.py --warm 25 --out evaluation/results/performance_phase5_batch4.json
```

Frontend tests ran from `frontend\`. Backend tests and evals used `venv\Scripts\python.exe` (3.11.9) on the same Windows 10 AMD64 machine as the mock baseline.

## Quality

| Suite | Before | After batch_size=4 |
| --- | --- | --- |
| Phase 2 retrieval (103) | R@1 0.835, R@4 **1.000**, MRR 0.910 | same |
| Phase 2 emergency / prescription / isolation / out-of-scope | 9/9, 3/3, 3/3, 4/4 | same |
| Phase 3 answer quality | 72/72 | **72/72** |
| Phase 4 conversation pipeline | 59/59 | **59/59** |
| Backend pytest | previously green | **188 passed** |
| Frontend tests | previously 56 | **56 passed** |

c06 still ranks `what_is_asthma_simple` at 2. d19 still ranks `gout` at 2.

### c11 top-4 vs `kb_phase2_after.json`

One top-4 list differs: c11 (“swollen painful calf after a long flight…”).

| File | Top 4 | Rank of expected |
| --- | --- | --- |
| `kb_phase2_after.json` (27 Oct) | `red_flag_leg_clot`, `charley_horse_calf`, `pulmonary_embolism`, `travel_constipation_plane` | 1 |
| `kb_phase2_batch4.json` | `red_flag_leg_clot`, `charley_horse_calf`, `travel_constipation_plane`, `swollen_ankles_evening` | 1 |

Live Chroma’s 12-hit pool for the current search text (`… breathless calf swelling`) does **not** contain `pulmonary_embolism`. Scoring that same frozen pool with `batch_size` 32, 4, and 1 produced **identical** top-4 IDs and raw scores (deltas 0.0 at 1e-6). The list change versus the October 27 file is from later query-normalize / index state, not from this batch-size edit. Recall@4 remains 1.000 via `red_flag_leg_clot`.

## Performance (same 10 scenarios, 25 warm reps, mock)

Pipeline wall / retrieve medians, milliseconds. Isolated rerank stage is n=5 and is not the full pipeline.

| ID | Wall before → after | Retrieve before → after | Isolated rerank before → after |
| --- | --- | --- | --- |
| pf01 cough | 819 → **421** | 814 → 417 | 676 → 314 |
| pf02 knee | 919 → **477** | 913 → 473 | 648 → 341 |
| pf03 follow-up | 800 → **491** | 794 → 484 | 511 → 276 |
| pf06 Pompe | 787 → **469** | 784 → 466 | 653 → 339 |
| pf07 pain | 626 → **404** | 623 → 402 | 512 → 290 |
| pf08 chest pain | 1200 → **450** | 1193 → 444 | 978 → 333 |
| pf10 rare disease | 1044 → **474** | 1041 → 471 | 678 → 378 |
| pf04 / pf05 general | 1.5 / 1.5 | 0 | skipped |
| pf09 prescription | 0.10 → 0.07 | 0 | skipped |

Retrieving scenarios are about **35–63%** faster on this machine. General chat and prescription refuse stay near zero (no rerank). p95 at n=25 is still indicative. FastAPI, Mongo, SSE, and the browser were not measured.

## Warnings

- Chroma telemetry: `capture() takes 1 positional argument but 3 were given`.
- The performance runner still labels its JSON `phase: baseline`; the new file is `performance_phase5_batch4.json`.
- Phase 4 frontend rows remain listed, not scored by the Python runner; UI coverage is the 56 frontend tests.

## Stop point

The narrow `batch_size=4` change is in `rerank_chunks` and the listed validations passed. This report does not claim the app is production-ready or fully deployed.
