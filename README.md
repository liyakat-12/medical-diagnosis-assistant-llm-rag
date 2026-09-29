# MediAssist — Medical Diagnosis Assistant using LLM + RAG

MediAssist is a research and academic medical information assistant. It takes a **plain-language symptom description**, retrieves matching passages from a curated markdown knowledge base, applies **safety and triage rules**, and returns a **grounded answer with citations**.

This is **not** a medical device and **does not** replace a clinician. It does not make a definitive diagnosis, prescribe medication, or give drug doses.

---

## Features

- React + TypeScript chat UI with persistent conversation history
- FastAPI backend with JWT authentication in HTTP-only cookies
- MongoDB storage for users, chats, and messages
- Retrieval-Augmented Generation over 200 curated medical notes
- Sentence-transformer embeddings and ChromaDB vector search
- General and medical embedding modes
- Safety guardrails, emergency detection, and prescription/dosage refusal
- Triage labels: self-care, consult a doctor, emergency
- Citation generation and citation-faithfulness auditing
- Pluggable LLM providers: mock, Groq, OpenAI, Ollama
- Token/chunk streaming over Server-Sent Events
- Evaluation scripts for embeddings, triage, hallucination, and end-to-end quality

---

## Screenshots

Add product screenshots here after a local run:

- Landing page
- Login / register
- Chat with triage banner and citations
- Conversation sidebar on desktop and mobile

---

## Architecture

```
Browser (http://localhost:5173)
    │  cookie auth, SSE stream
    ▼
FastAPI (http://localhost:8000/api/v1)
    ├── Auth / users          → MongoDB
    ├── Chats / messages      → MongoDB
    └── Diagnosis / stream
            │
            ▼
        RAG pipeline (backend/src)
            user query
            → safety checks
            → ChromaDB retrieval
            → triage
            → LLM provider (mock | groq | openai | ollama)
            → citations
            → faithfulness audit
            → streamed + stored assistant message
```

The application never answers from the model alone in the live chat. Retrieval, triage, and guardrails stay in the path.

---

## Technology stack

**Frontend:** React 19, TypeScript, Vite, Tailwind CSS, React Router, Context API, Lucide icons, React Markdown

**Backend:** FastAPI, Pydantic, Motor (async MongoDB), bcrypt, PyJWT

**AI / RAG:** ChromaDB, sentence-transformers, existing retrieval + safety modules, provider registry

**Database:** MongoDB for accounts and conversations; ChromaDB on disk for vectors

---

## Folder structure

```
project-root/
├── backend/
│   ├── app/
│   │   ├── api/              # HTTP routes
│   │   ├── core/             # config, security, errors
│   │   ├── connection/       # MongoDB client and indexes
│   │   ├── models/           # user, chat, message documents
│   │   ├── repositories/     # database queries
│   │   ├── schemas/          # API request/response models
│   │   └── services/         # auth, chat, RAG orchestration
│   └── src/                  # RAG, embeddings, retrieval, safety, LLM providers
├── frontend/                 # Vite + React + TypeScript
├── knowledge_base/           # Curated markdown documents
├── data/                     # Local Chroma indexes (gitignored)
├── evaluation/               # Datasets and scoring scripts
├── scripts/                  # Index build and smoke tests
├── tests/                    # Pytest suite
├── README.md
└── TECHNICAL_README.md
```

---

## AI / RAG flow

1. Safety pre-check on the raw query (prescription/dosage refusal; emergency flags).
2. Retrieve top-k passages from ChromaDB using the configured embedding mode.
3. Classify triage from the query and retrieved evidence (emergency override when red flags fire).
4. Generate an answer that may only use retrieved context.
5. Attach citations and run the citation-faithfulness audit.
6. Stream tokens to the browser, then persist the final assistant message in MongoDB.

---

