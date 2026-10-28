# MediAssist knowledge-base expansion — Phase 1

Audit date: 27 October 2026. Existing notes were not deleted or overwritten.

## 1. Audit of the current corpus

| Item | Finding |
| --- | --- |
| Location | `knowledge_base/sample_documents/` |
| Markdown files | 1,000 before this batch; 1,008 after |
| Loader | `backend/src/ingestion/loader.py` |
| Indexer | `scripts/build_index.py` → `VectorStore.build()` |
| Embeddings | Default `general`: `all-MiniLM-L6-v2`. Optional `medical`: PubMedBERT. Not changed. |
| Chunking | 120-word windows, 30-word overlap |

### Note format

Every note uses the same YAML-like front matter. No extra keys are present, and the loader only stores these six fields on each chunk:

```
id, title, source, url, condition, triage_level
```

Bodies are short plain-language teaching notes (median 75 words). There are no `##` section headings. Synonyms, warning signs, self-care, and “when to seek care” are written into the paragraphs rather than as a separate schema.

### Quality of the 1,000 existing notes

- Unique document IDs: 1,000. ID always matches the filename stem.
- Malformed front matter: 0
- Empty bodies: 0
- Missing `id` / `title` / `source` / `url` / `condition` / `triage_level`: 0
- Duplicate document IDs: 0
- Exact or whitespace-normalized duplicate bodies: 0
- All 1,000 URLs use `https://`
- Two shared titles with different IDs (not duplicate files): `Heat Rash`, `When a Fever Needs a Doctor`
- 22 shared `condition` labels across related notes (for example several knee-pain or constipation situational notes). These are overlapping everyday variants, not alias files.

Triage mix before this batch: `self_care` 511, `consult_doctor` 415, `emergency` 74.

Source domains (top): NHS 533, CDC 174, MedlinePlus 60, NIDDK 50, NIAMS 37, NINDS 20, Mayo Clinic 17, AHA 12, NIMH 11, WHO 9.

### ChromaDB before this batch

| Collection | Chunks | Unique `doc_id` | Notes vs files |
| --- | --- | --- | --- |
| `kb_general` | 1,005 | 1,000 | Every file was indexed. Every chunk had `source` and `url`. |
| `kb_medical` | 403 | stale vs current files | Not the runtime default (`EMBEDDING_MODE=general`). |

`VectorStore.build()` always deletes and rebuilds the collection. There is no incremental indexer, so unchanged notes are re-embedded on a full rebuild. Indexer code was left unchanged.

## 2. Coverage versus the Phase 1 topic list

The requested symptom, respiratory, digestive, cardiometabolic, musculoskeletal, neurological, skin, urinary/reproductive, mental health, and emergency topics already have dedicated or close everyday notes. Examples: `common_cold`, `influenza`, `asthma_mild`, `seasonal_allergies`, `pneumonia`, `gerd`, `gastritis`, `ibs`, `hypertension`, `type1_diabetes`, `type2_diabetes`, `hyperlipidemia`, `anemia`, `hypothyroidism`, `muscle_strain`, `sprained_ankle`, `sciatica`, `osteoarthritis`, `migraine`, `tension_headache`, `peripheral_neuropathy`, `epilepsy`, `acne`, `eczema`, `contact_dermatitis`, `hives`, `urinary_tract_infection`, `kidney_stones`, `menstrual_cramps`, `anxiety_disorder`, `depression`, `insomnia`, `dehydration`, `iron_deficiency_symptoms`, `vitamin_b12_deficiency`, `stroke`, `heart_attack`, `anaphylaxis`, `sepsis`, `red_flag_breathing`.

True gaps selected for this batch (missing dedicated notes, not aliases):

1. Home food-safety prevention (food poisoning notes existed; prevention did not)
2. Norovirus / winter vomiting bug by name
3. Adult vaccination overview (only a sore-arm after-jab note existed)
4. Cervical screening / smear test
5. Breast screening / mammogram (warning-sign notes existed; screening did not)
6. Bowel cancer screening / FIT kit (warning-sign notes existed; screening did not)
7. Dementia as an umbrella topic (Alzheimer’s existed)
8. Listeriosis / listeria, including pregnancy food-risk

