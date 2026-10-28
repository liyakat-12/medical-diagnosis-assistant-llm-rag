# MediAssist Phase 5 — Controlled reranking experiment (offline)

Date: 28 October 2026. Production retrieval, `RERANK_CANDIDATES`, thresholds, embeddings, and Chroma indexes were not changed. `evaluation/results/performance_phase5_baseline.json` and `docs/performance_phase5_baseline.md` were not rewritten.

This is not clinical validation. Phase 3 and Phase 4 suites were **not** run in this increment.

## Command

```powershell
.\venv\Scripts\python.exe evaluation/evaluate_rerank_phase5.py --warm 30 --out evaluation/results/performance_phase5_rerank_experiment.json
```

Window: `2026-10-28T01:24:25` to `01:31:05`. Same machine and venv as the Phase 5 mock baseline (Windows 10, AMD64, 16 CPUs, Python 3.11.9, `cross-encoder/ms-marco-MiniLM-L-6-v2` on **CPU**).

New files only:

- `evaluation/evaluate_rerank_phase5.py`
- `evaluation/results/performance_phase5_rerank_experiment.json`
- `docs/performance_phase5_rerank_experiment.md`

## Checkpoint (before any measurement)

### How the baseline timed rerank

The Phase 5 baseline’s `retrieve_ms` is embed + Chroma + rerank + filter. Isolated `stage_ms.rerank_ms` was a **separate** `rerank_chunks` call after the 25 stream runs, **n=5**. Those 511–978 ms figures are not pipeline wall time and are not a 25-sample distribution.

Production path (`retrieve_candidates`):

1. One `store.search(query, top_k=max(TOP_K, RERANK_CANDIDATES))` → **12** hits.
2. One `rerank_chunks(query, results, top_k=len(results))` → scores **all 12**.
3. Return top 4 for the answer and the full reranked list for match %.

`rerank_chunks` is in-memory only. It does not write Chroma, embeddings, or user state. Repeating it on frozen `RetrievedChunk` lists does not change retrieval results or persistent indexes.

`CrossEncoder.predict` is already one call on the full pair list. Default `batch_size=32`, so 12 pairs are one batch. Passing a smaller `top_k` still scores every pair; only the returned slice shrinks.

### Experiment plan

| ID | Question | Method | Overhead / confounders |
| --- | --- | --- | --- |
| A | What does warm rerank of 12 pairs cost? | Freeze 12 Chroma hits; 30 `rerank_chunks` reps; init timed separately | Not pipeline latency. Passage length and CPU load move the number. p95 at n=30 is indicative. |
| B | Does a smaller fetch keep Phase 2 quality? | Same 12-hit Chroma prefix; rerank first N ∈ {4,6,8,12}; score Recall@1/@4/MRR on 103 Phase 2 retrieval queries | First-N of one fetch matches `RERANK_CANDIDATES=N`. Sibling expected notes can sit at ranks 9–12. |
| C | Is there unused batching or a second model pass? | Inspect `predict`; time batched vs sequential; time `top_k=4` vs `12` on the same 12 pairs | Padding in a batch of 12 can differ from 12 single-pair forwards. No user-answer cache is added. |

## Experiment A — rerank cost (n=30, 12 candidates)

Model load in this process: **620.186 ms** (already on disk; not the 42.6 s MiniLM cold start from the pipeline baseline). Later `_load_model()` calls are cache hits (0.0 ms).

Rerank-only milliseconds. Chroma fetch is reported once and is **not** in `rerank_ms`.

| ID | Query | Words | Candidates | Rerank median | Indicative p95 | Chroma fetch once |
| --- | --- | --- | --- | --- | --- | --- |
| ra_short | pain | 1 | 12 | 529.322 | 672.277 | 31.542 |
| ra_medium | I have a dry cough at night | 7 | 12 | 630.182 | 779.150 | 47.319 |
| ra_knee | Why does my knee hurt when I climb stairs? | 9 | 12 | 644.966 | 856.708 | 46.914 |
| ra_long | swollen painful calf after a long flight… | 15 | 12 | 579.130 | 654.177 | 50.952 |
| ra_emergency | severe crushing chest pain spreading to my jaw | 10 | 12 | 605.205 | 720.451 | 75.650 |

Warm rerank of the current 12-pair set is about **0.53–0.65 s median** on this CPU. That is large enough, with n=30, to treat rerank as the main warm retrieve cost. It is still **not** the full pipeline (baseline medical walls were 626–1,200 ms).

## Experiment B — candidate-count alternatives (offline)

103 Phase 2 retrieval queries. One Chroma fetch of 12; rerank the first N; take top 4. Production `RERANK_CANDIDATES` stayed 12.

Offline **N=12** matched the recorded Phase 2 file: Recall@1 **0.835**, Recall@4 **1.000**, MRR **0.910**.

