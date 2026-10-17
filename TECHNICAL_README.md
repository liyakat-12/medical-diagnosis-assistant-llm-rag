# MediAssist technical notes

MediAssist is a research and academic medical information assistant. A user describes symptoms in everyday language—by typing, or by tapping a body map and choosing symptom chips—and the system looks up matching notes from a curated knowledge base, then returns grounded information with citations, a triage label (self-care, consult a doctor, or emergency), possible condition matches, and nearby hospitals. It is not a medical device and does not replace a doctor: it does not give a confirmed diagnosis, prescribe medicines, or suggest doses. Emergency wording and prescription/dosage questions are checked with safety rules before the model answers.

The website is built with React 19, TypeScript, Vite, and Tailwind CSS. The chat UI streams answers as they are generated, stores conversations after login, and uses an interactive body map only to describe where the person feels discomfort. The backend is FastAPI. Login uses JWT cookies. MongoDB stores users, chats, and messages (or an in-memory stand-in for local demos). Medical notes stay as markdown files; search uses ChromaDB.

The core method is RAG. Symptom text is turned into vectors with sentence-transformers (`all-MiniLM-L6-v2`, with optional PubMedBERT). ChromaDB finds similar passages; a cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`) re-ranks them and keeps the best few. An LLM (mock, Groq, OpenAI, or Ollama) may write only from those retrieved notes. After that, the system adds citations, checks that claims match the sources, labels urgency, and can list nearby hospitals through OpenStreetMap. Quality is measured with project evaluation scripts—not with RAGAS.

This document describes the **implemented** architecture. RAG, safety, evaluation, and the knowledge base live in `backend/src` and remain the source of truth for medical behavior. The HTTP API, MongoDB, and auth live in `backend/app`.

---

## Runtime topology

- Frontend: Vite on `http://localhost:5173`
- Backend: FastAPI on `http://localhost:8000`
- Browser calls `/api/v1/...`; Vite proxies `/api` to the API
- Production: build `frontend/` to static files. FastAPI is the API only.

CORS allows credentialed requests from `CORS_ORIGINS`. Cookies are `HttpOnly`, `SameSite=Lax`, and `Secure` when `APP_ENV=production`.

---

## Folder structure

```
project-root/
├── backend/
│   ├── app/                         # HTTP API, auth, MongoDB persistence
│   │   ├── main.py                  # FastAPI app, CORS, lifespan
│   │   ├── api/                     # versioned routes under /api/v1
│   │   │   ├── router.py
│   │   │   └── routes/              # auth, users, chats, messages, diagnosis, health
│   │   ├── core/                    # config, JWT/bcrypt, dependencies, errors
│   │   ├── connection/              # MongoDB client, ping, indexes
│   │   │   ├── mongodb.py
│   │   │   └── indexes.py
│   │   ├── models/                  # MongoDB document shapes + serializers
│   │   │   ├── user.py
│   │   │   ├── chat.py
│   │   │   └── message.py
│   │   ├── repositories/            # database queries (always filter by owner)
│   │   ├── schemas/                 # Pydantic API request/response models
│   │   └── services/                # auth, chat titles, message + RAG orchestration
│   └── src/                         # RAG / AI (used by API and evaluation)
│       ├── config.py
│       ├── pipeline/rag_pipeline.py
│       ├── ingestion/
│       ├── embeddings/
│       ├── retrieval/
│       ├── safety/                  # guardrails, triage, citation faithfulness
│       ├── llm/generator.py
│       └── ai/providers/            # mock, openai, groq, ollama
├── frontend/src/
│   ├── pages/                       # one page per route (Home, Safety, Privacy, …)
│   ├── components/
│   ├── context/
│   ├── services/
│   ├── types/
│   └── utils/
├── knowledge_base/sample_documents/
├── data/                            # Chroma indexes (gitignored)
├── evaluation/
├── scripts/
└── tests/
```

`backend/src/api/main.py` re-exports `app.main:app` so `uvicorn src.api.main:app` still works with `PYTHONPATH=backend`.

Duplicate wrapper packages (`app/ai`, `app/rag`, `app/safety`, `app/ingestion`) were removed. Call `src.*` directly.

---

## Connection vs models vs repositories

| Layer | Folder | Responsibility |
|---|---|---|
| Connection | `app/connection/` | One Motor client, connect/disconnect, indexes |
| Models | `app/models/` | Collection names, document builders, serializers |
| Repositories | `app/repositories/` | Queries; every chat/message query includes `user_id` |
| Schemas | `app/schemas/` | API JSON contracts (Pydantic) |
| Services | `app/services/` | Auth cookies, titles, RAG orchestration |

Do not create a new Mongo client per request. Use `get_db()` from `app.connection.mongodb`.

---

## Request flow for a chat message

1. Cookie (or Bearer) JWT → `get_current_user`
2. Ownership check on the chat (`user_id` match or 404)
3. Persist the user message
4. If the chat is still titled "New chat", set a short deterministic title
5. Run `iter_pipeline_stream` (SSE) or `run_pipeline` (JSON)
6. Persist the assistant message with answer, model/provider, citations, triage, possible conditions, faithfulness, recommendations, disclaimer

SSE event types: `status`, `token`, `citation`, `triage`, `metadata`, `done`.

---

## RAG pipeline (unchanged behavior)

`run_pipeline` / `iter_pipeline_stream` in `backend/src/pipeline/rag_pipeline.py`:

