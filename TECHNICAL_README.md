# MediAssist technical notes

This document describes the **implemented** architecture after the full-stack refactor. The live RAG, safety, evaluation, and knowledge-base code in `backend/src` remains the source of truth for medical behavior.

---

## Runtime topology

- Frontend: Vite dev server on `http://localhost:5173`
- Backend: FastAPI on `http://localhost:8000`
- Browser calls `/api/v1/...`; Vite proxies `/api` to the API
- Production: build `frontend/` to static files and serve them independently or behind a reverse proxy. FastAPI is the API only; there is no Express static server.

CORS allows credentialed requests from `CORS_ORIGINS`. Cookies are `HttpOnly`, `SameSite=Lax`, and `Secure` when `APP_ENV=production`.

---

## Backend layout

```
backend/app/
  main.py                 FastAPI app, CORS, startup/shutdown
  api/router.py           mounts /api/v1 routes
  api/routes/             auth, users, chats, messages, diagnosis, health
  core/                   config re-export, JWT/bcrypt, dependencies, errors
  db/mongodb.py           shared Motor client
  db/indexes.py           startup indexes
  db/repositories/        users, chats, messages
  schemas/                Pydantic request/response models
  services/               auth, chat titles, message + RAG orchestration
  ai/, rag/, safety/      thin re-exports of backend/src modules

backend/src/
  pipeline/rag_pipeline.py
  ingestion/
  embeddings/
  retrieval/
  safety/
  llm/generator.py        talks only to src.ai.registry
  ai/providers/           mock, openai, groq, ollama
  config.py
```

`backend/src/api/main.py` re-exports `app.main:app` so older `uvicorn src.api.main:app` commands still work if `PYTHONPATH=backend`.

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

Evaluation scripts import this module directly and must keep working.

---

## AI providers

`src.ai.registry.get_provider()` returns:

| Name | Module | Notes |
|---|---|---|
| mock | `providers/mock.py` | Offline; answers from retrieved titles/passages |
| openai | `providers/openai.py` | Uses `OPENAI_API_KEY` |
| groq | `providers/groq.py` | OpenAI-compatible Groq API |
| ollama | `providers/ollama.py` | Local HTTP at `OLLAMA_BASE_URL` |

`config.resolve_llm_provider()` falls back to `mock` when a required cloud key is missing. Application code should keep using the registry rather than SDKs.

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
  main.tsx, App.tsx
  context/     AuthContext, ChatContext, AppContext
  services/    api.ts (credentials + SSE), auth.ts, chat.ts, diagnosis.ts
  pages/       Home, Login, Register, Chat, ChatHistory, Profile, Privacy/Safety, 404
  components/  navbar, footer, chat sidebar, medical triage, common controls
```

Auth bootstrap: show a full-page spinner until `/auth/me` (and optional refresh) finishes. Guest routes `/login` and `/register` redirect to `/chat` when a session exists. Protected routes redirect to `/login`.

ChatContext owns chat list, active messages, streaming, rename, and delete. Components do not call `fetch` directly.

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
