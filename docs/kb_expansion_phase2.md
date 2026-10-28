# MediAssist knowledge-base expansion — Phase 2

Date: 27 October 2026. Existing notes were not deleted. Embedding model, `TOP_K`, `MIN_RELEVANCE_SCORE`, and `MIN_VECTOR_SCORE` were not changed. The medical Chroma collection was not rebuilt (`EMBEDDING_MODE` remains `general`).

This report covers both Phase 2 batches: the first seven notes, then the remaining sun-safety / Gaucher / safety-phrasing increment.

## Verified live state (after this work)

| Item | Value |
| --- | --- |
| Markdown notes | **1,017** unique IDs |
| General index | **1,035** chunks (`kb_general`, MiniLM) |
| Medical index | 403 chunks (stale; unused at runtime) |
| Default embedding | `sentence-transformers/all-MiniLM-L6-v2` |
| `EMBEDDING_MODE` | `general` |
| `TOP_K` | 4 |
| Front matter | `id`, `title`, `source`, `url`, `condition`, `triage_level` |

Starting counts in the original prompt (1,008 notes / 1,019 general chunks) were Phase 1’s end state, not the live corpus when this increment began. Live audit at the start of this increment: **1,015 notes / 1,031 general chunks / 403 medical chunks**.

## 1. Evaluation set

`evaluation/datasets/kb_phase2_queries.py` and `evaluation/datasets/kb_expansion_phase2.jsonl` contain **122** labeled queries. Retrieval scoring is separate from answer generation.

| Mode | Count | Role |
| --- | --- | --- |
| retrieval | 103 | Recall@k / MRR / citation URLs |
| emergency | 9 | Deterministic guardrail (independent of the LLM) |
| prescription | 3 | Deterministic prescription block |
| isolation | 3 | New complaint must not reuse unrelated history |
| out_of_scope | 4 | Weather, code, restaurants, car repair |
| gap | 0 | Former holes (sun protection, Gaucher) now have notes |

Categories: single symptoms, symptom combinations, digestive/respiratory/skin/neurological/urinary/musculoskeletal, chronic conditions, prevention/vaccination/screening, medication safety, children/pregnancy/older adults, rare disease (including Fabry and Gaucher), everyday language, misspellings, follow-ups, emergencies, and out-of-scope requests.

Run:

```powershell
$env:PYTHONPATH="backend"
.\venv\Scripts\python.exe evaluation\evaluate_kb_phase2.py --out evaluation\results\kb_phase2_after.json
```

## 2. Gap and failure classification

Already well covered before this increment: common symptoms and conditions, Phase 1 screening/vaccine/food-safety notes, ACE-inhibitor cough, antibiotic-associated diarrhoea, codeine constipation, paracetamol/ibuprofen/aspirin-in-children, pregnancy medicines, smoking cessation, delirium, and Fabry.

| Query / theme | Failure type | Action |
| --- | --- | --- |
| Sun protection to lower skin-cancer risk (`p12`) | Missing knowledge-base topic (sunburn *treatment* notes already existed) | Added `sun_safety_prevention` from CDC |
| Gaucher disease (`r06`) | Missing knowledge-base topic | Added `gaucher_disease` from MedlinePlus Genetics |
| `migrane`, `diarrea`, `ashtma`, `hypertention` | Missing synonym / terminology | Query-normalize expansions; no new notes |
| Ringworm, diabetic neuropathy, twisted ankle | Existing notes; labels only | No new notes |
| Stiff-neck + fever; glass-test rash (`e07`, `e09`) | Correct emergency response that the regex missed | Guardrail phrases; no new notes |
| “How many 500 mg paracetamol tablets…” (`m06`) | Correct prescription refusal that the regex missed | Guardrail phrases; no milligram dose added to notes |
| 17 retrieval queries with rank 2–4 | Poor ranking of sibling everyday notes | Left unchanged: Recall@4 is 1.000; embedding/thresholds not retuned |
| Crushing chest pain, stroke, breathing, allergy | Correct emergency response | Unchanged |
| Python / weather / pizza / tire | Correct out-of-scope refusal | Unchanged |
| Fabry after a knee-pain history | Conversation context isolation | Unchanged; still a new complaint |

No note was added where an existing note already covered the topic. Answer-generation quality was not scored here (kept separate from retrieval).

## 3. New verified notes

### First batch (7)

| ID | Source | URL |
| --- | --- | --- |
| `paracetamol_safety` | NHS - Paracetamol for adults | https://www.nhs.uk/medicines/paracetamol-for-adults/ |
| `ibuprofen_nsaid_safety` | NHS - Ibuprofen for adults | https://www.nhs.uk/medicines/ibuprofen-for-adults/ |
| `aspirin_and_children` | NHS - Aspirin | https://www.nhs.uk/medicines/aspirin-for-pain-relief/ |
| `medicines_in_pregnancy` | NHS - Medicines in pregnancy | https://www.nhs.uk/pregnancy/keeping-well/medicines/ |
| `smoking_cessation` | NHS - stop smoking services | https://www.nhs.uk/live-well/quit-smoking/nhs-stop-smoking-services-help-you-quit/ |
| `delirium` | MedlinePlus - Delirium | https://medlineplus.gov/ency/article/000740.htm |
| `fabry_disease` | MedlinePlus Genetics - Fabry disease | https://medlineplus.gov/genetics/condition/fabry-disease/ |

### This increment (2)

| ID | Source | URL |
| --- | --- | --- |
| `sun_safety_prevention` | CDC - Reducing Risk for Skin Cancer | https://www.cdc.gov/skin-cancer/prevention/index.html |
| `gaucher_disease` | MedlinePlus Genetics - Gaucher disease | https://medlineplus.gov/genetics/condition/gaucher-disease/ |

