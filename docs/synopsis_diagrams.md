# Synopsis Diagrams (Mermaid source)

These are editable mermaid versions of Figures 3.1-3.5 referenced in the
project synopsis. Paste any block into a mermaid live editor
(https://mermaid.live) to preview and export as PNG/SVG, or recreate the
same structure in draw.io for the final Word document.

---

## Figure 3.1 - System Architecture of the Proposed Assistant

```mermaid
flowchart TD
    subgraph OFFLINE["Offline Pipeline (run once, in advance)"]
        A1([Medical Document Sources<br/>WHO / CDC / NICE / MedQuAD]) --> A2[Data Collection &amp; Preprocessing]
        A2 --> A3[Chunking<br/>400-800 tokens, ~15% overlap]
        A3 --> A4[Embedding<br/>PubMedBERT / MiniLM]
        A4 --> A5[(Vector Index<br/>FAISS)]
        A3 --> A6[(Keyword Index<br/>BM25)]
    end

    subgraph ONLINE["Online Pipeline (per user query)"]
        B1([User Symptom Query]) --> B2{Safety Check:<br/>Emergency indicators?}
        B2 -- Yes --> B2a[Display Emergency Advisory]
        B2a -- continue --> B3[Query Embedding]
        B2 -- No --> B3
        B3 --> B4[Hybrid Retrieval<br/>Dense + BM25 + RRF Fusion]
        A5 -.-> B4
        A6 -.-> B4
        B4 --> B5[Cross-Encoder Re-ranking]
        B5 --> B6[Constrained Prompt Construction]
        B6 --> B7[LLM Generation<br/>GPT-4o / Claude / Llama 3.1]
        B7 --> B8[Citation Mapping &amp; Triage Assignment]
        B8 --> B9([Answer + Citations + Triage Level + Disclaimer])
    end
```

---

## Figure 3.2 - Level 0 Data Flow Diagram (Context Diagram)

```mermaid
flowchart LR
    U([User]) -- "Symptom Query" --> SYS((Medical Diagnosis<br/>Assistant System))
    SYS -- "Diagnosis Suggestions +<br/>Citations + Triage Level" --> U
    KS([Medical Knowledge Sources<br/>WHO / CDC / MedQuAD]) -- "Guideline Documents" --> SYS
```

---

## Figure 3.3 - Level 1 Data Flow Diagram

```mermaid
flowchart TD
    U([User]) -- "1. Symptom Query" --> P3(("3.0<br/>Query Processing<br/>&amp; Safety Check"))
    KS([Medical Knowledge Sources]) -- "Documents" --> P1(("1.0<br/>Data Collection &amp;<br/>Preprocessing"))

    P1 --> D1[(D1: Document Store)]
    D1 --> P2(("2.0<br/>Chunking &amp;<br/>Indexing"))
    P2 --> D2[(D2: Vector + Keyword Index)]

    P3 --> P4(("4.0<br/>Retrieval &amp;<br/>Re-ranking"))
    D2 -.-> P4
    P4 --> P5(("5.0<br/>Answer Generation &amp;<br/>Citation Mapping"))
    D1 -.-> P5
    P5 --> D3[(D3: Anonymized Query Log)]
    P5 -- "Answer + Citations + Triage" --> U
```

---

## Figure 3.4 - Entity Relationship Diagram

```mermaid
erDiagram
    DOCUMENT {
        string doc_id PK
        string title
        string source
        string publisher
        string url
        int year
        string triage_level
    }
    CHUNK {
        string chunk_id PK
        string doc_id FK
        text chunk_text
        int token_count
        string section_heading
    }
    QUERY_LOG {
        string query_id PK
        text anonymized_query_text
        datetime timestamp
        string triage_level
    }
    CITATION {
        string citation_id PK
        string query_id FK
        string chunk_id FK
        float relevance_score
    }

    DOCUMENT ||--o{ CHUNK : "is split into"
    QUERY_LOG ||--o{ CITATION : "supported by"
    CHUNK ||--o{ CITATION : "cited in"
```

> Note: `QUERY_LOG` intentionally has no name, contact, or user-identifier
> field - only anonymized query text and system metrics are retained, per
> the privacy clarification in Sections 1.4 and 3.6.

---

## Figure 3.5 - System Flowchart of the Query Answering Process

```mermaid
flowchart TD
    START([Start]) --> Q1[User enters symptom<br/>description]
    Q1 --> C1{Emergency indicators<br/>detected?}
    C1 -- Yes --> E1[Display emergency advisory]
    E1 --> Q2
    C1 -- No --> Q2[Convert query to vector]
    Q2 --> Q3[Hybrid retrieval:<br/>dense search + BM25]
    Q3 --> Q4[Fuse rankings<br/>Reciprocal Rank Fusion]
    Q4 --> Q5[Cross-encoder re-ranking]
    Q5 --> C2{Retrieval confidence<br/>above threshold?}
    C2 -- No --> A1[Abstain:<br/>"insufficient evidence" message]
    A1 --> ENDX
    C2 -- Yes --> Q6[Build constrained prompt<br/>with top passages]
    Q6 --> Q7[LLM generates<br/>grounded answer]
    Q7 --> Q8[Map claims to citations]
    Q8 --> Q9[Assign triage level]
    Q9 --> Q10([Display answer + citations<br/>+ triage + disclaimer])
    Q10 --> ENDX([End])
```
