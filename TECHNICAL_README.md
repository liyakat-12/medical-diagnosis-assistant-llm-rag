# MediAssist technical notes

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
2. `retrieve` from Chroma (`general` or `medical` collection)
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

---

## Tests

| File | Coverage |
|---|---|
| `tests/test_pipeline.py` | ingestion, chunking, emergency, dosage refusal, faithfulness |
| `tests/test_auth.py` | password hashing, title generation |
| `tests/test_chats.py` | register/login/logout, demo user, ownership, rename, delete |
| `tests/test_messages.py` | persist messages, stream save, cross-user 404 |
| `tests/test_ai.py` | provider registry + mock grounded answer |

`tests/conftest.py` swaps Motor for `mongomock-motor` and skips a live Mongo ping.

---

## Local data

- Chroma: `data/vector_store_general`, `data/vector_store_medical` (gitignored)
- MongoDB: database `mediassist` by default. Set `MONGODB_URI=memory` only when a MongoDB daemon is unavailable; that store is discarded on shutdown.
- Knowledge base markdown **is** part of the repository

Rebuild vectors with `python scripts/build_index.py`.
