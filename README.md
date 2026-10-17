# MediAssist — Medical Diagnosis Assistant using LLM + RAG

MediAssist is a research and academic medical information assistant. A user describes symptoms in everyday language—by typing, or by tapping a body map and choosing symptom chips—and the system looks up matching notes from a curated knowledge base, then returns grounded information with citations, a triage label (self-care, consult a doctor, or emergency), possible condition matches, and nearby hospitals. It is **not** a medical device and does **not** replace a doctor: it does not give a confirmed diagnosis, prescribe medicines, or suggest doses. Emergency wording and prescription/dosage questions are checked with safety rules before the model answers.

The website is built with **React 19**, **TypeScript**, **Vite**, and **Tailwind CSS**. The chat UI streams answers as they are generated, stores conversations after login, and uses an interactive body map only to describe where the person feels discomfort. The backend is **FastAPI**. Login uses **JWT cookies**. **MongoDB** stores users, chats, and messages (or an in-memory stand-in for local demos). Medical notes stay as markdown files; search uses **ChromaDB**.

The core method is **RAG (Retrieval-Augmented Generation)**. Symptom text is turned into vectors with **sentence-transformers** (`all-MiniLM-L6-v2`, with optional PubMedBERT). ChromaDB finds similar passages; a **cross-encoder** re-ranks them and keeps the best few. An LLM (mock, Groq, OpenAI, or Ollama) may write only from those retrieved notes. After that, the system adds citations, checks that claims match the sources, labels urgency, and can list nearby hospitals through OpenStreetMap. Quality is measured with project evaluation scripts for retrieval, triage, hallucination, and end-to-end answers—not with RAGAS.

---

## Features

- React + TypeScript chat UI: sidebar, scrolling conversation, pinned composer
- Collapsible / resizable chat sidebar; overlay drawer on small screens
- Interactive body map on a new chat and from the **Body** button (not a diagnosis)
- Demo login on the sign-in page (`demo@clinic.local` / `demo123`)
- FastAPI backend with JWT authentication in HTTP-only cookies
- MongoDB storage for users, chats, and messages
- Retrieval-Augmented Generation over 400 curated medical notes
- Sentence-transformer embeddings, ChromaDB vector search, and cross-encoder re-ranking
- Nearby hospitals via OpenStreetMap (Overpass) with a Nominatim fallback
- General and medical embedding modes
- Safety guardrails, emergency detection, and prescription/dosage refusal
- Triage labels: self-care, consult a doctor, emergency
- Answers shown as urgency, recommendations, explanation, possible matches, then sources
- Citation generation and citation-faithfulness auditing
- Pluggable LLM providers: mock, Groq, OpenAI, Ollama
- Token/chunk streaming over Server-Sent Events
- Evaluation scripts for embeddings, triage, hallucination, and end-to-end quality

---

## Screenshots

Add product screenshots here after a local run:

- Landing page
- Login / register
- Chat with body map, urgency banner, recommendations, and citations
- Nearby hospitals and conversation sidebar on desktop and mobile

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
            user query (typed text + optional body-map context)
            → safety checks
            → ChromaDB retrieval + cross-encoder re-rank
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

**AI / RAG:** ChromaDB, sentence-transformers (MiniLM / optional PubMedBERT), cross-encoder re-ranker (`ms-marco-MiniLM-L-6-v2`), safety modules, provider registry

**Maps:** OpenStreetMap Overpass API, Nominatim fallback, embedded map for nearby hospitals

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
2. Retrieve 12 candidate passages from ChromaDB, then re-rank them with a cross-encoder and keep the top 4.
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

Creating a chat stores an empty conversation. The first user message generates a short title (deterministic, not an extra model call). The layout is a full-height chat shell: history sidebar, independently scrolling messages, and a composer that stays at the bottom. The sidebar can collapse to a narrow rail, be drag-resized on desktop (about 240–380 px), and becomes an overlay drawer on phones. Chats are grouped by Today / Yesterday / Previous 7 days / Older. Rename and delete are per-owner. Deleting a chat also deletes its messages.

