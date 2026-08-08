# Medical Diagnosis Assistant using LLM + RAG

A Retrieval-Augmented Generation (RAG) system that takes a plain-language
symptom description and returns a short, **cited** list of possible
conditions, together with a **triage level** (self care / consult a doctor
soon / seek emergency care) and a rule-based **safety layer** that detects
emergencies and refuses prescription/dosage requests.

This project was built to satisfy four objectives:

1. Build a RAG pipeline over a curated collection of trusted medical
   documents so a symptom description returns possible conditions with a
   visible citation on every claim.
2. Classify each query into a triage level and enforce a safety layer that
   detects emergencies and refuses prescription/dosage requests.
3. Compare retrieval accuracy of general-purpose sentence embeddings vs.
   domain-specific medical embeddings (PubMedBERT), reported quantitatively.
4. Measure the reduction in hallucination from grounding the LLM in
   retrieved documents vs. the same LLM with no retrieval.

> **This is not a medical device and does not replace a doctor.** See
> [Disclaimer](#disclaimer) below.

## Architecture

```
User query
   │
   ▼
Safety guardrails (src/safety/guardrails.py)
   │  - prescription/dosage request?  -> refuse immediately
   │  - emergency red-flag keywords?  -> force triage = emergency
   ▼
Retriever (src/retrieval) -- embeds query, searches Chroma vector store
   │  -> top-k cited passages, each tagged with its condition + triage level
   ▼
Triage classifier (src/safety/triage.py)
   │  -> self_care | consult_doctor | emergency
   ▼
LLM generator (src/llm/generator.py)
   │  -> answer grounded ONLY in retrieved passages, citation required
   ▼
DiagnosisResponse -> FastAPI (/diagnose) and Streamlit chat UI
```

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Orchestration | Custom Python (no LangChain) | Fully transparent for evaluation/defense - every step is inspectable code, not a black-box chain |
| Embeddings (general) | `sentence-transformers/all-MiniLM-L6-v2` | Fast, free, strong general-purpose baseline |
| Embeddings (medical) | `pritamdeka/S-PubMedBert-MS-MARCO` | PubMedBERT fine-tuned for semantic search - domain comparison target |
| Vector store | ChromaDB (persistent, local) | Free, zero-config, good for small/medium corpora |
| LLM | OpenAI (`gpt-4o-mini`) or local Ollama (`llama3`) | Switch providers via one `.env` variable |
| Backend | FastAPI | Simple typed REST API |
| Frontend | Streamlit | Fast chat UI, pure Python |
| Evaluation | pandas + scikit-learn | Recall@k, MRR, precision/recall/F1, citation coverage |

## Project structure

```
knowledge_base/sample_documents/   20 starter medical documents (markdown, with citation front-matter)
src/
  config.py                       All paths & settings (reads .env)
  ingestion/loader.py              Parses documents, chunks text, attaches citations
  embeddings/embedding_models.py   General vs. medical embedding model wrappers
  retrieval/vector_store.py        Chroma indexing + similarity search
  retrieval/retriever.py           High-level retrieve() -> list[Evidence]
  safety/guardrails.py             Emergency + prescription/dosage regex rules
  safety/triage.py                 Combines guardrails + evidence -> triage level
  llm/generator.py                 OpenAI / Ollama call wrapper + prompts
  pipeline/rag_pipeline.py         Ties it all together -> DiagnosisResponse
  api/main.py                      FastAPI app (/diagnose, /health)
app/streamlit_app.py               Chat UI
scripts/
  generate_sample_kb.py            (Re)generates the 20 starter KB documents
  build_index.py                   Builds/rebuilds the Chroma vector stores
evaluation/
  datasets/                        Labeled test sets (emergency, symptom->condition, hallucination Qs)
  evaluate_embeddings.py           Objective 3
  evaluate_hallucination.py        Objective 4
  evaluate_triage.py               Safety-layer recall/precision/F1
  evaluate_e2e.py                  End-to-end condition + triage accuracy
tests/test_pipeline.py             Unit tests (no API key required)
```

## Setup

### 1. Create a virtual environment (Python 3.11 recommended)

```powershell
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> Windows note: `chromadb`, `torch`, and `sentence-transformers` do not yet
> have full wheel support on very new Python versions. Python 3.11 or 3.12
> is the safest choice.

### 2. Configure your `.env`

```powershell
copy .env.example .env
```

Then edit `.env`:

- To use **OpenAI** (recommended, best quality): set `LLM_PROVIDER=openai`
  and put your key in `OPENAI_API_KEY`.
- To use a **free local model** instead: install [Ollama](https://ollama.com),
  run `ollama pull llama3`, and set `LLM_PROVIDER=ollama`.

### 3. Build the vector index

This downloads the two embedding models (first run only, ~500MB) and
indexes all 20 sample documents into two separate Chroma collections:

```powershell
python scripts\build_index.py
```

### 4. Run the app

FastAPI backend:

```powershell
uvicorn src.api.main:app --reload --port 8000
```

Streamlit chat UI (in a second terminal; works standalone too, no need to
run the API separately):

```powershell
streamlit run app\streamlit_app.py
```

### 5. Run the unit tests (no API key required)

```powershell
python -m pytest tests\ -v
```

## Running the evaluations (Objectives 3 and 4, plus safety-layer checks)

All results are written to `evaluation/results/`.

```powershell
# Objective 3: general vs. medical embeddings retrieval accuracy
python evaluation\evaluate_embeddings.py

# Safety layer: emergency-detection recall/precision/F1 (no API key needed)
python evaluation\evaluate_triage.py

# Objective 4: hallucination reduction, RAG vs. no-RAG (needs an LLM configured)
python evaluation\evaluate_hallucination.py

# End-to-end: does the final answer surface the right condition + triage level?
python evaluation\evaluate_e2e.py
```

## Extending the knowledge base

The 20 documents in `knowledge_base/sample_documents/` are **starter/demo
content** written in plain language for this project, not verbatim copies
of any single source. Each file's front matter names the organization
whose public guidance informed it, so every citation shown to the user is
a real, checkable reference.

For a production system or a more rigorous academic submission, replace or
extend these with verified excerpts from real guideline documents (WHO,
CDC, NICE, Mayo Clinic, MedlinePlus, PubMed review articles, etc.). To add
a new document, create a new `.md` file following this format:

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

Then re-run `python scripts\build_index.py` to re-index.

## Known limitations / suggested next steps

- The starter knowledge base has 20 conditions; real deployments need a
  much larger, clinically-reviewed corpus.
- The emergency-detection safety layer is rule-based (regex/keywords) for
  auditability; it should be periodically reviewed and extended with real
  missed cases, and ideally validated against clinician-labeled data at
  scale before any real-world use.
- No user data persistence/authentication is implemented — this is a
  research/demo-grade pipeline, not a HIPAA-compliant clinical system.

## Disclaimer

This tool provides general information retrieved from reference medical
documents. It is **not** a medical device, cannot examine you, and does
**not** replace a licensed clinician. Always consult a qualified
healthcare professional for diagnosis and treatment. If you may be
experiencing a medical emergency, call your local emergency number
immediately.