Each URL was fetched during this work. Notes follow the existing six-field schema. They do **not** include milligram doses. CDC sun-safety SPF 15 is a sunscreen rating, not a drug dose, and is United States guidance (peak hours 10 a.m.–4 p.m. DST). Screening, vaccination, and stop-smoking help differ by country.

Genuinely new topics across Phase 2: **9**. Corpus is now **1,017** notes / **1,035** general chunks.

## 4. Retrieval changes (only where evidence required them)

- Synonym expand: `tummy hurts?` → abdominal pain; `migrane` → migraine; `diarrea` → diarrhoea; `ashtma` → asthma; `hypertention` → hypertension.
- Embedding model, `TOP_K`, `MIN_RELEVANCE_SCORE`, and `MIN_VECTOR_SCORE` were not changed. Recall@4 was already 1.000 on the labeled set, so a model or threshold change had no measured need.

## 5. Before and after retrieval metrics

Measured with `evaluate_kb_phase2.py` using `build_conversation_state().search_query` against the live general index.

| | Phase 2 start (1,008 notes, 87 retrieval) | After first batch (1,015 notes, 94 retrieval) | After this increment (1,017 notes, 103 retrieval) |
| --- | --- | --- | --- |
| Recall@1 | 0.816 | 0.840 | **0.835** |
| Recall@4 | 0.989 | 1.000 | **1.000** |
| MRR | 0.894 | 0.912 | **0.910** |
| Citation rate (source + `https://` URL) | 1.000 | 1.000 | **1.000** |

Recall@1 / MRR dipped slightly because the labeled set grew (misspellings and extra body-system queries). Those extra queries still hit a labeled note in the top 4. Rank 1 is often a related sibling (`nausea_anxiety` before `nausea_without_vomiting`, `light_hurts_eyes` before `migraine`). That is ranking of overlapping everyday notes, not a missing topic.

Safety on the same 122-query run:

| Check | Result |
| --- | --- |
| Emergency | 9/9 |
| Prescription | 3/3 |
| Isolation | 3/3 |
| Out of scope | 4/4 |
| Missing labels | none |
| Retrieval misses @4 | none |

## 6. Citation and safety tests (actual runs)

```
pytest tests/test_kb_expansion_phase2.py tests/test_kb_expansion_phase1.py tests/test_everyday_retrieval.py tests/test_pipeline.py tests/test_intent.py tests/test_emergency_context.py
55 passed, 1 warning in 39.98s

frontend npm test
42 passed, 0 failed
```

New-topic retrieval tests hit `sun_safety_prevention` and `gaucher_disease` in the top 4, each with a source and `https://` URL. Meningitis-style fever + stiff neck and a non-blanching glass-test rash now trip emergency detection. “How many 500 mg paracetamol tablets should I take?” trips prescription safety. “What is paracetamol used for?” and “stiff neck after sleeping on a bad pillow” do not. A Gaucher or Fabry question after a knee-pain history is a new complaint and does not keep knee cards.

## 7. Commands

Rebuild **only** the general index after adding notes (`VectorStore.build` always resets that collection first, so this does not duplicate records):

```powershell
$env:PYTHONPATH="backend"
.\venv\Scripts\python.exe scripts\build_index.py general
```

Do **not** pass `medical` unless you intend to rebuild the unused PubMedBERT collection.

Evaluate:

```powershell
$env:PYTHONPATH="backend"
.\venv\Scripts\python.exe evaluation\evaluate_kb_phase2.py --out evaluation\results\kb_phase2_after.json
```

Tests:

```powershell
$env:APP_ENV="development"
$env:LLM_PROVIDER="mock"
$env:MONGODB_URI="memory"
$env:PYTHONPATH="backend"
.\venv\Scripts\python.exe -m pytest tests\test_kb_expansion_phase2.py tests\test_kb_expansion_phase1.py tests\test_everyday_retrieval.py tests\test_pipeline.py tests\test_intent.py tests\test_emergency_context.py -q --tb=short
```

Run MediAssist:

```powershell
$env:PYTHONPATH="backend"
$env:APP_ENV="development"
$env:LLM_PROVIDER="mock"
$env:MONGODB_URI="memory"
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --reload-dir backend --port 8000
```

In another terminal:

```powershell
cd frontend
npm run dev
```

Website: http://localhost:5173 — API docs: http://localhost:8000/docs. Demo login is development-only (`demo@clinic.local` / `demo123`).

Try: “How can I protect my skin from the sun to lower skin cancer risk?”, “What is Gaucher disease?”, “I get a migrane with light hurting my eyes”, then a new complaint after a previous knee-pain thread.

## 8. Remaining limitations

- The medical embedding index remains at **403 chunks** and was not rebuilt. Runtime still uses MiniLM / `general`.
- Recall@1 is not 1.0. Seventeen labeled queries retrieve a relevant sibling first. Changing the embedder or thresholds was not justified while Recall@4 is 1.000.
- The corpus is a curated sample, not a complete encyclopedia. Other rare conditions beyond the labeled set can still miss.
- Screening, vaccination, and sun-safety notes mix **NHS (UK)** and **CDC (US)** guidance. Country programmes are not interchangeable.
- Emergency detection is still regex-based. It is independent of the LLM and now covers the meningitis-style phrases in the eval set, but it is not exhaustive of every emergency phrasing.
- Notes still contain no milligram drug doses. Dosage questions are refused rather than answered from the corpus.
- This evaluation scores retrieval, citations, and safety. It does not score answer-generation quality, streaming, or live LLM providers.
