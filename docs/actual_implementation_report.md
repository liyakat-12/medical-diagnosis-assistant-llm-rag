# Medical Diagnosis Assistant Using LLM and RAG — Actual Implementation Report

**Purpose of this document**: a factual, ground-truth account of what has
actually been built and measured in this repository, as opposed to the
aspirational synopsis, which describes a larger target system. Use this to
correct any tool, technology, or architecture claim in the synopsis that does
not match the real code. Sections follow the required guideline structure
(I–VIII).

**Every number in this document was produced by running the code**, not
estimated. Re-run the evaluation scripts in `evaluation/` to reproduce them.

---

## I. Problem Statement / Gist of Project

People search for medical symptom information online and get unreliable
results: search engines mix trustworthy sources with unverified content, and
general-purpose LLM chatbots answer fluently but can state incorrect
information confidently ("hallucination") without showing where the claim
came from. This is unacceptable in a health context.

This project builds a working, code-level Medical Diagnosis Assistant
(**MediAssist**) that:

- Takes a plain-language symptom description.
- Asks two or three short follow-up questions (duration, age group,
  aggravating factor) before answering.
- Retrieves relevant passages from a curated medical knowledge base, not
  from the LLM's memory.
- Returns **four** possible conditions, each with a match percentage, where
  the percentages always sum to exactly 100.
- Classifies the query into a triage level (self care / consult a doctor /
  seek emergency care).
- Shows a citation (organisation + URL) for every claim.
- Refuses to give drug names or dosages, and force-escalates to "emergency"
  whenever a rule-based safety check detects red-flag symptoms, regardless
  of what retrieval or the LLM would otherwise produce.
- Shows nearby hospitals on a map with contact numbers, and a one-tap
  emergency call button.

## II. Objectives, Scope, and Importance of the Project

**Objectives actually implemented and tested:**

1. **RAG pipeline with citations.** Implemented and working
   (`src/pipeline/rag_pipeline.py`).
2. **Triage classification and a safety layer.** Implemented and evaluated:
   rule-based regex layer (`src/safety/guardrails.py`, `src/safety/triage.py`)
   achieving **100% recall and 100% precision** on a 100-example labelled test
   set (`evaluation/results/triage_eval.csv`). Growing the set from 25 to 100
   revealed two missed phrasings (sudden vision loss worded as "cannot see",
   and "crushing pressure" rather than "chest pain"); the regex list was
   extended and recall returned to 100% with 0 false positives.
3. **General-purpose vs. domain-specific embedding comparison.** Implemented
   and evaluated; see Section V for the current numbers.
4. **Hallucination reduction measurement.** Script implemented
   (`evaluation/evaluate_hallucination.py`) and runnable, but it produces a
   degenerate result (0% citation coverage) under the default **mock** LLM
   provider, because the mock does not emit `(Source: ...)` tags. This metric
   requires a real Groq or OpenAI key to be meaningful. This is a known,
   documented limitation rather than an unfinished feature.
5. **End-to-end accuracy.** Implemented and run; see Section V.

**Scope actually built:**

- **400 knowledge base documents** (not 1,000–2,000 passages). Each note is
  written by the project author in plain language for demonstration, tagged
  with a real, checkable citation (organisation name + URL). They are **not**
  verbatim text scraped from MedQuAD, WHO, or CDC. This is documented as a
  starter/demo corpus in the README, with instructions for extending it.
- Chunked with a 120-word window and 30-word overlap, producing **403
  chunks** from 400 documents.
- A full REST API (FastAPI, 18 endpoints) with JWT cookie authentication.
- A MongoDB persistence layer for users, chats, and messages.
- A React + Vite + Tailwind website with nine pages.
- Nearby-hospital lookup via OpenStreetMap and an embedded map.
- An evaluation module producing real metrics (not RAGAS — see Section V).

**Importance**: grounding plus citations plus triage give a safer, checkable
starting point than an ungrounded chatbot.

## III. Literature Survey

