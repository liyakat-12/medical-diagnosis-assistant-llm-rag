# Project Diagrams (Mermaid source)

These diagrams describe the system **as actually implemented in this
repository**, verified against the code. Paste any block into a mermaid live
editor (https://mermaid.live) to preview and export as PNG/SVG, or recreate
the same structure in draw.io for the final Word document.

> If your synopsis contains the earlier versions of these figures (FAISS,
> BM25 hybrid retrieval, Reciprocal Rank Fusion, confidence-threshold
> abstention, and an anonymised `QUERY_LOG` table), those describe the
> *proposed* design. Cross-encoder re-ranking **is** now implemented.
> See `docs/actual_implementation_report.md` for the full gap analysis.

---

## Figure 3.1 - System Architecture

```mermaid
flowchart TD
    subgraph INDEX["Indexing (offline, run manually via scripts/build_index.py)"]
        A1([400 curated medical notes<br/>knowledge_base/sample_documents/*.md]) --> A2[Front-matter parsing<br/>src/ingestion/loader.py]
        A2 --> A3[Word-window chunking<br/>120 words, 30-word overlap<br/>400 docs to 403 chunks]
        A3 --> A4[Embedding<br/>all-MiniLM-L6-v2 or S-PubMedBert]
        A4 --> A5[(ChromaDB persistent store<br/>cosine / HNSW<br/>data/vector_store_*)]
    end

    subgraph CLIENT["Frontend - React 19 + TypeScript + Vite"]
        C1([User describes symptoms]) --> C2[Follow-up questions<br/>duration, age group, trigger]
        C2 --> C3[POST /api/v1/chats/id/messages/stream]
        C9[Render: 4 matches with %,<br/>urgency, citations] --> C10[Geolocation -> nearby hospitals + map]
    end

    subgraph API["Backend - FastAPI"]
        C3 --> S1{JWT cookie valid?}
        S1 -- No --> S1a[401 Unauthorised]
        S1 -- Yes --> S2{Guardrails<br/>src/safety/guardrails.py}
        S2 -- "Drug / dosage request" --> S2a[Refuse, LLM never called]
        S2 -- "Emergency red flag" --> S2b[Force triage = emergency]
        S2 -- Normal --> S3[Embed query]
        S2b --> S3
        S3 --> S4[Vector search, 12 candidates]
        A5 -.-> S4
        S4 --> S4b[Cross-encoder re-ranker<br/>keep best 4]
        S4b --> S5[Triage from document metadata]<br/>src/safety/triage.py]
        S5 --> S6[match_percents<br/>largest-remainder, sums to 100]
        S6 --> S7[LLM generation using retrieved passages only<br/>mock / Groq / OpenAI / Ollama]
        S7 --> S8[Citation faithfulness audit]
        S8 --> S9[SSE stream: status, token,<br/>citation, triage, metadata, done]
        S9 --> C9
        S8 --> DB[(MongoDB<br/>users / chats / messages)]
    end

    C10 --> H1[GET /api/v1/hospitals/nearby]
    H1 --> H2[OpenStreetMap Overpass API<br/>Haversine distance, top 8]
```

---

## Figure 3.2 - Level 0 Data Flow Diagram (Context Diagram)

```mermaid
flowchart LR
    U([User]) -- "Symptom query + follow-up answers" --> SYS((MediAssist<br/>Medical Diagnosis<br/>Assistant))
    SYS -- "4 matches with %, urgency,<br/>citations, disclaimer" --> U
    SYS -- "Nearby hospitals + map" --> U
    KS([Curated medical notes<br/>WHO / CDC / NHS / Mayo / MedlinePlus]) -- "400 markdown documents" --> SYS
    OSM([OpenStreetMap Overpass API]) -- "Hospital name, address, phone" --> SYS
    LLM([LLM provider<br/>mock / Groq / OpenAI / Ollama]) -- "Generated wording" --> SYS
    SYS -- "Retrieved passages only" --> LLM
```

---

## Figure 3.3 - Level 1 Data Flow Diagram

```mermaid
flowchart TD
    KS([Medical notes]) -- "Markdown files" --> P1(("1.0<br/>Ingestion &amp;<br/>Chunking"))
    P1 --> D1[(D1: knowledge_base/<br/>sample_documents)]
    P1 --> P2(("2.0<br/>Embedding &amp;<br/>Indexing"))
    P2 --> D2[(D2: ChromaDB<br/>vector store)]

    U([User]) -- "1. Credentials" --> P0(("0.0<br/>Authentication"))
    P0 --> D3[(D3: users)]
    P0 -- "JWT cookie" --> U

    U -- "2. Symptom query" --> P3(("3.0<br/>Guardrails &amp;<br/>Query Processing"))
    P3 --> P4(("4.0<br/>Vector Retrieval"))
    D2 -.-> P4
    P4 --> P5(("5.0<br/>Triage &amp;<br/>Percentage Scoring"))
    P5 --> P6(("6.0<br/>Grounded Answer<br/>Generation"))
    P6 --> P7(("7.0<br/>Citation<br/>Faithfulness Audit"))
    P7 --> D4[(D4: chats)]
    P7 --> D5[(D5: messages)]
    P7 -- "3. Answer + citations + triage" --> U

    U -- "4. Location" --> P8(("8.0<br/>Nearby Hospital<br/>Lookup"))
    OSM([Overpass API]) -.-> P8
    P8 -- "5. Hospitals + map" --> U
```

---

## Figure 3.4 - Entity Relationship Diagram

The application database is MongoDB. The three collections below are created
in `backend/app/models/` and indexed in `backend/app/connection/indexes.py`.

```mermaid
erDiagram
    USERS {
        ObjectId _id PK
        string name
        string email UK
        string password_hash
        datetime created_at
        datetime updated_at
        datetime last_login
        bool is_active
        bool medical_disclaimer_accepted
    }
    CHATS {
        ObjectId _id PK
        ObjectId user_id FK
        string title
        datetime created_at
        datetime updated_at
        datetime last_message_at
        int message_count
        bool archived
        object metadata
    }
    MESSAGES {
        ObjectId _id PK
        ObjectId chat_id FK
        ObjectId user_id FK
        string role
        text content
        datetime created_at
        string model
        array citations
        object triage
        array possible_conditions
        object faithfulness
        array recommendations
        bool refused
        string disclaimer
    }

    USERS ||--o{ CHATS : "owns"
    USERS ||--o{ MESSAGES : "authors"
    CHATS ||--o{ MESSAGES : "contains"
```

**Indexes actually created:** unique on `users.email`;
`chats(user_id, updated_at desc)`, `chats(user_id, last_message_at desc)`,
`chats(user_id)`; `messages(chat_id, created_at asc)`, `messages(user_id)`,
`messages(chat_id)`.

> Privacy note, stated accurately: messages are **not** anonymised. Each
> message stores the `user_id` of its author so that chat history can be
> shown back to the correct logged-in user. Passwords are never stored in
> plain text (bcrypt hash only), and the JWT is held in an HTTP-only cookie
> so client-side JavaScript cannot read it.

---

## Figure 3.5 - Knowledge Base Document Structure

The 400 notes are plain markdown with a YAML-style front-matter block. Every
field is used by the running system, which is why citations and urgency can
be shown for any answer.

```mermaid
flowchart LR
    DOC[["sample_documents/dengue_fever.md"]]
    DOC --> F1["id: dengue_fever"]
    DOC --> F2["title + source + url"]
    DOC --> F3["condition: Dengue Fever"]
    DOC --> F4["triage_level: consult_doctor"]
    DOC --> F5["body: 3 paragraphs"]

    F2 --> U2["Citation shown under the answer"]
    F3 --> U3["Name of one of the 4 matches"]
    F4 --> U4["Urgency colour band"]
    F5 --> U5["Chunked, embedded, searched"]
```

---

## Figure 3.6 - System Flowchart of the Query Answering Process

```mermaid
flowchart TD
    START([Start]) --> L1{Logged in?}
    L1 -- No --> L2[Redirect to login] --> ENDX
    L1 -- Yes --> Q1[User enters symptom description]
    Q1 --> C0{Emergency wording<br/>detected in the browser?}
    C0 -- Yes --> Q3[Skip follow-up questions]
    C0 -- No --> Q2[Ask 3 follow-up questions:<br/>duration, age group, trigger]
    Q2 --> Q3
    Q3 --> C1{Drug or dosage<br/>request?}
    C1 -- Yes --> R1[Refuse politely, LLM not called] --> OUT
    C1 -- No --> C2{Server-side emergency<br/>red flag?}
    C2 -- Yes --> E1[Force triage = emergency]
    C2 -- No --> Q4
    E1 --> Q4[Embed query with sentence-transformers]
    Q4 --> Q5[ChromaDB cosine search, 12 candidates]
    Q5 --> Q5r[Cross-encoder re-ranks to top 4]
    Q5r --> C3{Fewer than 4 distinct<br/>conditions returned?}
    C3 -- Yes --> Q5b[Re-query with top-k = 12 and de-duplicate]
    C3 -- No --> Q6
    Q5b --> Q6[Assign triage from document metadata]
    Q6 --> Q7[Normalise scores to 4 percentages summing to 100]
    Q7 --> Q8[Build prompt containing retrieved passages only]
    Q8 --> Q9[LLM generates grounded answer with Source tags]
    Q9 --> Q10[Citation faithfulness audit]
    Q10 --> OUT[Stream to browser over SSE:<br/>4 matches + urgency + citations + disclaimer]
    OUT --> SAVE[(Persist user and assistant<br/>messages in MongoDB)]
    SAVE --> H1{User allows location?}
    H1 -- Yes --> H2[Overpass lookup, show hospitals on map,<br/>show Call 108 button]
    H1 -- No --> ENDX
    H2 --> ENDX([End])
```