A new conversation shows a clickable body figure (“Tap where it hurts”) plus region buttons. The composer also has a **Body** control. The user can switch Front / Back, tap a region, and see only that region’s symptom chips. A **Will send** review line shows the typed text plus selected locations and symptoms before submit. Helpers live in `frontend/src/utils/bodyMap.ts` (`buildBodyMapQuery`, `formatReviewLine`). Changing a selection replaces that context instead of appending duplicates. The map only records discomfort; it does not name a disease, improve retrieval by itself, or change triage on its own.

Assistant replies are arranged as: **urgency → recommendations → explanation → possible matches → sources**. Match percentages are normalized retrieval scores that sum to 100, not the chance of a diagnosis.

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
- The body map never suppresses emergency checks; red-flag text in the sent message still forces emergency guidance.
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
- `EMBEDDING_MODE`, `TOP_K`, `RERANK_ENABLED`, `RERANK_CANDIDATES`

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

The repository has **32** pytest tests under `tests/` and **16** frontend body-map tests (`npm test`). Auth/chat tests use an in-memory Mongo mock. Pipeline tests cover ingestion, guardrails, triage, and faithfulness without calling a paid LLM. Do not claim the full suite passed unless you re-run it in this project’s venv.

Body-map query helpers (frontend):

```bash
cd frontend
npm test
```

---

## Evaluation

```bash
python evaluation/evaluate_embeddings.py
python evaluation/evaluate_triage.py
python evaluation/evaluate_hallucination.py
python evaluation/evaluate_e2e.py
```

Datasets live in `evaluation/datasets/`: **112** symptom–condition queries, **100** emergency cases (53 emergency / 47 non-emergency), and **112** hallucination questions. Scripts import `src.*` and the live RAG path.

Documented results (expanded sets, MiniLM live path with re-ranking unless noted):

| Test | Result |
|---|---|
| Emergency safety layer | 53/53 detected; 0 missed; 0 false alarms (100 cases) |
| MiniLM only, 112 queries | Recall@1 62.50%; Recall@3 90.18%; Recall@5 92.86%; MRR 0.758 |
| PubMedBERT only, 112 queries | Recall@1 65.18%; Recall@3 84.82%; Recall@5 86.61%; MRR 0.742 |
| **Live MiniLM + re-ranker** | Recall@1 **85.71%**; Recall@3 94.64%; Recall@5 96.43%; MRR 0.903 |
| End-to-end (same 112 queries) | Condition surfaced 110/112 (**98.21%**); exact triage 105/112 (93.75%) |

PubMedBERT is slightly better at Recall@1 **without** the re-ranker; MiniLM is better at Recall@3, Recall@5, and MRR in that fair compare. The running app uses MiniLM **with** re-ranking.

**98.21%** and **Recall@5 (96.43%)** are different tests: the first is end-to-end condition surfacing in the answer or citations (`evaluate_e2e.py`); the second is whether the expected document is in the top 5 retrieved chunks (`evaluate_embeddings.py`). Warm-cache timings still documented: about **24 ms** retrieval, **28 ms** mock pipeline, **82.1 s** / **114.4 s** to build the general / medical indexes.

---

## Configuration

| Setting | Role |
|---|---|
| `LLM_PROVIDER` | `mock`, `groq`, `openai`, or `ollama` |
| `EMBEDDING_MODE` | `general` (MiniLM) or `medical` (PubMedBERT) |
| `TOP_K` | Passages kept after re-ranking (default 4) |
| `RERANK_ENABLED` | Cross-encoder second stage (default `true`) |
| `RERANK_CANDIDATES` | Chroma hits scored before keeping `TOP_K` (default 12) |
| Missing cloud keys | Provider resolver falls back to `mock` |

Add a new model by implementing `generate` / `stream` in `backend/src/ai/providers/` and registering it in `backend/src/ai/registry.py`.

---

## Limitations

- Knowledge is limited to the bundled sample documents, not the whole medical literature.
- Without re-ranking, first-place retrieval was 62.50% on 112 queries; with the cross-encoder it was 85.71%. A condition that is not in the 400-note set cannot be suggested.
- The body map only adds location and symptom words to the query. It does not diagnose and is not claimed to raise Recall@1.
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