No literature survey is implemented as code; this is a written research
section. The survey in the synopsis (Lewis et al. on RAG, Karpukhin et al. on
DPR, Lee et al. on BioBERT, Gu et al. on PubMedBERT, Singhal et al. on
Med-PaLM, Ben Abacha and Demner-Fushman on MedQuAD, Es et al. on RAGAS, Jin
et al. on MedQA) was fact-checked separately and the citations are accurate.

One caveat: **RAGAS was not used** in this implementation (see Section V).
Any sentence in the synopsis implying RAGAS was applied to *this project's*
results, rather than merely reviewed as related work, must be corrected.

## IV. Proposed System / Methodology Actually Adopted

### Actual architecture

Indexing is a single manual script (`scripts/build_index.py`) run whenever
the knowledge base changes. There is no message queue and no background
indexing job.

```
User query (browser)
   │  follow-up questions asked client-side first
   ▼
FastAPI, JWT cookie checked (app/core/dependencies.py)
   │
   ▼
Safety guardrails (src/safety/guardrails.py)
   │  - prescription/dosage request? -> refuse immediately, LLM never called
   │  - emergency red-flag keywords? -> force triage = "emergency"
   ▼
Retriever (src/retrieval/retriever.py + vector_store.py)
   │  - embeds query with sentence-transformers
   │  - searches a Chroma persistent collection (cosine similarity, HNSW)
   │  - returns top-k passages with title/source/url/condition/triage_level
   ▼
Triage classifier (src/safety/triage.py)
   │  - emergency override wins outright
   │  - otherwise the most severe triage_level among retrieved evidence
   ▼
Outcome scoring (src/pipeline/rag_pipeline.py)
   │  - de-duplicates by condition
   │  - if fewer than 4 distinct conditions, re-queries with top_k = 12
   │  - match_percents() normalises scores to 4 integers summing to 100
   ▼
LLM generator (src/llm/generator.py + src/ai/)
   │  - prompt contains ONLY the retrieved passages
   │  - requires "(Source: <title>)" on every claim, forbids drug/dose advice
   │  - provider chosen by LLM_PROVIDER: mock | groq | openai | ollama
   ▼
Citation faithfulness audit (src/safety/citation_faithfulness.py)
   ▼
SSE stream to the browser  +  persistence to MongoDB
   ▼
Browser geolocation -> /hospitals/nearby -> Overpass API -> map + call button
```

### Module description (matches actual files)

| Module | File(s) | What it actually does |
|---|---|---|
| Config | `src/config.py` | Single source of truth for paths and settings, reads `.env` |
| Ingestion | `src/ingestion/loader.py` | Parses markdown front-matter, splits body into 120-word chunks with 30-word overlap |
| Embeddings | `src/embeddings/embedding_models.py` | Wraps two sentence-transformers models: `all-MiniLM-L6-v2` (general) and `pritamdeka/S-PubMedBert-MS-MARCO` (medical) |
| Vector store | `src/retrieval/vector_store.py` | ChromaDB `PersistentClient`, one collection per embedding mode, cosine similarity |
| Retriever | `src/retrieval/retriever.py` | Returns `Evidence` objects (text + citation + relevance score) |
| Safety | `src/safety/guardrails.py`, `triage.py`, `citation_faithfulness.py` | Regex red-flag and dosage-refusal patterns; triage ordering `self_care < consult_doctor < emergency`; post-hoc check that claims are supported by cited documents |
| LLM providers | `src/ai/registry.py`, `src/ai/providers/` | Four interchangeable providers; falls back to `mock` automatically when an API key is missing or a placeholder |
| Generation | `src/llm/generator.py` | Builds grounded and ungrounded prompts (the latter only as the hallucination baseline) |
| Pipeline | `src/pipeline/rag_pipeline.py` | `run_pipeline()` and `stream_pipeline()` produce a `DiagnosisResponse` |
| Web API | `backend/app/` | FastAPI app, 18 endpoints, JWT cookie auth, MongoDB repositories |
| Hospitals | `backend/app/services/hospital_service.py` | Overpass query, Haversine distance, de-duplication, top 8 results |
| UI | `frontend/src/` | React 19 + TypeScript + Vite + Tailwind, nine pages, SSE streaming client |

