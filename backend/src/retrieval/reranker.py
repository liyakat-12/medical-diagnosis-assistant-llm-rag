"""
Second-stage re-ranking.

The vector store is a fast first pass. A cross-encoder then reads the query
together with each candidate chunk and reorders them, which usually lifts
Recall@1 without changing the knowledge base.
"""
from __future__ import annotations

import math
from functools import lru_cache

from src import config
from src.retrieval.vector_store import RetrievedChunk


@lru_cache(maxsize=1)
def _load_model():
    from sentence_transformers import CrossEncoder

    return CrossEncoder(config.RERANK_MODEL)


def rerank_chunks(query: str, chunks: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
    """Return the top_k chunks ordered by cross-encoder score, highest first."""
    if not chunks or top_k <= 0:
        return []
    if len(chunks) == 1:
        return chunks[:top_k]

    model = _load_model()
    pairs = [(query, chunk.text) for chunk in chunks]
    scores = model.predict(pairs, show_progress_bar=False)
    ranked = sorted(zip(chunks, scores), key=lambda item: float(item[1]), reverse=True)
    reranked: list[RetrievedChunk] = []
    for chunk, score in ranked[:top_k]:
        relevance = 1.0 / (1.0 + math.exp(-float(score)))
        reranked.append(
            RetrievedChunk(
                chunk_id=chunk.chunk_id,
                text=chunk.text,
                distance=1.0 - relevance,
                metadata=chunk.metadata,
                rerank_score=relevance,
            )
        )
    return reranked