Not added: duplicates of headache, fever, cough, UTI, diabetes, asthma, stroke, heart attack, and the other already-covered list items.

## 3. New notes

Eight new Markdown files, each citing a URL that was fetched during this work:

| ID | Source page |
| --- | --- |
| `food_safety_at_home` | https://www.cdc.gov/food-safety/prevention/index.html |
| `norovirus` | https://www.nhs.uk/conditions/norovirus/ |
| `adult_vaccination_overview` | https://www.nhs.uk/vaccinations/nhs-vaccinations-and-when-to-have-them/ |
| `cervical_screening` | https://www.nhs.uk/conditions/cervical-screening/what-is-cervical-screening/ |
| `breast_screening` | https://www.nhs.uk/conditions/breast-screening-mammogram/when-youll-be-invited-and-who-should-go/ |
| `bowel_cancer_screening` | https://www.nhs.uk/conditions/bowel-cancer-screening/ |
| `dementia` | https://www.nhs.uk/conditions/dementia/about-dementia/what-is-dementia/ |
| `listeriosis` | https://www.nhs.uk/conditions/listeriosis/ |

Screening and vaccine notes state that eligibility differs by country. They are health education, not a personal screening or immunisation plan. Emergency red-flag wording stays aligned with existing notes (call emergency services; do not replace the deterministic guardrails).

Generator wiring: `scripts/extra_sample_kb_10.py` is appended in `scripts/generate_sample_kb.py` so a future full regenerate would keep these IDs. Do not run the generator now; it would rewrite every existing file.

## 4. Deduplication and validation

- Searched existing IDs, titles, and condition names before adding each file.
- No new file overwrote an existing path.
- Unique IDs after the batch: 1,008.
- Front matter matches the existing six-field schema.
- Cited URLs returned the expected public pages when fetched.

## 5. Indexing

No retrieval-threshold or embedding-model changes. After note validation, rebuild the default general collection:

```powershell
$env:PYTHONPATH="backend"
.\venv\Scripts\python.exe scripts\build_index.py general
```

Optional, slower, and not required for local chat (`EMBEDDING_MODE` defaults to `general`):

```powershell
.\venv\Scripts\python.exe scripts\build_index.py medical
```

## 6. Tests

```powershell
$env:PYTHONPATH="backend"
$env:APP_ENV="development"
$env:LLM_PROVIDER="mock"
$env:MONGODB_URI="memory"
.\venv\Scripts\python.exe -m pytest tests\test_kb_expansion_phase1.py tests\test_everyday_retrieval.py tests\test_pipeline.py -q --tb=short
```

`tests/test_kb_expansion_phase1.py` covers condition names, lay symptoms, synonyms, a multi-symptom query, an absent topic (`Fabry disease`), a new complaint after an unrelated knee question, and emergency phrases that must still trip the existing safety pathway.

Actual results after rebuilding `kb_general` to 1,019 chunks:

```
pytest tests/test_kb_expansion_phase1.py tests/test_everyday_retrieval.py tests/test_pipeline.py
28 passed, 1 warning in 48.53s
```

Labeled retrieval set (22 queries: 8 new topics, 11 existing body-system queries, 3 synonym/multi-word variants):

| Metric | Value |
| --- | --- |
| Recall@1 | 0.864 |
| Recall@4 | 1.000 |
| MRR | 0.932 |

Each of the eight new notes ranked first for its target query. Emergency phrases for chest pain, stroke, severe breathing difficulty, and anaphylaxis still triggered the existing guardrails. `Fabry disease` still has no dedicated note. A norovirus question after a knee-pain history did not reuse the knee complaint.

## 7. Genuinely new topics

**8**, excluding aliases and duplicates.

## 8. Local run

1. Rebuild the general index (command above).
2. Start the API from the project root with the usual `.env` / venv setup.
3. Start the frontend with `npm run dev` in `frontend`.
4. Ask a new-topic question such as “What is the winter vomiting bug?” and a screening question such as “When should I have a smear test?”