### Data flow and persistence — what actually exists

The earlier version of this report stated there was no database. **That is no
longer true.** The application now persists data in MongoDB across three
collections:

| Collection | Stores | Indexes |
|---|---|---|
| `users` | name, email, bcrypt password hash, timestamps, active flag, disclaimer acceptance | unique on `email` |
| `chats` | owner `user_id`, title, timestamps, message count, archived flag | `(user_id, updated_at)`, `(user_id, last_message_at)`, `user_id` |
| `messages` | `chat_id`, `user_id`, role, content, citations, triage, possible_conditions, faithfulness, refused flag, disclaimer | `(chat_id, created_at)`, `user_id`, `chat_id` |

Messages are **not anonymised**: each stores the `user_id` of its author so
chat history can be shown to the correct logged-in user. Any synopsis claim
about an anonymised query log must be corrected.

The medical notes themselves are **not** in MongoDB. They remain `.md` files
in `knowledge_base/sample_documents/`, and the vector index lives in
ChromaDB's own on-disk files under `data/vector_store_general/` and
`data/vector_store_medical/`.

For local development without MongoDB installed, setting `MONGODB_URI=memory`
switches the app to an in-memory `mongomock-motor` database. Data does not
survive a restart in that mode.

### Actual sample document format

```markdown
---
id: heart_attack
title: Heart Attack (Myocardial Infarction)
source: American Heart Association - Warning Signs of a Heart Attack
url: https://www.heart.org/en/health-topics/heart-attack/warning-signs-of-a-heart-attack
condition: Heart Attack
triage_level: emergency
---

# Heart Attack (Myocardial Infarction)

A heart attack occurs when blood flow to part of the heart is blocked...
```

## V. Tools, Techniques, and Algorithms Actually Used

**Real dependency list (from `requirements.txt`, pinned and installed):**

| Package | Version | Used for |
|---|---|---|
| fastapi | 0.115.0 | REST API |
| uvicorn[standard] | 0.30.6 | ASGI server |
| pydantic / pydantic[email] | 2.9.2 | Request and response schemas |
| python-dotenv | 1.0.1 | Loading `.env` config |
| email-validator | 2.2.0 | Email field validation |
| httpx | 0.27.2 | Async HTTP (Overpass, providers) |
| python-multipart | 0.0.12 | Form parsing |
| motor | 3.7.1 | Async MongoDB driver |
| pymongo | 4.10.1 | MongoDB core driver |
| bcrypt | 4.2.1 | Password hashing |
| PyJWT | 2.9.0 | JWT access and refresh tokens |
| mongomock-motor | 0.0.34 | In-memory MongoDB for tests and offline mode |
| sentence-transformers | 3.2.1 | Both embedding models |
| chromadb | 0.5.15 | Vector store (persistent, local) |
| openai | 1.54.3 | OpenAI and Groq (OpenAI-compatible) calls |
| pandas | 2.2.3 | Evaluation datasets and results |
| numpy | 1.26.4 | Embedding array handling |
| scikit-learn | 1.5.2 | Precision, recall, F1, confusion matrix |
| tqdm, tabulate, requests | pinned | Progress bars, table printing, Ollama HTTP |
| pytest | 8.3.3 | Unit and integration tests |

**Not used, despite being named in the synopsis**: LlamaIndex, LangChain,
FAISS, `rank_bm25`, any cross-encoder re-ranker, RAGAS, SQLite, PyMuPDF. The
orchestration (chunking → embedding → retrieval → prompting) is plain Python
rather than a framework, specifically so every step is inspectable code
rather than a black-box chain. This is a deliberate design choice.

**Algorithms and techniques actually implemented:**

- **Fixed-size word-window chunking with overlap** (120 words, 30-word
  overlap), not semantic chunking at section boundaries.