| N | Recall@1 | Recall@4 | MRR | Pool-loss queries | Top-4 ID diffs vs 12 | New Recall@4 misses vs 12 |
| --- | --- | --- | --- | --- | --- | --- |
| 4 | 0.845 (87/103) | **0.981 (101/103)** | 0.908 | 39 | 91 | **c06, d19** |
| 6 | 0.845 | **0.981** | 0.908 | 29 | 60 | **c06, d19** |
| 8 | 0.845 | **0.981** | 0.908 | 23 | 40 | **c06, d19** |
| 12 (current) | 0.835 (86/103) | **1.000 (103/103)** | 0.910 | 17 | 0 | none |
| Vector top-4, no rerank (reference only) | 0.845 | 0.981 | 0.907 | — | — | same two misses |

“Pool-loss” means at least one **labeled sibling** was outside the first N Chroma hits. At N=12 that happens on 17 queries, but another labeled note still lands in the top 4, so Recall@4 stays 1.000.

### Queries that lose Recall@4 below 12 candidates

Both labeled notes sit **outside the first 8 Chroma hits**. The 12-candidate rerank then places them at rank 2.

**c06** — “I have a wheezy cough and a tight chest”

| N | Top 4 | Expected asthma notes in pool? |
| --- | --- | --- |
| 4 / 6 / 8 | `cough_after_exercise`, `wheeze_after_cold`, `cough_with_mucus`, plus a cough/rib note | No (`asthma_mild`, `what_is_asthma_simple`, `exercise_induced_asthma` all absent) |
| 12 | `cough_after_exercise`, **`what_is_asthma_simple`**, `wheeze_after_cold`, `cough_with_mucus` | `what_is_asthma_simple` recovered |

**d19** — “My big toe is red hot and extremely painful overnight”

| N | Top 4 | `gout` in pool? |
| --- | --- | --- |
| 4 / 6 / 8 | `big_toe_joint_ache` plus shoe / toenail / bunion notes | No |
| 12 | `big_toe_joint_ache`, **`gout`**, `flip_flop_toe_pain`, `bunion_ache` | Yes, rank 2 |

These are explained pool-truncation misses, not scorer noise. They are still retrieval regressions relative to the current 12-candidate setup.

### Other ranking movement (Recall@4 still hits)

- **d14** (“I cannot get to sleep at night”): smaller N ranks `difficulty_sleeping` first; N=12 ranks `cannot_sleep_after_nap` first and the expected note at 3. That is why Recall@1 is slightly **higher** at N=4/6/8.
- **d12** / **s05**: N=4 also swaps hypothyroidism / fatigue winners; N=6 and N=8 do not repeat the s05 Recall@1 loss.
- Isolation f01–f03 still hit the expected note and keep forbidden docs out at every N. Emergency 9/9, prescription 3/3, out-of-scope 4/4 — those checks do not call the reranker.

### Latency vs N (frozen knee-stairs pool, n=30, rerank only)

| N | Median ms | Indicative p95 |
| --- | --- | --- |
| 4 | 209.159 | 271.510 |
| 6 | 306.596 | 463.909 |
| 8 | 442.001 | 663.633 |
| 12 | 681.726 | 761.183 |

Smaller N is faster. That saving is rerank-only, not a measured pipeline or API delta.

## Experiment C — batching and reuse

- Production already calls `model.predict(pairs)` once. There is no per-chunk loop and no second rerank.
- `_to_evidence` runs twice after scoring (top slice and pool). That is formatting, not a second model pass.
- `predict` default `batch_size=32`, so 12 pairs are one batch.
- Same 12 pairs, n=30: batched median **596.782 ms**; sequential 12×`predict([pair])` median **519.380 ms** (max 1095 vs 724). Sequential can avoid padding to the longest sibling; it is not a clear win and was not adopted.
- `rerank_chunks(..., top_k=4)` vs `top_k=12` on the same 12 pairs: **571** vs **559** ms. Shrinking the return slice does not shrink model work.
- No personalized-answer cache exists. None was added.

## Recommendation

**Keep production `RERANK_ENABLED=true` and `RERANK_CANDIDATES=12`.**

Rerank is the dominant warm retrieve cost (~0.53–0.65 s median for 12 CPU pairs). Cutting to 4, 6, or 8 candidates would likely save a few hundred milliseconds of rerank time, but it drops Phase 2 Recall@4 from **1.000 to 0.981** by losing `what_is_asthma_simple` (c06) and `gout` (d19). Those notes are only in the Chroma tail that 12-candidate fetch still sees. Vector-only top-4 has the same Recall@4 hole, so turning rerank off is not a quality-neutral shortcut.

Do not change thresholds, embeddings, or indexes on the back of this experiment. If a later change is approved, rerun:

```powershell
.\venv\Scripts\python.exe evaluation/evaluate_answer_quality.py --out evaluation/results/answer_quality_after.json
.\venv\Scripts\python.exe evaluation/evaluate_conversation_phase4.py --out evaluation/results/conversation_phase4_after.json
.\venv\Scripts\python.exe evaluation/evaluate_kb_phase2.py --out evaluation/results/kb_phase2_after.json
```

Those three commands were **not** executed here.

## Limitations

- Rerank timings exclude embed, Chroma, FastAPI, SSE, and the browser.
- p95 with n=30 is interpolated, not a precise tail.
- Candidate-count quality uses the first N of one 12-hit fetch.
- Chroma telemetry warning (`capture() takes 1 positional argument but 3 were given`) still appears; the run completed.
- Production retrieval behavior was not changed.