## Authentication

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/refresh`

Passwords are hashed with bcrypt. Access and refresh JWTs are stored in HTTP-only cookies (`mediassist_access`, `mediassist_refresh`). The frontend sends `credentials: "include"` and does not keep tokens in `localStorage`. Protected chat routes are enforced on the server; a user cannot read another account's chats.

A demo user is created on API startup if missing: `demo@clinic.local` / `demo123`.

---

## MongoDB schema overview

**users:** `_id`, `name`, `email`, `password_hash`, `created_at`, `updated_at`, `last_login`, `is_active`, `medical_disclaimer_accepted`

**chats:** `_id`, `user_id`, `title`, `created_at`, `updated_at`, `last_message_at`, `message_count`, `archived`, `metadata`

**messages:** `_id`, `chat_id`, `user_id`, `role`, `content`, timestamps, `model`, `citations`, `triage`, `possible_conditions`, `faithfulness`, `recommendations`, `refused`, `disclaimer`, `metadata`

Indexes exist on email (unique), `user_id`, `chat_id`, and recency fields.

---

## Chat architecture

Creating a chat stores an empty conversation. The first user message generates a short title (deterministic, not an extra model call). The sidebar groups chats by Today / Yesterday / Previous 7 days / Older. Rename and delete are per-owner. Deleting a chat also deletes its messages.

Historical messages are loaded from MongoDB. Previous answers are not regenerated.

---

## Streaming architecture

`POST /api/v1/chats/{chat_id}/messages/stream` returns `text/event-stream` events:

- `status` — retrieval / analysis progress
- `token` — answer chunk
- `citation` / `triage` / `metadata` — structured extras
- `done` — final payload plus the saved assistant message

Providers that cannot natively stream still emit reasonable chunks (the mock provider splits on words).

---

## Safety design

- Prescription and dosage requests are refused before generation.
- Emergency language forces an emergency triage banner even if retrieval continues for context.
- Answers must not claim certainty or replace a clinician.
- The UI labels the product as an information assistant, not a doctor.
- Chat content is not written to application logs by default.

---

## Installation

Requirements: **Python 3.11**, **Node.js 18+**, **MongoDB 6+** running locally.

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

cd frontend
npm install
```

Copy `.env.example` to `.env`. Keep `LLM_PROVIDER=mock` if you do not have an API key.

---

## Environment variables

See `.env.example`. Important groups:

- `MONGODB_URI`, `MONGODB_DB_NAME`
- `JWT_SECRET`, cookie lifetimes
- `CORS_ORIGINS` (include `http://localhost:5173`)
- `LLM_PROVIDER`, provider keys / Ollama URL
- `EMBEDDING_MODE`, `TOP_K`

Do not put real secrets in `.env.example`.

---

## Running the backend

MongoDB must be reachable first (`mongodb://127.0.0.1:27017` by default). For a disposable in-memory store while developing without a MongoDB install, set `MONGODB_URI=memory`.

```bash
set PYTHONPATH=backend
uvicorn app.main:app --reload --port 8000
```

Or double-click `run_api.bat`. Docs: http://localhost:8000/docs

---

## Running the frontend

```bash
cd frontend
npm run dev
```

Or `run_web.bat`. Website: http://localhost:5173  
`run_full.bat` starts API then Vite.

During development Vite proxies `/api` to port 8000.

---

## Building vector indexes

The live RAG path needs a Chroma index:

```bash
set PYTHONPATH=backend
python scripts/build_index.py
```

Use `general` or `medical` as an optional argument to build one store. The app reads `EMBEDDING_MODE`.

---

## Running tests

```bash
set PYTHONPATH=backend
python -m pytest tests/ -v
```

Auth/chat tests use an in-memory Mongo mock. Pipeline tests cover ingestion, guardrails, triage, and faithfulness without calling a paid LLM.

---

## Evaluation

```bash
python evaluation/evaluate_embeddings.py
python evaluation/evaluate_triage.py
python evaluation/evaluate_hallucination.py
python evaluation/evaluate_e2e.py
```

Datasets live in `evaluation/datasets/`. These scripts still import `src.*` and the original RAG pipeline.

---

## Configuration

| Setting | Role |
|---|---|
| `LLM_PROVIDER` | `mock`, `groq`, `openai`, or `ollama` |
| `EMBEDDING_MODE` | `general` (MiniLM) or `medical` (PubMedBERT) |
| `TOP_K` | Retrieved passage count |
| Missing cloud keys | Provider resolver falls back to `mock` |

Add a new model by implementing `generate` / `stream` in `backend/src/ai/providers/` and registering it in `backend/src/ai/registry.py`.

---

## Limitations

- Knowledge is limited to the bundled sample documents, not the whole medical literature.
- Retrieval and generation can miss or under-rank a condition.
- Mock mode answers from retrieved passages only; it is not a frontier clinical model.
- MongoDB and Chroma are local-process defaults, not a production clinical deployment.
- Cookie `Secure` is enabled only when `APP_ENV=production`.

---

## Medical disclaimer

This tool provides general information retrieved from reference medical documents. It cannot examine you, cannot order tests, and cannot provide emergency care. If you think you may be having a medical emergency, seek urgent in-person help.

---

## Future extension

- Additional providers in the existing registry
- Richer profile preferences
- Cursor-based chat pagination for very large histories
- Production reverse-proxy serving `frontend/dist` beside FastAPI

---

## Academic objectives (unchanged)

| # | Objective | Status |
|---|---|---|
| 1 | RAG over curated medical documents with citations | Implemented |
| 2 | Triage plus safety layer | Implemented |
| 3 | General vs medical embeddings (Recall@k, MRR) | Implemented |
| 4 | Hallucination comparison: RAG vs no retrieval | Implemented |
