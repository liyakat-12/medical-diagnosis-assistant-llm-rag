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

**New laptop?** Start at [Run on another laptop](#run-on-another-laptop). You
need **Python 3.11**, **Node.js 18+**, this project folder, and about **10–15 minutes** plus
one model download (~500 MB). No paid API key if you keep `LLM_PROVIDER=mock`.

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
DiagnosisResponse → Express website (`/app`) via `/api/diagnose`
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
| Backend | FastAPI | Typed REST: `/diagnose`, `/health`, `/auth` |
| Frontend | Node.js + Express + Tailwind CSS | Professional login + symptom checker on port 3000 |
| Evaluation | pandas + scikit-learn | Recall@k, MRR, precision / recall / F1, citation coverage |

---

## Project structure

```
backend/                           Python FastAPI API
  src/
    config.py                      Paths and settings (reads .env)
    ingestion/loader.py            Parse documents, chunk text, attach citations
    embeddings/embedding_models.py General vs medical embedding wrappers
    retrieval/vector_store.py      Chroma indexing + similarity search
    retrieval/retriever.py         retrieve() → list[Evidence]
    safety/guardrails.py           Emergency + prescription/dosage rules
    safety/triage.py               Guardrails + evidence → triage level
    safety/citation_faithfulness.py Post-generation claim vs source audit
    llm/generator.py               mock / Groq / OpenAI / Ollama + prompts
    pipeline/rag_pipeline.py       Full flow → DiagnosisResponse
    api/main.py                    Auth, /diagnose, and chat history
frontend/                          Node.js + Express + Tailwind website
  server.js                        Serves UI and proxies /api → FastAPI
  public/                          home, login, register, chat pages
knowledge_base/sample_documents/   40 starter medical documents (markdown + citation front matter)
scripts/
  generate_sample_kb.py            (Re)generate the 40 starter documents
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

## Run on another laptop

Follow this section if you copied the project (USB, OneDrive, zip, or git clone)
onto a **different computer**.

### What you must install (before anything else)

| Need | Required? | Details |
|---|---|---|
| **Python 3.11** (or 3.12) | **Yes** | [python.org/downloads](https://www.python.org/downloads/release/python-3119/). On the installer, tick **Add python.exe to PATH**. Do **not** use Python 3.13/3.14 — `torch` / `chromadb` often fail there. |
| **pip** | Yes (comes with Python) | Check with `python -m pip --version` |
| **Internet** | Yes, **first setup only** | Downloads Python packages and two embedding models (~500 MB) |
| **RAM** | ~8 GB recommended | Embedding models load into memory on first query |
| **Disk** | ~3–4 GB free | `venv` + PyTorch + Hugging Face models |
| Git | Optional | Only if you clone from GitHub instead of copying the folder |
| Node.js / npm | **No** | This is a Python app. `npm run dev` will not work. |
| Groq / OpenAI key | **No** for first run | Keep `LLM_PROVIDER=mock` |
| Ollama | **No** unless you want a local LLM | |

**Windows extra:** if `python` is not found, use `py -3.11` instead.

**Check Python version:**

```powershell
py -3.11 --version
```

You should see `Python 3.11.x`. If the command fails, install Python 3.11 and
reopen the terminal.

### What to copy / what to leave behind

Copy the **project folder**. Do **not** copy these from the old laptop — they
are machine-specific and will break:

| Copy | Do not copy |
|---|---|
| `src/`, `frontend/`, `knowledge_base/`, `scripts/`, `evaluation/`, `tests/`, `docs/` | `venv/` — recreate it on the new laptop |
| `requirements.txt`, `README.md`, `.env.example` | `.env` — recreate from `.env.example` (never commit keys) |
| `run_web.bat`, `run_api.bat`, `run_full.bat` | `data/vector_store_*` — rebuild with `build_index.py` (optional to copy if you want to skip rebuild) |
| `frontend/package.json` | `__pycache__/`, `.pytest_cache/`, `frontend/node_modules/` |

If you use OneDrive, copy the folder locally first (Desktop or `C:\projects\...`)
so Python is not reading files through a sync lock.

### Step 1 — Open a terminal in the project folder

```powershell
cd "C:\path\to\project MEDICAL DIAGNOSIS ASSISTANT USING LLM AND RAG"
```

Confirm you see `requirements.txt` and `frontend\package.json` in that folder.

### Step 2 — Create a fresh virtual environment

**Windows (PowerShell):**

```powershell
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If activation is blocked (`running scripts is disabled`):

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then run `.\venv\Scripts\Activate.ps1` again. Your prompt should start with
`(venv)`.

**Windows (Command Prompt):**

```bat
py -3.11 -m venv venv
venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**macOS / Linux:**

```bash
python3.11 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

This installs FastAPI, sentence-transformers, ChromaDB, pandas,
scikit-learn, pytest, and the other packages listed in `requirements.txt`.
The first `pip install` can take several minutes (PyTorch is large).

### Step 3 — Create `.env`

**Windows:**

```powershell
copy .env.example .env
```

**macOS / Linux:**

```bash
cp .env.example .env
```

Leave these defaults for a first run on a new laptop:

```
LLM_PROVIDER=mock
EMBEDDING_MODE=general
TOP_K=4
```

No API key is required. Edit `.env` later only if you want Groq, OpenAI, or
Ollama (see [LLM options](#llm-options-optional)).

### Step 4 — Build the vector index (required once)

```powershell
python scripts\build_index.py
```

macOS / Linux: `python scripts/build_index.py`

This downloads two Hugging Face models (first time only, ~500 MB) and indexes
the 40 documents into:

- `data/vector_store_general/`
- `data/vector_store_medical/`

Keep the terminal open until it finishes. After this, you can run the app
offline with `LLM_PROVIDER=mock`.

### Step 5 — Run the website (Node.js + Express)

You need **two** terminals: the Python API, then the website.

**Terminal 1 — API**

```powershell
$env:PYTHONPATH = "backend"
uvicorn src.api.main:app --reload --port 8000
```

**Terminal 2 — website**

```powershell
cd frontend
npm install
npm run build:css
npm start
```

Then open **http://localhost:3000**

- Sign in with `demo@clinic.local` / `demo123`
- Or create a new account
- Open **Chat** from the navbar to describe symptoms
- Past conversations appear in the left sidebar

Windows shortcut: double-click `run_full.bat` (starts both).

The **first** symptom you type can take 30–90 seconds (embedding model loads
once). Later queries are faster.

### Step 6 — Optional checks

```powershell
python scripts\smoke_test.py
python -m pytest tests\ -v
```

### Optional — REST API notes

The website is **Express on port 3000**. It proxies `/api` to FastAPI on port 8000.

- Website: http://localhost:3000
- API docs: http://localhost:8000/docs
- Health: `GET http://localhost:8000/health`
- Login: `POST /api/auth/login` with `{ "email": "demo@clinic.local", "password": "demo123" }`
- Diagnose: `POST /api/diagnose` with header `Authorization: Bearer <token>`

### LLM options (optional)

| Setting | What to do |
|---|---|
| `LLM_PROVIDER=mock` | **Recommended on a new laptop.** Offline answers from retrieved passages. |
| `LLM_PROVIDER=groq` | Free cloud LLM. Key from [console.groq.com](https://console.groq.com/keys) → `GROQ_API_KEY` |
| `LLM_PROVIDER=openai` | Paid. Set `OPENAI_API_KEY` |
| `LLM_PROVIDER=ollama` | Install [Ollama](https://ollama.com), run `ollama pull llama3` |
| `EMBEDDING_MODE` | `general` (default) or `medical` |
| `TOP_K` | Passages to retrieve (default `4`) |

If `groq` or `openai` is set but the key is still a placeholder, the app
falls back to `mock`.

### Quick checklist

1. Install **Python 3.11** and **Node.js 18+**
2. Copy the project folder (**not** `venv/` or `frontend/node_modules/`)
3. `py -3.11 -m venv venv` → activate → `pip install -r requirements.txt`
4. `copy .env.example .env` and keep `LLM_PROVIDER=mock`
5. `python scripts\build_index.py`
6. Start API: `$env:PYTHONPATH="backend"; uvicorn src.api.main:app --port 8000`
7. Start website: `cd frontend` → `npm install` → `npm run build:css` → `npm start`
8. Open http://localhost:3000

### Troubleshooting

| Problem | Fix |
|---|---|
| `python` / `pip` not found | Use `py -3.11` and `py -3.11 -m pip`. Reinstall Python 3.11 with **Add to PATH**. |
| `Activate.ps1` cannot be loaded | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `npm` / Node not found | Install Node.js 18+ from https://nodejs.org then `cd frontend` → `npm install` |
| `torch` / `chromadb` install error | You are on Python 3.13+. Install 3.11 and recreate `venv`. |
| UI opens but first answer hangs | Normal. Models are loading. Wait up to ~2 minutes once. |
| Empty or old-looking UI | Hard-refresh the browser (Ctrl+F5). Confirm venv is active. |
| `ModuleNotFoundError` | Activate `venv`, then `pip install -r requirements.txt`. Run commands from the **project root**. |
| Retrieval / Chroma errors | Run `python scripts\build_index.py` again on this laptop. |
| Port 3000 already in use | Close the other Node window, or run `$env:PORT=3001; npm start` from `frontend/` |

---

## How to demo

Try these three queries on **http://localhost:3000**:

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

### Latest saved results (20-query evaluation set; originally measured on the 20-document corpus)

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

The 40 files in `knowledge_base/sample_documents/` are **starter/demo
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

- The starter knowledge base has **40 conditions**. A real system needs a
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
