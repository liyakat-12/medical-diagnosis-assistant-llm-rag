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


def _device() -> str:
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


@lru_cache(maxsize=1)
def _load_model():
    from sentence_transformers import CrossEncoder

    device = _device()
    try:
        return CrossEncoder(config.RERANK_MODEL, device=device, automodel_args={"local_files_only": True})
    except TypeError:
        try:
            return CrossEncoder(config.RERANK_MODEL, device=device, local_files_only=True)
        except TypeError:
            return CrossEncoder(config.RERANK_MODEL, device=device)
    except Exception:
        return CrossEncoder(config.RERANK_MODEL, device=device)


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
        vector_score = (
            float(chunk.vector_score)
            if chunk.vector_score is not None
            else max(0.0, 1.0 - float(chunk.distance))
        )
        reranked.append(
            RetrievedChunk(
                chunk_id=chunk.chunk_id,
                text=chunk.text,
                distance=1.0 - relevance,
                metadata=chunk.metadata,
                rerank_score=relevance,
                vector_score=vector_score,
            )
        )
    return reranked
