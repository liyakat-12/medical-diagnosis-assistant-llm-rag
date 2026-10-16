"""
High-level retriever used by the RAG pipeline.

Wraps VectorStore.search() and formats results into a clean list of
"evidence" items, each carrying the exact citation (source name + URL)
that the LLM must attach to any claim it makes from that passage.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from src import config
from src.retrieval.vector_store import VectorStore


@dataclass
class Evidence:
    text: str
    title: str
    source: str
    url: str
    condition: str
    triage_level: str
    relevance_score: float  # higher is better (1 - cosine distance)
    doc_id: str = ""

    def citation(self) -> str:
        return f"{self.title} ({self.source})"


@lru_cache(maxsize=2)
def _get_store(mode: str) -> VectorStore:
    return VectorStore(mode)


def retrieve(query: str, top_k: int | None = None, mode: str | None = None, rerank: bool | None = None) -> list[Evidence]:
    from src.retrieval.reranker import rerank_chunks

    mode = (mode or config.EMBEDDING_MODE).strip().lower()
    top_k = top_k or config.TOP_K
    use_rerank = config.RERANK_ENABLED if rerank is None else rerank
    store = _get_store(mode)
    fetch_k = max(top_k, config.RERANK_CANDIDATES) if use_rerank else top_k
    results = store.search(query, top_k=fetch_k)
    if use_rerank:
        results = rerank_chunks(query, results, top_k)
    else:
        results = results[:top_k]

    evidence = []
    for r in results:
        if r.rerank_score is not None:
            score = float(r.rerank_score)
        else:
            score = 1.0 - float(r.distance)
        evidence.append(
            Evidence(
                text=r.text,
                title=r.metadata.get("title", "Unknown"),
                source=r.metadata.get("source", "Unknown source"),
                url=r.metadata.get("url", ""),
                condition=r.metadata.get("condition", "Unknown"),
                triage_level=r.metadata.get("triage_level", "consult_doctor"),
                relevance_score=score,
                doc_id=str(r.metadata.get("doc_id") or ""),
            )
        )
    return evidence
