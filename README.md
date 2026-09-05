# Medical Diagnosis Assistant using LLM + RAG

A Retrieval-Augmented Generation (RAG) system that takes a **plain-language
symptom description** and returns:

- a short list of **possible conditions**
- a **visible citation** on every medical claim
- a **triage level**: self-care / consult a doctor soon / seek emergency care
- a **rule-based safety layer** (emergency red flags + prescription/dosage refusal)
- a **citation faithfulness audit** after generation (supported / uncited / not retrieved)

This is a research and academic demo. **It is not a medical device and does
not replace a clinician.** See [Disclaimer](#disclaimer).

---

## Objectives

| # | Objective | Status |
|---|---|---|
| 1 | RAG over curated medical documents: symptom text → possible conditions with a citation on every claim | Implemented |
| 2 | Triage into three levels + safety layer (emergencies, refuse prescription/dosage) | Implemented |
| 3 | Compare general sentence embeddings vs medical embeddings (PubMedBERT) with Recall@k and MRR | Implemented |
| 4 | Measure hallucination reduction: full RAG pipeline vs the same model **without** retrieval | Implemented |

**Unique addition:** after the answer is generated, a **citation faithfulness
audit** checks every claim against the retrieved documents. Claims with no
`(Source: …)` tag, or a source that was never retrieved, are flagged.

---

## Architecture

```
User query
   │
   ▼
Safety guardrails (src/safety/guardrails.py)
   │  - prescription / dosage request?  → refuse immediately (skip RAG)
   │  - emergency red-flag keywords?    → force triage = emergency
   ▼
Retriever (src/retrieval)
   │  embed query → search Chroma → top-k passages
   │  each passage carries title, source URL, condition, triage level
   ▼
Triage classifier (src/safety/triage.py)
   │  → self_care | consult_doctor | emergency
   ▼
LLM generator (src/llm/generator.py)
   │  answer grounded ONLY in retrieved passages
   │  every condition claim must include (Source: <title>)
   ▼
Citation faithfulness audit (src/safety/citation_faithfulness.py)
   │  each claim: supported | no citation | citation not in retrieval
   │  verdict: pass | partial | fail
   ▼
DiagnosisResponse → Streamlit chat UI  and  FastAPI POST /diagnose
```

Orchestration is **custom Python** (no LangChain) so every step is inspectable
for evaluation and viva defense.

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Orchestration | Custom Python (no LangChain) | Every step is visible code, not a black-box chain |
| Embeddings (general) | `sentence-transformers/all-MiniLM-L6-v2` | Fast baseline for Objective 3 |
| Embeddings (medical) | `pritamdeka/S-PubMedBert-MS-MARCO` | PubMedBERT fine-tuned for semantic search |
| Vector store | ChromaDB (local, persistent) | Two separate indexes: general and medical |
| Language model | `mock` (offline), Groq, OpenAI, or Ollama | Mock works with no API key |
| Backend | FastAPI | Typed REST: `/diagnose`, `/health` |
| Frontend | Streamlit | Chat UI with triage, sources, faithfulness card |
| Evaluation | pandas + scikit-learn | Recall@k, MRR, precision / recall / F1, citation coverage |

---

## Project structure

```
knowledge_base/sample_documents/   20 starter medical documents (markdown + citation front matter)
src/
  config.py                        Paths and settings (reads .env)
  ingestion/loader.py              Parse documents, chunk text, attach citations
  embeddings/embedding_models.py   General vs medical embedding wrappers
  retrieval/vector_store.py        Chroma indexing + similarity search
  retrieval/retriever.py           retrieve() → list[Evidence]
  safety/guardrails.py             Emergency + prescription/dosage rules
  safety/triage.py                 Guardrails + evidence → triage level
  safety/citation_faithfulness.py  Post-generation claim vs source audit
  llm/generator.py                 mock / Groq / OpenAI / Ollama + prompts
  pipeline/rag_pipeline.py         Full flow → DiagnosisResponse
  api/main.py                      FastAPI app
app/streamlit_app.py               Chat UI
.streamlit/config.toml             UI theme
scripts/
  generate_sample_kb.py            (Re)generate the 20 starter documents
  build_index.py                   Build / rebuild both Chroma indexes
  smoke_test.py                    Quick end-to-end checks (no API key)
evaluation/
  datasets/                        Labeled test sets
  evaluate_embeddings.py           Objective 3
  evaluate_hallucination.py        Objective 4
  evaluate_triage.py               Emergency-layer recall / precision / F1
  evaluate_e2e.py                  Condition + triage accuracy
  results/                         Saved metric CSVs
tests/test_pipeline.py             Unit tests (no API key)
docs/                              Implementation notes and diagrams
```

---

## Setup

### 1. Create a virtual environment (Python 3.11 recommended)

```powershell
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

`chromadb`, `torch`, and `sentence-transformers` are most reliable on
**Python 3.11 or 3.12**. Very new Python versions may not have wheels yet.

### 2. Configure `.env`

```powershell
copy .env.example .env
```

| Setting | What to do |
|---|---|
| `LLM_PROVIDER=mock` | Works immediately, no API key. Answers are built from retrieved passages. **Use this for the first demo.** |
| `LLM_PROVIDER=groq` | Free cloud LLM. Get a key at [console.groq.com](https://console.groq.com/keys) and set `GROQ_API_KEY`. |
| `LLM_PROVIDER=openai` | Paid. Set `OPENAI_API_KEY`. |
| `LLM_PROVIDER=ollama` | Local. Install [Ollama](https://ollama.com), run `ollama pull llama3`. |
| `EMBEDDING_MODE` | `general` (default) or `medical` — which index the live app uses |
| `TOP_K` | How many passages to retrieve (default `4`) |

If `groq` or `openai` is selected but the key is still a placeholder, the app
falls back to `mock`.

### 3. Build the vector index

First run downloads the two embedding models (~500 MB) and indexes all 20
documents into **two** Chroma collections:

```powershell
python scripts\build_index.py
```

### 4. Run the app

**Windows:** double-click `run_ui.bat` (chat UI) or `run_api.bat` (REST API).

Or from a terminal:

```powershell
.\venv\Scripts\Activate.ps1
streamlit run app\streamlit_app.py
```

Open **http://localhost:8501**

FastAPI (optional; the Streamlit UI talks to the pipeline in-process):

```powershell
.\venv\Scripts\Activate.ps1
uvicorn src.api.main:app --reload --port 8000
```

- Interactive docs: http://localhost:8000/docs
- Health: `GET /health`
- Diagnose: `POST /diagnose` with `{ "query": "...", "top_k": 4 }`

Smoke test (no API key with mock):

```powershell
python scripts\smoke_test.py
```

### 5. Unit tests

```powershell
python -m pytest tests\ -v
```

---

## How to demo

Try these three queries in the chat UI:

| Query | What you should see |
|---|---|
| `I have a runny nose and sore throat for two days` | Self-care, cited conditions, faithfulness **pass** |
| `How many mg of ibuprofen should I take?` | **Refused** — no drug or dose advice |
| `Sudden crushing chest pain and shortness of breath` | **Emergency** triage, still grounded + cited |

The UI also shows retrieved sources (with relevance) and a
**Citation faithfulness audit** card after each answer.

---

## Evaluations

All scripts write to `evaluation/results/`.

```powershell
# Objective 3 — general vs medical embeddings
python evaluation\evaluate_embeddings.py

# Safety layer — emergency recall / precision / F1 (no API key)
python evaluation\evaluate_triage.py

# Objective 4 — RAG vs no-RAG citation coverage
python evaluation\evaluate_hallucination.py

# End-to-end — expected condition + triage in the final answer
python evaluation\evaluate_e2e.py
```

### Latest saved results (20-document starter corpus)

**Objective 3 — retrieval accuracy**

| Metric | General (MiniLM) | Medical (PubMedBERT) |
|---|---|---|
| Recall@1 | 95% (19/20) | 70% (14/20) |
| Recall@3 | 100% | 95% |
| MRR | 0.975 | 0.835 |

On this small corpus the **general** model retrieved the correct document more
often. That is a valid, reportable finding — Objective 3 is to **compare and
quantify**, not to assume medical embeddings always win.

**Objective 4 — hallucination (citation coverage, mock LLM)**

| Setting | Mean citation coverage |
|---|---|
| RAG | 100% |
| No retrieval | 0% |

The no-RAG side has nothing to cite. With `LLM_PROVIDER=mock` the no-RAG
answer is a fixed template. For a stronger claim, rerun
`evaluate_hallucination.py` with Groq or OpenAI (optional LLM-as-judge scores).

**Safety (emergency test set)**

- Recall on true emergencies: **100%** (12/12)
- Missed emergencies: **0**
- Prescription refusal is implemented and covered by unit tests

**End-to-end (labeled symptom → condition set)**

- Expected condition surfaced in the answer or citations: **20/20**
- Triage level match: **20/20**

---

## Suggested faculty progress checks

| Check | Date | What to show |
|---|---|---|
| Progress check 1 | 11.09.2026 | **Objective 1** — live RAG: symptom text → cited conditions + sources |
| Progress check 2 | 25.09.2026 | **Objective 2 + audit** — self-care / refuse dosage / emergency + faithfulness card |
| Progress check 3 | 09.10.2026 | **Objectives 3 and 4** — embedding table, RAG vs no-RAG coverage, limitations |

---

## Extending the knowledge base

The 20 files in `knowledge_base/sample_documents/` are **starter/demo
content** written in plain language. They are not verbatim copies of any
single source. Front matter names the organization whose public guidance
informed the text, so citations shown to the user are real, checkable
references.

For a stronger academic or clinical corpus, replace or extend these with
verified excerpts (WHO, CDC, NICE, Mayo Clinic, MedlinePlus, PubMed reviews).
Add a new `.md` file in this format:

```markdown
---
id: my_condition
title: My Condition
source: Organization Name - Page Title
url: https://example.org/my-condition
condition: My Condition
triage_level: self_care   # or consult_doctor / emergency
---

# My Condition

Body text describing symptoms, causes, self-care, and when to seek
professional or emergency care...
```

Then rebuild the indexes:

```powershell
python scripts\build_index.py
```

---

## Known limitations

- The starter knowledge base has **20 conditions**. A real system needs a
  much larger, clinically reviewed corpus.
- Emergency detection is **rule-based** (regex / keywords) on purpose, so it
  can be audited. It should be extended from missed real cases and validated
  on clinician-labeled data before any real-world use.
- With `LLM_PROVIDER=mock`, answers are assembled from retrieved document
  titles. Extra top-k hits can still appear as extra “possible” conditions.
- Objective 4 numbers above used **mock** mode. A live LLM + judge is the
  stronger hallucination experiment.
- No login, no stored patient data, not HIPAA-compliant. Research/demo only.

---

## Disclaimer

This tool provides general information retrieved from reference medical
documents. It is **not** a medical device, cannot examine you, and does
**not** replace a licensed clinician. Always consult a qualified healthcare
professional for diagnosis and treatment. If you may be experiencing a
medical emergency, call your local emergency number immediately.
