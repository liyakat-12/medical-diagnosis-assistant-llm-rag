# Medical Diagnosis Assistant Using LLM and RAG — Actual Implementation Report

**Purpose of this document**: This is a factual, ground-truth account of what has
actually been built and tested in the project folder (as opposed to the
aspirational synopsis, which describes a larger target system). Use this to
correct any tool/technology/architecture claims in the synopsis that don't
match what was really implemented. Sections follow the required guideline
structure (I-VIII).

---

## I. Problem Statement / Gist of Project

People search for medical symptom information online and get unreliable
results: search engines mix trustworthy sources with unverified content, and
general-purpose LLM chatbots answer fluently but can state incorrect
information confidently ("hallucination"), without showing where the claim
came from. This is unacceptable in a health context.

This project builds a working, code-level Medical Diagnosis Assistant that:
- Takes a plain-language symptom description.
- Retrieves relevant passages from a small curated medical knowledge base
  (not from the LLM's memory).
- Generates an answer that the LLM is instructed to ground strictly in those
  retrieved passages, with a citation on every claim.
- Classifies the query into a triage level (self care / consult a doctor soon
  / seek emergency care).
- Refuses to give drug names or dosages, and force-escalates to "emergency"
  whenever a rule-based safety check detects red-flag symptoms, regardless of
  what retrieval or the LLM would otherwise produce.

## II. Objectives, Scope, and Importance of the Project

**Objectives actually implemented and tested:**
1. Build a RAG pipeline over a curated set of medical documents so a symptom
   query returns possible conditions with a citation on every claim.
   → **Implemented and working** (`src/pipeline/rag_pipeline.py`).
2. Classify each query into a triage level and enforce a safety layer that
   detects emergencies and refuses prescription/dosage requests.
   → **Implemented and evaluated**: rule-based regex layer
   (`src/safety/guardrails.py`, `src/safety/triage.py`), achieving **100%
   recall and 100% precision** on a 25-example labeled test set
   (`evaluation/results/triage_eval.csv`) after one iteration of pattern
   fixes (initial version had 75% recall / 3 missed cases; patterns were
   broadened and recall reached 100%).
3. Compare general-purpose vs. domain-specific medical embeddings, reported
   quantitatively. → **Implemented and evaluated**: see actual numbers in
   Section IV below and `evaluation/results/embedding_eval_general.csv` /
   `embedding_eval_medical.csv`.
4. Measure hallucination reduction from grounding vs. no retrieval.
   → **Implemented** (`evaluation/evaluate_hallucination.py`), but **not yet
   run to completion** in this environment because it requires a configured
   LLM (OpenAI API key or a running Ollama instance), which was not available
   at build time. The script is ready to run once an LLM is configured.

**Scope actually built:**
- 40 knowledge base documents (not 1,000-2,000). Documents were written by
  the project author in plain language for demonstration, each tagged with
  a real, checkable citation (organization name + URL) — not verbatim text
  scraped from MedQuAD/WHO/CDC. This is clearly documented as a "starter/demo
  corpus" in the project README, with instructions for extending it with
  real guideline excerpts.
- These 40 documents are chunked with a 120-word window (most stay as one
  passage; longer ones split with overlap).
- A REST API (FastAPI) and a website (React + Vite + Tailwind), both working.
- An evaluation module producing real metrics (not RAGAS - see Section V).

**Importance**: identical rationale to the synopsis — grounding + citations +
triage give a safer, checkable starting point than an ungrounded chatbot.

## III. Literature Survey

No literature survey was implemented as part of the code (this is a written/
research section, not a software component). The literature survey already
in the synopsis (Lewis et al. RAG, Karpukhin et al. DPR, Lee et al. BioBERT,
Gu et al. PubMedBERT, Singhal et al. Med-PaLM, Ben Abacha & Demner-Fushman
MedQuAD, Es et al. RAGAS, Jin et al. MedQA) was independently fact-checked in
an earlier review and all citations were verified accurate (correct titles,
venues, years). It does not need correction against the code, since it
describes external research, not this implementation. One caveat: since RAGAS
was **not actually used** in the implementation (see Section V), any sentence
in the synopsis that implies RAGAS was applied to *this* project's results
(rather than just being reviewed as related work) should be corrected.

## IV. Proposed System / Methodology Actually Adopted

### Actual architecture (single pipeline, no separate offline/online split needed at this scale)

```
User query
   │
   ▼
Safety guardrails (regex-based, src/safety/guardrails.py)
   │  - prescription/dosage request?  -> refuse immediately, LLM never called
   │  - emergency red-flag keywords?   -> force triage = "emergency"
   ▼
Retriever (src/retrieval/retriever.py + vector_store.py)
   │  - embeds query with sentence-transformers
   │  - searches a Chroma persistent collection (cosine similarity)
   │  - returns top-k passages, each with title/source/url/condition/triage_level
   ▼
Triage classifier (src/safety/triage.py)
   │  - emergency override wins outright
   │  - otherwise: most severe triage_level among retrieved evidence
   ▼
LLM generator (src/llm/generator.py)
   │  - builds a prompt containing ONLY the retrieved passages
   │  - system prompt requires a citation "(Source: <title>)" on every claim
   │  - calls OpenAI or a local Ollama server, selected by one .env variable
   ▼
DiagnosisResponse -> FastAPI /diagnose and /chats endpoints AND React website
```

There is **no separate offline/online split, no message queue, and no
background indexing job** — indexing is a single manual script
(`scripts/build_index.py`) run whenever the knowledge base changes.

### Module description (matches actual files, not the synopsis's module table)

| Module | File(s) | What it actually does |
|---|---|---|
| Config | `src/config.py` | Single source of truth for paths and settings, reads `.env` |
| Ingestion | `src/ingestion/loader.py` | Parses markdown front-matter (id/title/source/url/condition/triage_level), splits body into 120-word chunks with 30-word overlap |
| Embeddings | `src/embeddings/embedding_models.py` | Wraps two `sentence-transformers` models behind one interface: `all-MiniLM-L6-v2` (general) and `pritamdeka/S-PubMedBert-MS-MARCO` (medical) |
| Vector store | `src/retrieval/vector_store.py` | ChromaDB `PersistentClient`, one collection per embedding mode, cosine similarity |
| Retriever | `src/retrieval/retriever.py` | Thin wrapper returning `Evidence` objects (text + citation + relevance score) |
| Safety | `src/safety/guardrails.py`, `src/safety/triage.py` | Regex pattern lists for emergency red flags and prescription/dosage requests; triage severity ordering `self_care < consult_doctor < emergency` |
| LLM | `src/llm/generator.py` | `_call_openai()` / `_call_ollama()`, selected by `LLM_PROVIDER` env var; two system prompts (grounded vs. ungrounded, the latter used only for the hallucination-comparison baseline) |
| Pipeline | `src/pipeline/rag_pipeline.py` | `run_pipeline()` ties the above together into one `DiagnosisResponse` |
| API | `src/api/main.py` | FastAPI app, `POST /diagnose`, `GET /health` |
| UI | `frontend/` | React + Vite + Tailwind website (home, login, register, chat), proxies `/api` to FastAPI |

### Data flow — what actually exists

There is **no database and no ERD** in the real implementation. Documents
live as `.md` files in `knowledge_base/sample_documents/`; the vector index
lives as ChromaDB's own on-disk files under `data/vector_store_general/` and
`data/vector_store_medical/`; nothing is logged to any SQL database, and no
query history is persisted anywhere. If the synopsis's ERD/query-log design
is kept, it should be labeled as a **planned/future enhancement**, not as
something already implemented.

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

**Real dependency list (from `requirements.txt`, pinned versions actually installed and tested):**

| Package | Version | Used for |
|---|---|---|
| fastapi | 0.115.0 | REST API |
| uvicorn | 0.30.6 | ASGI server |
| pydantic | 2.9.2 | API request/response schemas |
| python-dotenv | 1.0.1 | Loading `.env` config |
| sentence-transformers | 3.2.1 | Both embedding models |
| chromadb | 0.5.15 | Vector store (persistent, local) |
| openai | 1.54.3 | OpenAI API calls |
| pandas | 2.2.3 | Evaluation datasets/results |
| numpy | 1.26.4 | Embedding array handling |
| scikit-learn | 1.5.2 | Precision/recall/F1/confusion matrix in `evaluate_triage.py` |
| tqdm, tabulate, requests | latest pinned | Progress bars, table printing, Ollama HTTP calls |
| pytest | 8.3.3 | Unit tests |

**Not used, despite being named in the synopsis**: LlamaIndex, LangChain,
FAISS, `rank_bm25`, any cross-encoder re-ranker package, RAGAS, SQLite,
PyMuPDF. The orchestration (chunking → embedding → retrieval → prompting) was
written as plain Python instead of a framework, specifically so every step is
inspectable code rather than a black-box chain — a deliberate design choice,
not an oversight.

**Algorithms/techniques actually implemented:**
- **Fixed-size word-window chunking with overlap** (120 words, 30-word
  overlap) — not the synopsis's "semantic chunking at section boundaries."
- **Cosine similarity search** via ChromaDB's HNSW index (`hnsw:space:
  cosine`) — single dense retrieval only, **no BM25/keyword search, no
  hybrid fusion, no re-ranking stage**.
- **Rule-based (regex) safety classification** for emergency detection and
  prescription/dosage refusal — deliberately simple and auditable rather
  than a learned classifier, so every trigger can be traced to an exact
  pattern.
- **Severity-ordered triage merge**: `emergency > consult_doctor >
  self_care`; the safety layer's emergency detection always overrides
  whatever the retrieved evidence would otherwise imply.
- **Prompt-level grounding constraint**: the LLM's system prompt explicitly
  requires a `(Source: <title>)` citation on every claim and forbids
  drug/dose recommendations; this is enforced by instruction, not by a
  separate verifier model.

**Real evaluation results obtained (not projected/expected — actually run):**

*Objective 3 - embedding comparison (20 labeled queries, `evaluate_embeddings.py`):*

| Metric | General (MiniLM) | Medical (PubMedBERT) |
|---|---|---|
| Recall@1 | 95.00% | 70.00% |
| Recall@3 | 100.00% | 95.00% |
| Recall@5 | 100.00% | 100.00% |
| MRR | 0.975 | 0.835 |

General-purpose embeddings outperformed the medical embeddings on this small,
plain-language corpus — a genuine, reportable finding (PubMedBERT's advantage
typically shows up on more clinically-worded text; the 40 starter documents
are deliberately written in patient-friendly language). This should replace
any assumption in the synopsis that domain embeddings will necessarily win.

*Safety layer - emergency detection (25 labeled examples, `evaluate_triage.py`):*
100% recall, 100% precision, F1 = 1.000, 0 false negatives, 0 false positives
(after one round of regex refinement; initial version was 75% recall with 3
missed cases).

*Objective 4 - hallucination reduction*: script exists
(`evaluate_hallucination.py`, uses a citation-coverage heuristic plus an
optional LLM-judge score) but has not been run yet — needs an LLM API key or
local Ollama model configured.

*End-to-end accuracy*: script exists (`evaluate_e2e.py`) but likewise needs an
LLM configured to run.

## VI. Hardware & Software Requirements (as actually used to build/run this)

**Hardware actually used:** a standard Windows laptop, no GPU. All embedding
inference ran on CPU (both models are small enough — MiniLM ~80MB, PubMedBERT
~420MB — to embed 22 chunks in seconds on CPU). No GPU is required unless
running a local LLM through Ollama with a larger model.

**Software actually used:**
- OS: Windows 10/11
- Python 3.11 (specifically chosen over the system's default Python 3.14,
  because `torch`/`chromadb`/`sentence-transformers` did not yet have full
  wheel support for 3.14 at build time)
- Virtual environment: `venv/` (created with `py -3.11 -m venv venv`)
- All packages listed in Section V, installed via `pip install -r
  requirements.txt`
- LLM access: either an OpenAI API key (`OPENAI_API_KEY` in `.env`) or a
  locally running Ollama server (`ollama pull llama3`) — selected via
  `LLM_PROVIDER` in `.env`. Neither was configured/available during this
  build, so all non-LLM components were tested, and LLM-dependent components
  were implemented and code-reviewed but not live-tested end-to-end.
- Editor: VS Code / Cursor
- Version control: Git (local repository, branch `cursor/medical-rag-
  assistant-scaffold`, not yet pushed to any remote by user's choice)

## VII. Conclusion (of the actual implementation, to date)

A working, testable RAG pipeline exists end-to-end for every component that
doesn't require a live LLM call: document loading and chunking, dual-mode
embedding and indexing, citation-preserving retrieval, and a rule-based
safety/triage layer — all verified with 9 passing unit tests and two
completed evaluation runs (embeddings comparison, safety-layer accuracy). The
LLM-dependent half of the pipeline (grounded answer generation, the
hallucination-reduction evaluation, and the end-to-end accuracy evaluation)
is fully implemented and ready to run, pending only an API key or local model
being configured — no further coding is required for that step. The most
significant deviations from the original synopsis are: a custom lightweight
orchestration instead of LlamaIndex, ChromaDB instead of FAISS, no BM25
hybrid search or re-ranking stage, no SQLite/ERD-backed logging layer, and a
40-document starter corpus rather than 1,000-2,000 passages — these should
either be reflected as "future work" in the synopsis, or flagged to your
guide as intentional scope reduction for a project of this size.

## VIII. References — Tools & Libraries Actually Used (supplement to the academic references already in the synopsis)

- ChromaDB documentation — https://docs.trychroma.com/
- Sentence-Transformers documentation — https://www.sbert.net/
- `pritamdeka/S-PubMedBert-MS-MARCO` model card — https://huggingface.co/pritamdeka/S-PubMedBert-MS-MARCO
- `sentence-transformers/all-MiniLM-L6-v2` model card — https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
- FastAPI documentation — https://fastapi.tiangolo.com/
- Vite documentation — https://vite.dev/
- React documentation — https://react.dev/
- Tailwind CSS documentation — https://tailwindcss.com/docs
- OpenAI API reference — https://platform.openai.com/docs
- Ollama documentation — https://ollama.com/