1. `check_prescription_request` — refuse and skip retrieval when triggered
2. `retrieve` from Chroma (`general` or `medical` collection), then optional cross-encoder re-rank (`src/retrieval/reranker.py`; default on)
3. `classify_triage` with emergency override from `check_emergency`
4. `stream_grounded_answer` / `generate_grounded_answer` via the provider registry
5. `audit_citation_faithfulness`
6. Package `DiagnosisResponse` (`result_to_dict` for APIs)

Evaluation scripts import `src.*` and must keep working.

---

## AI providers

`src.ai.registry.get_provider()` returns:

| Name | Module | Notes |
|---|---|---|
| mock | `providers/mock.py` | Offline; answers from retrieved titles/passages |
| openai | `providers/openai.py` | Uses `OPENAI_API_KEY` |
| groq | `providers/groq.py` | OpenAI-compatible Groq API |
| ollama | `providers/ollama.py` | Local HTTP at `OLLAMA_BASE_URL` |

`config.resolve_llm_provider()` falls back to `mock` when a required cloud key is missing.

To add a provider: implement `generate` and `stream`, then register the class in `_PROVIDERS`.

---

## Authentication and authorization

- Register/login set access + refresh cookies
- `GET /auth/me` restores the session on frontend boot
- Refresh rotates cookies from the refresh cookie
- Chat and message queries always filter by `user_id`
- Missing or foreign chat ids return 404 (not 403) to avoid leaking existence

---

## Frontend layout

```
frontend/src/
  pages/       Home, Login, Register, Chat, ChatHistory, Profile, Privacy, Safety, NotFound
  components/  navbar, footer, chat, medical, auth, common
  context/     AuthContext, ChatContext, AppContext
  services/    api.ts, auth.ts, chat.ts, diagnosis.ts
```

Auth bootstrap: full-page spinner until `/auth/me` finishes. Guest routes redirect to `/chat` when signed in. Protected routes redirect to `/login`.

Chat shell (`pages/Chat.tsx`): viewport height; sidebar + message scroller + composer. Sidebar collapse/width persist in `localStorage` (`AppContext`). Desktop drag-resize is pointer-only (not on touch). Mobile uses an overlay drawer (close control, overlay click, Escape).

Body map: `frontend/src/components/chat/BodyMap.tsx` is presentational (`BodyFigure` is the SVG). Selection state lives in `ChatInput.tsx`. A new empty chat shows the figure in the message column; the composer **Body** button opens the same front/back panel. Query construction is in `frontend/src/utils/bodyMap.ts` (`buildBodyMapQuery`, `formatReviewLine`). The composer **Will send** line previews typed text plus selected regions/symptoms. Selected regions and symptoms are extra query text; they do not rebuild the Chroma index or override triage on their own.

Assistant message layout (`MessageBubble.tsx`): urgency, then recommendations, then explanation, then possible matches, then sources. Match percentages are normalized retrieval scores summing to 100.

Nearby hospitals: `backend/app/services/hospital_service.py` queries Overpass mirrors, falls back to Nominatim, and returns a short list plus an embeddable map.

---

## Tests

| File | Coverage |
|---|---|
| `tests/test_pipeline.py` | ingestion, chunking, emergency, dosage refusal, faithfulness |
| `tests/test_body_map_context.py` | body-map query text does not bypass emergency or prescription rules |
| `tests/test_hospitals.py` | Overpass/Nominatim parsing and friendly errors |
| `tests/test_auth.py` | password hashing, title generation |
| `tests/test_chats.py` | register/login/logout, demo user, ownership, rename, delete |
| `tests/test_messages.py` | persist messages, stream save, cross-user 404 |
| `tests/test_ai.py` | provider registry + mock grounded answer |
| `frontend/tests/bodyMap.test.ts` | selection, duplicate prevention, review line, keyboard/collapse markup |

There are **32** pytest functions under `tests/` and **16** cases in `frontend/tests/bodyMap.test.ts`. `tests/conftest.py` swaps Motor for `mongomock-motor` and skips a live Mongo ping. Do not claim the full suite passed unless it was re-run in this venv.

---

## Documented evaluation figures

Sets: `symptom_condition_testset.csv` (112), `emergency_test_set.csv` (100: 53 / 47), `hallucination_test_questions.csv` (112).

| Metric | Value |
|---|---|
| Emergency recall / precision / F1 | 100% / 100% / 1.000 (0 missed, 0 false alarms) |
| MiniLM only Recall@1 / @3 / @5 / MRR | 62.50% / 90.18% / 92.86% / 0.758 |
| PubMedBERT only Recall@1 / @3 / @5 / MRR | 65.18% / 84.82% / 86.61% / 0.742 |
| MiniLM + re-ranker Recall@1 / @3 / @5 / MRR | **85.71%** / 94.64% / 96.43% / 0.903 |
| E2E condition surfaced / exact triage | 110/112 (98.21%) / 105/112 (93.75%) |

`98.21%` (e2e: expected condition in the answer or citations) is not the same test as Recall@5 `96.43%` (expected document in the top 5 chunks). PubMedBERT was compared **without** the re-ranker. The live app uses MiniLM **with** re-ranking (`RERANK_ENABLED` default true, `RERANK_CANDIDATES` default 12). Chunking: 120-word windows, 30-word overlap. Timings (warm CPU cache): ~24 ms retrieval, ~28 ms mock pipeline, 82.1 s / 114.4 s index builds.

---

## Local data

- Chroma: `data/vector_store_general`, `data/vector_store_medical` (gitignored)
- MongoDB: database `mediassist` by default. Set `MONGODB_URI=memory` only when a MongoDB daemon is unavailable; that store is discarded on shutdown.
- Knowledge base markdown **is** part of the repository

Rebuild vectors with `python scripts/build_index.py`.
