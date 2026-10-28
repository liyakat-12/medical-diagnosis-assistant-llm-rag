# MediAssist Phase 5 — Performance baseline (no optimizations)

Date: 28 October 2026. Application code, retrieval behavior, embeddings, thresholds, indexes, and caching were not modified. Phase 3 and Phase 4 datasets and result files were left unchanged.

This report records the current in-process pipeline only. It is not clinical validation and not an API or browser benchmark.

## Commands

```powershell
.\venv\Scripts\python.exe evaluation/evaluate_performance.py --warm 25 --out evaluation/results/performance_phase5_baseline.json
```

The system `python` on PATH is 3.14 and does not have project dependencies. Use `venv\Scripts\python.exe` (3.11.9), the same interpreter as Phase 3 and Phase 4.

Live-provider lane was **not** run. A later Groq/OpenAI/Ollama measurement must use `--live` and a separate results file, for example `evaluation/results/performance_phase5_baseline_live.json`. Do not mix those numbers with this mock baseline.

## Artifacts

| File | Role |
| --- | --- |
| `evaluation/datasets/performance_phase5.py` | Fixed 10-scenario dataset |
| `evaluation/datasets/performance_phase5.jsonl` | Same 10 rows |
| `evaluation/evaluate_performance.py` | Cold + warm runner |
| `evaluation/results/performance_phase5_baseline.json` | Mock-provider baseline |
| `docs/performance_phase5_baseline.md` | This report |

Preserved (not rewritten):

- `evaluation/datasets/answer_quality_phase3.py` / `.jsonl`
- `evaluation/results/answer_quality_baseline.json` / `answer_quality_after.json`
- `evaluation/datasets/conversation_phase4.py` / `.jsonl`
- `evaluation/results/conversation_phase4_baseline.json` / `conversation_phase4_after.json`

## What this measures

In-process `iter_pipeline_stream` after isolated cold model loads.

| Included | Excluded |
| --- | --- |
| Import time | FastAPI HTTP stack |
| MiniLM load + first encode | MongoDB, auth, JWT cookies |
| Chroma open + first `collection.query` | SSE queue and network transport |
| Reranker load + first rerank | Browser / React / ChatContext |
| 25 warm stream repetitions per scenario | Live LLM network latency |
| 5 extra embed / Chroma / rerank probes on retrieving scenarios | Token or dollar cost (no `usage` data exists) |

`first_pipeline_ms` is the first assembled pipeline **after** those isolated loads, so models are already cached. It is closer to a request after FastAPI lifespan warmup than to a brand-new process.

Mock first-token time is local generation plus word yield. It is not a network TTFB.

## Environment (keep this fixed for later before/after)

| Setting | Value |
| --- | --- |
| OS | Windows 10, AMD64, 16 logical CPUs |
| Processor | AMD64 Family 23 Model 96 Stepping 1, AuthenticAMD |
| Python | 3.11.9 (`venv`) |
| Started / finished | 2026-10-28T01:14:36 / 2026-10-28T01:18:42 |
| Provider lane | **mock** (`LLM_PROVIDER=mock`) |
| `EMBEDDING_MODE` | `general` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Rerank | enabled, `cross-encoder/ms-marco-MiniLM-L-6-v2`, candidates=12 |
| `TOP_K` | 4 |
| `MIN_RELEVANCE_SCORE` / `MIN_VECTOR_SCORE` | 0.22 / 0.38 |
| `LLM_KB_FALLBACK` | true |
| `CHAT_HISTORY_WINDOW` | 8 |
| Warm repeats | **25 requested, 25 ok on every scenario**, 0 errors |
| RAM RSS | not measured (`psutil` not installed) |
| tracemalloc current | 41.0 MB before load → 245.33 MB after cold → 245.64 MB after warm (Python allocations only; native MiniLM / Chroma / torch heaps are excluded) |

## Cold-start (one process-local sample)

| Step | ms |
| --- | --- |
| Import `rag_pipeline` | 7406.194 |
| MiniLM load | 42595.809 |
| First query embed (`headache`) | 343.087 |
| Chroma open | 1185.870 |
| First isolated `collection.query` | 187.856 |
| First `store.search` (includes another embed) | 111.245 |
| Reranker load | 896.280 |
| First rerank | 841.956 |
| First assembled pipeline after those loads | 851.813 |

