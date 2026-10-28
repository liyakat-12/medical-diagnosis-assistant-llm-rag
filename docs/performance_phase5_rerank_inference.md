# MediAssist Phase 5 — Cross-encoder inference experiment (12 candidates kept)

Date: 28 October 2026. Production `reranker.py`, `RERANK_ENABLED`, `RERANK_CANDIDATES`, model weights, MiniLM embeddings, thresholds, and the Chroma index were not changed. Earlier Phase 5 baseline and candidate-count files were left as they were.

This is not clinical validation. Phase 3 and Phase 4 suites were **not** run.

## Command

```powershell
.\venv\Scripts\python.exe evaluation/evaluate_rerank_inference_phase5.py --warm 30 --out evaluation/results/performance_phase5_rerank_inference.json
```

Window: `2026-10-28T01:39:33` to `01:58:34`. Same machine and venv as the mock baseline (Windows 10, AMD64, 16 logical CPUs, Python 3.11.9).

New files only:

- `evaluation/evaluate_rerank_inference_phase5.py`
- `evaluation/results/performance_phase5_rerank_inference.json`
- `docs/performance_phase5_rerank_inference.md`

## Checkpoint and measurement plan

Inspected before any production edit:

| Item | Live value |
| --- | --- |
| Production path | `rerank_chunks` → one `model.predict(pairs)` under `torch.no_grad()` |
| Candidates scored | all 12 |
| Device | CPU (`torch 2.14.0+cpu`, CUDA false) |
| Default threads | intra **8**, interop **8** |
| MKL / OpenMP | available |
| sentence-transformers / transformers | 3.2.1 / 4.57.6 |
| CrossEncoder `max_length` | `None` (tokenizer 512) |
| Default `predict` batch_size | 32 (so 12 pairs = one padded batch) |
| onnxruntime | 1.29.0 installed |
| Optimum | **not** installed — no drop-in ORT CrossEncoder |
| psutil | not installed |

Frozen pair token lengths on the five Phase 5 queries: **49–164**. Padding is to the longest sibling in the batch, not to 512. Truncating `max_length` to 128 would cut some pairs and was not tested as a speed knob.

Plan that was then executed (offline only):

1. Freeze the same 12-hit pools and pair order.
2. Screen thread counts {1,2,4,8,16}, interop=1, batch sizes {1,4,12,32}, and an extra `inference_mode` wrap. n=30 on the knee query. Do not assume more threads or another device are faster.
3. Re-measure the default and the two fastest variants on all five queries for isolated rerank **and** search+rerank.
4. Score the same 103 Phase 2 retrieval queries. Require Recall@4 = 1.000 and check c06 / d19.

Not evaluated (unsupported or out of scope): CUDA, Optimum-ORT export, `torch.compile`, shrinking the 12-candidate pool, answer caching.

## Screen (knee stairs, n=30, rerank only)

Default median **714.377 ms**. Indicative p95. Same top-4 IDs on every config.

| Config | Threads | Batch | Median ms | Indicative p95 | Process CPU median ms |
| --- | --- | --- | --- | --- | --- |
| default | 8 | 32 | 714.377 | 831.762 | 5476.562 |
| threads_1 | 1 | 32 | 936.847 | 1040.966 | 937.500 |
| threads_2 | 2 | 32 | 657.071 | 723.131 | 1289.062 |
| **threads_4** | 4 | 32 | **604.017** | 670.412 | 2351.562 |
| threads_16 | 16 | 32 | 780.487 | 880.372 | 9234.375 |
| interop_1 | 8 / interop 1 | 32 | 715.727 | 955.654 | 5492.188 |
| batch_1 | 8 | 1 | 615.419 | 827.164 | 4726.562 |
| **batch_4** | 8 | 4 | **534.072** | 688.211 | 4179.688 |
| batch_12 | 8 | 12 | 652.110 | 773.905 | 5039.062 |
| inference_mode | 8 | 32 | 661.400 | 754.165 | 5117.188 |

More threads were slower. Default 8 intra-op threads spend about **7.7 CPU-seconds per wall-second**. Four threads cut that oversubscription and also lowered wall time. `batch_size=4` was the fastest screen point (less padding than one batch of 12). `torch.inference_mode` on top of the existing `no_grad` was a small, noisy gain and was not in the top two.

## Confirm (five frozen queries, n=30)

Medians in milliseconds. Retrieve = one Chroma `search(top_k=12)` plus rerank of those 12 pairs.

| Query | Default rerank / retrieve | threads_4 | batch_4 |
| --- | --- | --- | --- |
| pain | 528 / 559 | 489 / 509 | **430 / 464** |
| dry cough at night | 626 / 635 | 562 / 585 | **441 / 498** |
| knee stairs | 650 / 703 | 577 / 612 | **508 / 548** |
| calf after long flight | 609 / 655 | 565 / 591 | **486 / 528** |
| crushing chest pain | 602 / 628 | 506 / 547 | **461 / 513** |

`batch_4` was fastest on every query. Isolated rerank medians fell by about **19–30%** versus this run’s default. Search+rerank medians fell by about **17–22%**. `threads_4` was slower than `batch_4` but still below default on every query.

These are not full pipeline or API times. Embed, FastAPI, SSE, and the browser remain excluded.

## Retrieval quality (103 Phase 2 queries, 12 candidates)

| Config | Recall@1 | Recall@4 | MRR | Top-4 diffs vs production `rerank_chunks` |
| --- | --- | --- | --- | --- |
| default | 0.835 | **1.000** | 0.910 | 0 |
| threads_4 | 0.835 | **1.000** | 0.910 | 0 |
| batch_4 | 0.835 | **1.000** | 0.910 | 0 |

Watch queries still recover the labeled notes at rank 2:

- **c06** wheezy cough / tight chest → `what_is_asthma_simple` in top 4
- **d19** red-hot big toe overnight → `gout` in top 4

Emergency, prescription, citation, and isolation suites were **not** rerun here.

## Recommendation

**Do not deploy yet.** Production settings should stay `RERANK_ENABLED=true`, `RERANK_CANDIDATES=12`, same model and index.

If a later production change is approved, the only isolated knob that both sped up inference and held quality in this run is:

- `model.predict(..., batch_size=4)` while still scoring all 12 pairs.

That is a one-argument change inside `rerank_chunks`. It does not drop candidates. Ranking matched production exactly on 103 queries.

`torch.set_num_threads(4)` also helped and reduced CPU oversubscription. Combining `batch_size=4` with 4 threads was **not** measured. More threads (16) and CUDA (unavailable) should not be assumed faster.

Before any production edit, rerun:

```powershell
.\venv\Scripts\python.exe evaluation/evaluate_answer_quality.py --out evaluation/results/answer_quality_after.json
.\venv\Scripts\python.exe evaluation/evaluate_conversation_phase4.py --out evaluation/results/conversation_phase4_after.json
.\venv\Scripts\python.exe evaluation/evaluate_kb_phase2.py --out evaluation/results/kb_phase2_after.json
```

Those commands were **not** executed in this increment.

## Warnings and limitations

- Chroma telemetry: `capture() takes 1 positional argument but 3 were given`. The run completed.
- p95 with n=30 is interpolated, not a precise tail.
- Screen default on the knee query was 714 ms; the later confirm default was 650 ms. Treat deltas inside this process as relative, not as a new pipeline baseline.
- Thread settings apply only to this Python process. A FastAPI worker may start with a different default.
- onnxruntime is present; Optimum is not, so ORT was not a supported drop-in in this experiment.
- No answer cache or user-specific medical-response cache was added.
- Phase 3 / Phase 4 / frontend tests were not claimed and were not run.
