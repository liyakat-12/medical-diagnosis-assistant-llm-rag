# MediAssist Phase 6 — Semantic consistency

Date: 28 October 2026. Small, reversible pipeline and UI changes. Embeddings, the 12-candidate rerank pool, `batch_size=4`, retrieval thresholds, and the Chroma index were not changed. Phase 2–5 result files were not overwritten.

This is not clinical validation and does not prove diagnostic accuracy.

## Root causes

1. Coarse intent was only `medical | greeting | non_medical | ambiguous`. Definition questions such as “What is asthma?” used the same symptom-workup prompt, condition cards, and note-metadata triage as “I have a cough.”
2. Search text did not canonicalize educational paraphrases (“what asthma is”, “tell me about asthma”), so retrieval could diverge.
3. The generator always framed the user line as a “symptom description” and asked for a short list of possible conditions plus “see a clinician.”
4. Frontend educational detection missed “tell me about”, inverted copulas, and “I want to understand,” and treated bare words such as `cough` as personal symptoms.

## What changed

Deterministic `question_type` classification (no extra model) plus educational search rewrite. Emergency and prescription regex still run on the raw message before retrieval and the LLM.

Reference questions (`MEDICAL_EDUCATION`, educational `SYMPTOM_INFORMATION` / `TREATMENT_INFORMATION` / `POSSIBLE_CAUSES`, non-personal `FOLLOW_UP`) skip personalized urgency and match cards. Citations remain. Symptom reports still get cards and triage.

## How classification and normalization work

`build_conversation_state` still owns routing. After status is set, `classify_question_type` reads the current message plus conversation status/history with regexes and existing follow-up/correction helpers.

Search rewrite examples (original message is unchanged for display and safety):

- “what asthma is” → “What is asthma?”
- “explain asthma simply” → “What is asthma? Explain in simple language.”
- “asthma symptoms?” → “What are the symptoms of asthma?”
- “how can asthma be treated?” → “What are the general treatment and management options for asthma?”

Negation, location corrections, medication names, and emergency wording are not rewritten into general education. A cache of answers was not added.

## Equivalent-query retrieval

Phase 6 scores Jaccard overlap of live top-4 `doc_id`s inside each family, plus Recall@1 / Recall@4 / MRR against labeled notes. Overlap is reported, not assumed identical.

Asthma education family: pairwise Jaccard **0.787**, vs canonical **0.84**. Shared core notes: `what_is_asthma_simple`, `asthma_mild`. COPD / smoky-cough neighbors still enter the top four for some paraphrases.

## Results (mock LLM)

| Suite | Result |
| --- | --- |
| Phase 6 semantic consistency | **36/37** (intent 1.000, emergency 1.000, prescription 1.000) |
| Phase 3 answer quality | **72/72** (no regression vs batch4) |
| Phase 4 conversation pipeline | **59/59** (no regression vs batch4) |
| Backend pytest | **198 passed** before the final mock-answer trim; Phase 6 unit tests green after |
| Frontend tests | **57 passed** |

Known Phase 6 failure, left in the suite:

- `oe09` “What is costochondritis?” retrieves joint-wear / RA / bursitis, not `costochondritis_tender_chest`. Classification and no-personal-triage still pass. This is a retrieval/candidate-pool miss, not a cross-encoder batch-size issue.

## Safety

- Emergency paraphrases including “cannot breathe”, “cannot speak normally”, and “breathing is severely difficult” pass independent regex + pipeline triage (`112`).
- Dosage / prescription requests still refuse before RAG.

## Latency

No stored before-timing exists for “What is asthma?” specifically.

| Measurement | Value |
| --- | --- |
| Warm probe, n=5, “What is asthma?” | median **448 ms**, mean 446 ms |
| Phase 6 37-case mean (includes one cold load) | 907 ms, max 14.6 s |
| Phase 5 batch4 pf01 cough warm median (different query) | 421 ms |

The first pipeline call in a process still pays embedding/rerank load. Warm educational latency is in the same band as Phase 5 retrieving scenarios.

## Files

- `backend/src/pipeline/question_type.py` — types, rewrite, personal vs reference
- `backend/src/pipeline/conversation_state.py`, `rag_pipeline.py`, `query_normalize.py`
- `backend/src/llm/generator.py`, `backend/src/ai/providers/mock.py`
- `backend/src/safety/guardrails.py` — extra respiratory emergency paraphrases
- `backend/app/services/message_service.py`, frontend intent / chrome / bubble / chatSession
- `evaluation/datasets/semantic_consistency_phase6.py`, `evaluation/evaluate_semantic_consistency.py`
- Results: `evaluation/results/semantic_consistency_phase6.json`, `answer_quality_phase6_regression.json`, `conversation_phase4_phase6_regression.json`

## Next recommended task

Investigate why `costochondritis` loses to generic joint notes in the 12-candidate pool (query expansion / metadata, not a rerank-batch experiment). Optionally add a query-side condition-name boost for educational `What is X?` without rebuilding the index.