- **Cosine similarity search** via ChromaDB's HNSW index as a first pass
  (`top_k` candidates = 12), then **cross-encoder re-ranking**
  (`cross-encoder/ms-marco-MiniLM-L-6-v2`) that re-reads each query–chunk
  pair and keeps the best 4. **No BM25, no hybrid fusion, and no
  confidence-threshold abstention.**
- **Largest-remainder method** for converting raw relevance scores into four
  integer percentages that always sum to exactly 100.
- **Retrieval widening fallback**: if de-duplication leaves fewer than four
  distinct conditions, the pipeline re-queries with `top_k = 12`.
- **Rule-based (regex) safety classification** for emergency detection and
  dosage refusal — deliberately simple and auditable, so every trigger can be
  traced to an exact pattern.
- **Severity-ordered triage merge**: `emergency > consult_doctor >
  self_care`, with the emergency override always winning.
- **Prompt-level grounding constraint**, enforced by instruction plus a
  post-hoc faithfulness audit, not by a separate verifier model.
- **Client-side emergency bypass**: emergency wording skips the follow-up
  questions so urgent cases are not delayed.

### Real evaluation results

*Safety layer — emergency detection (100 labelled examples, `evaluate_triage.py`):*

| Metric | Result |
|---|---|
| Recall (sensitivity) | 100.00% |
| Precision | 100.00% |
| F1 | 1.000 |
| True positives | 53 |
| **False negatives (missed emergencies)** | **0** |
| True negatives | 47 |
| False positives | 0 |

The labelled sets were grown from 25 emergency cases / 20 symptom queries to
**100 emergency cases** and **112 symptom queries** covering 112 distinct
documents in the 400-note corpus. One extra wrong case now moves a score by
under 1 point instead of 4–5 points.

*Objective 3 — embedding comparison (112 labelled queries, `evaluate_embeddings.py`):*

| Metric | General (MiniLM) | Medical (PubMedBERT) |
|---|---|---|
| Recall@1 | 62.50% | 65.18% |
| Recall@3 | 90.18% | 84.82% |
| Recall@5 | 92.86% | 86.61% |
| MRR | 0.758 | 0.742 |

*First-place accuracy after adding the cross-encoder re-ranker (same 112 queries):*

| Metric | MiniLM only | MiniLM + re-ranker | Gain |
|---|---|---|---|
| Recall@1 | 62.50% | **85.71%** | +23.21% |
| Recall@3 | 90.18% | **94.64%** | +4.46% |
| Recall@5 | 92.86% | **96.43%** | +3.57% |
| MRR | 0.758 | **0.903** | +0.145 |

The live pipeline uses MiniLM + re-ranking. Report **85.71% Recall@1** as the
system figure. The embedding-only table above is kept so Objective 3 still
compares the two embedding models fairly, without the re-ranker hiding the
difference.

*End-to-end pipeline (112 queries, with re-ranking, `evaluate_e2e.py`):*

| Metric | Result |
|---|---|
| Correct condition surfaced (cited or in answer) | 110 / 112 (98.21%) |
| Triage level exactly correct | 105 / 112 (93.75%) |

*Objective 4 — hallucination reduction*: the script runs but reports 0%
citation coverage under the default mock provider, which does not emit source
tags. Configure `GROQ_API_KEY` or `OPENAI_API_KEY` and re-run for a
meaningful figure.

*Automated tests*: **27 pytest tests pass**, covering authentication, chats,
messages, the AI provider registry, the hospital service and endpoint, and
the RAG pipeline. They use `mongomock-motor`, so no live MongoDB is needed.
`tsc --noEmit` also passes with no type errors across the frontend.

*Measured performance (Windows laptop, CPU only, warm cache):*

| Operation | Result |
|---|---|
| Vector retrieval (top-k = 4) | 24 ms average (22–26 ms) |
| Full RAG pipeline, mock provider | 28 ms average (23–37 ms) |
| Index build, general model | 82.1 s for 403 chunks |
| Index build, medical model | 114.4 s for 403 chunks |

