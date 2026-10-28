# MediAssist Phase 4 — Conversation baseline (no fixes)

Date: 28 October 2026. Application code, prompts, routing, safety rules, indexes, and Phase 3 evaluation files were not modified. This report records the current system only.

This is not clinical validation. Frontend/streaming UI scenarios were listed, not scored.

## Dataset

- `evaluation/datasets/conversation_phase4.py`
- `evaluation/datasets/conversation_phase4.jsonl` (67 records)
- Runner: `evaluation/evaluate_conversation_phase4.py`
- Results: `evaluation/results/conversation_phase4_baseline.json`

| Layer | Count | Scored? |
| --- | --- | --- |
| pipeline (`run_pipeline` + `build_conversation_state`) | 59 | Yes |
| frontend (abort, retry, refresh, chat switch, chrome, copy) | 8 | **No** |

Phase 3 remains 72 single-question cases in its original files.

## Method

Each pipeline scenario is a message sequence. After every user turn the runner:

1. Builds `ConversationState` on the prior turns of **that scenario only**.
2. Calls `run_pipeline` with `LLM_PROVIDER=mock`.
3. Asserts routing, reuse, search text, origin, triage, refusals, mentions, and leftover cards.

Frontend rows describe expected UI behavior from the prior audit. They do **not** contribute to the pass rate.

## Pipeline baseline

| | Count |
| --- | --- |
| Scored | 59 |
| Passed | **47** |
| Failed | **12** |
| Pass rate | **79.7%** |

### By category

| Category | Passed | Failed | Rate |
| --- | --- | --- | --- |
| followup | 3 / 12 | 9 | 25% |
| correction | 1 / 2 | 1 | 50% |
| isolation | 9 / 9 | 0 | 100% |
| routing | 10 / 10 | 0 | 100% |
| uncertainty | 7 / 7 | 0 | 100% |
| safety | 13 / 15 | 2 | 87% |
| reliability (empty/malformed/new-chat history) | 4 / 4 | 0 | 100% |

Isolation, educational-vs-general routing, vague/uncovered-disease uncertainty, and empty/malformed history all passed on this runner.

### Failed scenarios

| ID | Last failing user turn | Actual | Failed checks |
| --- | --- | --- | --- |
| fu01 | What could cause this? | `ambiguous`, no reuse | intent, status, reuse, search_contains |
| fu02 | What should I do? | `ambiguous`, no reuse | intent, status, reuse, search_contains |
| fu07 | What should I do? (after UTI) | same | same |
| fu09 | What should I do? (after morning sickness) | same | same |
| hy06 | What could cause this? (after rash) | same | same |
| hy07 | What should I do? (after post-meal chest burn) | same | same |
| sf04 | What should I do? (after crushing chest pain) | `ambiguous`, no reuse | reuse, search_contains |
| fu03 | What warning signs should I watch for? | `non_medical` / `general` | intent, status, reuse, search_contains |
| fu04 | When should I seek help? | `non_medical` / `general` | intent, status, reuse, search_contains |
| fu10 | No fever now, just the sore throat | `new_complaint`, no reuse | status, reuse |
| cr01 | I meant my ankle, not my knee | `non_medical` / `general` | intent, status |
| sf13 | (1) swollen painful calf after a long flight | `non_medical` (`flight` is a general-chat keyword; `painful`/`calf` are not enough) | intent |
| sf13 | (2) Now I feel breathless | triage emergency from notes; **regex false** because calf/flight are not in this turn | emergency_guard, emergency_independent |

Follow-ups that already contain `worse` / `left` / `tell me more` / `getting better` passed (fu05, fu06, fu08).

## Ambiguities (not forced to a single clinical rule)

- **cr01:** Knee→ankle is the same limb topic group. The fail is routing (`non_medical`), not leftover knee cards.
- **sf04:** A bare “What should I do?” after chest pain has no red-flag words. Emergency regex on the latest text does not fire. The scenario only required follow-up reuse of the chest complaint; it did not require an emergency banner.
- **hy08:** Delirium vs dementia as follow-up vs new complaint is left open. That scenario passed on medical routing and mention checks.

## Frontend scenarios (not scored)

ui01 abort, ui02 retry, ui03 refresh, ui04 chat switch, ui05 sticky emergency chrome, ui06 copy, ui07 composer after error, ui08 incomplete stream. The Python runner cannot click Stop, reload, or switch routes. Do not treat these as passes.

## Phase 3 (unchanged)

`evaluation/results/answer_quality_after.json` is still **72 / 72**. Those files were not rewritten.

## Existing tests actually run

```
pytest tests/test_answer_quality_phase3.py tests/test_intent.py tests/test_emergency_context.py
        tests/test_general_chat.py tests/test_reliability_hardening.py tests/test_messages.py
        tests/test_chats.py
63 passed, 1 warning in 22.35s

frontend npm test
42 passed, 0 failed
```

Warning: Starlette `BlockingPortal` deprecation. No failures. No skipped tests in these commands.

## Commands

```powershell
$env:PYTHONPATH="backend"
$env:LLM_PROVIDER="mock"
$env:APP_ENV="development"
.\venv\Scripts\python.exe evaluation\evaluate_conversation_phase4.py --out evaluation\results\conversation_phase4_baseline.json
```

Phase 3 (unchanged files):

```powershell
.\venv\Scripts\python.exe evaluation\evaluate_answer_quality.py --out evaluation\results\answer_quality_after.json
```

App (not started for this baseline):

```powershell
$env:PYTHONPATH="backend"
$env:APP_ENV="development"
$env:LLM_PROVIDER="mock"
$env:MONGODB_URI="memory"
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --reload-dir backend --port 8000
```

```powershell
cd frontend
npm run dev
```

## Limitations

- Mock LLM only. Live providers were not scored.
- No browser, SSE abort, or chat-switch execution.
- History is the in-memory turn list for one scenario, not Mongo chat ids. Cross-chat isolation is simulated with empty `seed_history`.
- Emergency de-escalation after a resolved red flag is only partly specified (see sf04).
- No notes were added and Chroma was not rebuilt.

No application fixes were made.