First assembled pipeline stage split: classify 17.45 ms, retrieve 827.95 ms, generate 3.66 ms, total 851.64 ms. Origin: `knowledge_base`.

Process-cold is dominated by MiniLM load (~42.6 s) plus imports (~7.4 s). Do not treat the 852 ms first pipeline as a from-scratch process start.

## Warm pipeline (n=25 per scenario)

p95 is a linear interpolation on 25 samples. It is **indicative only** and is not a precise tail estimate.

Times are milliseconds.

| ID | Category | Origin (last) | Wall median | Wall p95 | First-token median | Retrieve median | Generate median |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pf01 | simple_medical | knowledge_base | 818.959 | 1188.332 | 816.431 | 813.54 | 1.94 |
| pf02 | multi_source_medical | knowledge_base | 918.903 | 1149.231 | 916.927 | 913.43 | 1.83 |
| pf03 | followup | knowledge_base | 800.263 | 853.280 | 798.647 | 793.93 | 1.68 |
| pf04 | general_chat | general | 1.501 | 2.205 | 1.360 | 0.00 | 0.13 |
| pf05 | general_chat | general | 1.545 | 1.852 | 1.344 | 0.00 | 0.20 |
| pf06 | weak_evidence | none | 787.079 | 852.369 | 786.787 | 784.33 | 0.13 |
| pf07 | weak_evidence | none | 625.506 | 703.773 | 625.208 | 623.45 | 0.11 |
| pf08 | emergency | knowledge_base | 1199.956 | 1622.173 | 1196.496 | 1193.34 | 2.38 |
| pf09 | safety_refusal | none (refused) | 0.104 | 0.179 | 0.072 | 0.00 | 0.00 |
| pf10 | educational | none | 1044.043 | 1394.139 | 1043.714 | 1040.81 | 0.16 |

Median of scenario-median wall times by category (ms): general_chat 1.523, safety_refusal 0.104, weak_evidence 706.293, followup 800.263, simple_medical 818.959, multi_source_medical 918.903, educational 1044.043, emergency 1199.956.

On retrieving paths, first-token median is within about 3 ms of wall median. Mock generation finishes before tokens are yielded, so first-token is not a useful streaming-TTFB proxy here.

## Isolated warm stages (n=5, after the 25 stream runs)

These probes do not change the n=25 stream timings. p95 on n=5 is not a tail estimate; use the medians.

| ID | Embed median | Isolated Chroma median | `store.search` (includes embed) | Rerank median |
| --- | --- | --- | --- | --- |
| pf01 | 48.398 | 81.422 | 122.004 | 676.006 |
| pf02 | 36.497 | 80.626 | 112.796 | 648.403 |
| pf03 | 36.446 | 73.427 | 113.215 | 511.092 |
| pf06 | 36.506 | 77.344 | 112.454 | 653.051 |
| pf07 | 26.405 | 79.196 | 104.636 | 512.338 |
| pf08 | 74.407 | 96.611 | 168.477 | 977.875 |
| pf10 | 42.192 | 89.170 | 131.918 | 678.327 |
| pf04 / pf05 / pf09 | skipped (no retrieval) | | | |

On this machine, warm retrieve time is mostly rerank (about 0.5–1.0 s), then Chroma (about 70–100 ms), then embed (about 26–74 ms). Mock generate is 0–3 ms and is not representative of a live provider.

## Warnings

- Chroma printed `Failed to send telemetry event … capture() takes 1 positional argument but 3 were given` at process start. It did not fail the run.
- `psutil` is not installed, so OS RSS is unknown.
- No live-provider results exist. Do not compare this mock generate/first-token column to Groq or OpenAI.

## Limitations

- Default `LLM_PROVIDER=mock`: generate and first-token numbers are not Groq/OpenAI/Ollama latency.
- FastAPI, Mongo, cookies, SSE transport, and the React client are excluded.
- p95 with 25 samples is interpolated and not a precise tail estimate.
- Cold-start is one process-local sample.
- Stage embed/Chroma/rerank samples are 5 extra probes per retrieving scenario, not 25.
- No application code, embeddings, thresholds, or indexes were changed for this baseline.
- This is not a cost benchmark. Providers currently discard `response.usage`.

## Stop point

This increment only added the benchmark suite and recorded the mock baseline. No optimization, cache, index, threshold, or retrieval change has been made. Review these numbers before any Phase 5 performance work.