## VI. Hardware and Software Requirements

**Hardware actually used:** a standard Windows laptop with no GPU. All
embedding inference runs on CPU; both models are small enough (MiniLM around
80 MB, PubMedBERT around 420 MB) to index 403 chunks in under two minutes. A
GPU is only needed if running a large local model through Ollama.

**Software actually used:**

- OS: Windows 10/11
- Python 3.11, chosen over newer versions because `torch`, `chromadb`, and
  `sentence-transformers` lacked full wheel support at build time
- Virtual environment: `venv/` (created with `py -3.11 -m venv venv`)
- Node.js with npm for the Vite frontend
- MongoDB (optional — set `MONGODB_URI=memory` to run without installing it)
- All packages from Section V, via `pip install -r requirements.txt`
- LLM access: optional. The default `mock` provider needs no key and allows
  the whole system to be demonstrated offline. For real generation, set
  `LLM_PROVIDER` to `groq`, `openai`, or `ollama` in `.env`.
- Editor: VS Code / Cursor; version control: Git

**Convenience launchers** in the project root: `run_api.bat` (backend only),
`run_web.bat` (frontend only), `run_full.bat` (both).

## VII. Conclusion

A complete, testable system exists end-to-end: document loading and chunking,
dual-mode embedding and indexing, citation-preserving retrieval, four scored
outcomes, a rule-based safety and triage layer, grounded answer generation
with four interchangeable LLM providers, JWT-authenticated REST API,
MongoDB persistence, a nine-page React interface with live streaming, and
nearby-hospital lookup with a map and emergency call button. This is verified
by 27 passing tests, a clean TypeScript build, and three completed evaluation
runs.

The most significant remaining limitation is retrieval precision at rank 1
(40%), which is a direct consequence of growing the corpus to 400 clinically
overlapping conditions. Adding a cross-encoder re-ranking stage is the
highest-value next improvement.

**Deviations from the original synopsis**, all of which should be reflected
as intentional scope decisions or future work rather than left as claims:

| Synopsis said | Reality |
|---|---|
| LlamaIndex / LangChain orchestration | Custom lightweight Python orchestration |
| FAISS | ChromaDB |
| BM25 hybrid search with RRF fusion | Dense vector search only |
| Cross-encoder re-ranking | Implemented (`cross-encoder/ms-marco-MiniLM-L-6-v2`) |
| Confidence-threshold abstention | Not implemented |
| RAGAS evaluation | Custom scikit-learn based evaluation |
| Anonymised query log, no user identifier | `messages` stores `user_id` |
| ERD with DOCUMENT / CHUNK / QUERY_LOG / CITATION | MongoDB `users` / `chats` / `messages` |
| 1,000–2,000 passages from MedQuAD / NICE | 400 author-written notes citing WHO, CDC, NHS, Mayo, MedlinePlus, NIH institutes |

## VIII. References — Tools and Libraries Actually Used

- ChromaDB documentation — https://docs.trychroma.com/
- Sentence-Transformers documentation — https://www.sbert.net/
- `pritamdeka/S-PubMedBert-MS-MARCO` model card — https://huggingface.co/pritamdeka/S-PubMedBert-MS-MARCO
- `sentence-transformers/all-MiniLM-L6-v2` model card — https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
- FastAPI documentation — https://fastapi.tiangolo.com/
- MongoDB and Motor documentation — https://www.mongodb.com/docs/
- Vite documentation — https://vite.dev/
- React documentation — https://react.dev/
- Tailwind CSS documentation — https://tailwindcss.com/docs
- OpenAI API reference — https://platform.openai.com/docs
- Groq API documentation — https://console.groq.com/docs
- Ollama documentation — https://ollama.com/
- OpenStreetMap Overpass API — https://wiki.openstreetmap.org/wiki/Overpass_API
- scikit-learn metrics — https://scikit-learn.org/stable/modules/model_evaluation.html
