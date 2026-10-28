# MediAssist Phase 4 — Targeted fixes after baseline

Date: 28 October 2026. Original baseline artifacts and Phase 3 files were not rewritten. This is not clinical validation.

Baseline (unchanged): `evaluation/results/conversation_phase4_baseline.json` — **47 / 59** (79.7%).
After: `evaluation/results/conversation_phase4_after.json` — **59 / 59** (100%).

The after-run used the same 59 pipeline scenarios in `evaluation/datasets/conversation_phase4.py`. Frontend ui01–ui08 are now covered by `frontend/tests/conversationPhase4Ui.test.ts` (pure session helpers + source contracts; ChatProvider is not mounted).

## Baseline reproducibility

Before edits, the runner was executed without writing over the baseline JSON:

```
47/59 passed, fail_ids: fu01 fu02 fu03 fu04 fu07 fu09 fu10 cr01 sf04 sf13 hy06 hy07
```

That matched the saved baseline exactly.

## File-level fixes mapped to failures

| Failure IDs | Change | Why |
| --- | --- | --- |
| fu01, fu02, fu03, fu04, fu07, fu09, hy06, hy07, sf04 | `query_normalize.py` follow-question / reuse rules; `guardrails.py` `classify_intent` inherits medical context for those questions | Everyday “What could cause this?”, “What should I do?”, warning-sign and seek-help turns were `ambiguous`/`non_medical` with no reuse |
| fu10 | Same-area continuation reuses history unless the turn is a full new “I have …” complaint | “No fever now, just the sore throat” stayed a new complaint |
| cr01 | Correction detection, rewrite of contradicted body terms in the search, skip synonym-expand on “not my knee”; ankle/knee as medical body language | “I meant my ankle, not my knee” was general chat |
| sf13 turn 1 | `painful`/`swollen`/`calf` medical terms; narrow `_NON_MEDICAL` so bare `flight` is not travel chat | Swollen painful calf after a long flight routed to the travel mock |
| sf13 turn 2 | `check_emergency(text, history)` for calf+travel then breathless; pipeline and evaluator pass history; independent of retrieval | Regex only saw “Now I feel breathless” |
| ui05 | `conversationChrome.ts` uses the latest user turn, not `messages.some(emergency)` | Header/112 stayed urgent after a later coding question |
| ui01, ui02, ui08 | `chatSession.ts` + `ChatContext.tsx` abort marks `streaming=false`, incomplete notice, `failedContentRef`, request-id ignores late `done` | Stop left a streaming cursor and retry did not work |
| ui03, ui04 | Reload replaces local messages; stream events are dropped when the request id or chat id no longer matches | Refresh/switch policy is now explicit |
| ui06, ui07 | Existing copy helper plus `publicError` stripping provider leaks; ChatInput still restores `draftRef` on error | Copy and composer-after-error needed tests, not new pipeline rules |

The evaluator now calls `check_emergency(user, history)` so `emergency_guard` matches the history-aware safety contract. Dataset expected fields were not changed.

## Pipeline before / after

| Category | Baseline | After |
| --- | --- | --- |
| followup | 3 / 12 (25%) | **12 / 12** |
| correction | 1 / 2 (50%) | **2 / 2** |
| isolation | 9 / 9 | 9 / 9 |
| routing | 10 / 10 | 10 / 10 |
| uncertainty | 7 / 7 | 7 / 7 |
| safety | 13 / 15 (87%) | **15 / 15** |
| reliability | 4 / 4 | 4 / 4 |
| **Total** | **47 / 59 (79.7%)** | **59 / 59 (100%)** |

Previously failed IDs that now pass: `fu01` `fu02` `fu03` `fu04` `fu07` `fu09` `fu10` `cr01` `sf04` `sf13` `hy06` `hy07`.

## Frontend ui01–ui08

| ID | Result | How it was tested |
| --- | --- | --- |
| ui01 abort | Pass | `abortStream` clears streaming, keeps the user row, marks incomplete, ignores late `done` |
| ui02 retry | Pass | `beginSend(..., reuseFailed)` does not add a second user bubble |
| ui03 refresh | Pass | `reloadMessages` drops temp ids and uses the server list |
| ui04 chat switch | Pass | `switchChat` then a stale token event does not append onto chat B |
| ui05 emergency chrome | Pass | Coding after chest pain is not “Emergency help”; “What should I do?” keeps it |
| ui06 copy | Pass | `formatAssistantCopy` includes answer/sources/evidence status, no provider names |
| ui07 composer after error | Pass | `publicError` is provider-neutral; ChatInput restores `draftRef` (source contract) |
| ui08 incomplete stream | Pass | Aborted row has no match cards and shows the incomplete notice |

**Limitation:** there is no React Testing Library / browser pass. ChatProvider is not mounted. ui03 refresh after a server-side `done` that raced the abort is documented in code (`item.streaming` must still be true before `done` is applied) but not exercised against a live SSE server.

## Phase 3 regression

`evaluation/evaluate_answer_quality.py` (no `--out`, so `answer_quality_after.json` was not rewritten): **72 / 72**.

## Persistence / retry policy

- Stopping a stream does **not** delete the user message (it may already be saved on the server).
- The temporary assistant row is marked incomplete and loses match/urgency cards.
- Retry resends the same user text and replaces the incomplete assistant row.
- Refresh loads the server list; a completed pair appears only if the server already persisted `done`.
- A late `done` for an aborted request id is ignored.

## Remaining ambiguities (unchanged dataset notes)

- **cr01:** Same-limb knee→ankle may still share the musculoskeletal topic group. Search now rewrites knee→ankle; leftover knee cards were never a required fail.
- **sf04:** Pipeline scores follow-up reuse of the chest complaint. The header may still show emergency chrome for “What should I do?” after chest pain (ui05 follow-up rule). That banner is **not** required by the pipeline case.
- **hy08:** Follow-up vs new complaint for delirium vs dementia remains unspecified; medical routing is required.

## Commands actually run

```powershell
$env:PYTHONPATH="backend"
$env:LLM_PROVIDER="mock"
$env:APP_ENV="development"

# Reproducibility (no --out)
.\venv\Scripts\python.exe evaluation\evaluate_conversation_phase4.py
# 47/59, same 12 fail_ids as the saved baseline

# After fixes
.\venv\Scripts\python.exe evaluation\evaluate_conversation_phase4.py --out evaluation\results\conversation_phase4_after.json
# 59/59, fail_ids []

.\venv\Scripts\python.exe evaluation\evaluate_answer_quality.py
# 72/72 (Phase 3 files not rewritten)

.\venv\Scripts\python.exe -m pytest tests\test_answer_quality_phase3.py tests\test_intent.py tests\test_emergency_context.py tests\test_general_chat.py tests\test_reliability_hardening.py tests\test_messages.py tests\test_chats.py -q --tb=short
# 72 passed, 1 warning (Starlette BlockingPortal) in 23.22s

cd frontend
npm test
# 56 passed, 0 failed
```

Warnings: Chroma telemetry `capture() takes 1 positional argument but 3 were given`; Starlette `BlockingPortal` deprecation. No skipped tests in these commands. No notes added, Chroma not rebuilt, embeddings and thresholds unchanged.
