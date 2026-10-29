"""Retrieval prerequisites: a populated general index and a loadable reranker.

Build the general index first:
    python scripts/build_index.py general
"""
from __future__ import annotations

import sentence_transformers

from src.ingestion.loader import build_chunks
from src.retrieval import reranker
from src.retrieval.retriever import _get_store


def test_general_index_contains_every_knowledge_base_chunk():
    count = _get_store("general").count()
    expected = len(build_chunks())
    assert count == expected, (
        f"general index has {count} chunks, expected {expected}; "
        "run `python scripts/build_index.py general`"
    )


def test_reranker_downloads_when_model_is_not_cached(monkeypatch):
    calls = []

    class UncachedCrossEncoder:
        def __init__(self, model_name, device=None, local_files_only=False, **kwargs):
            calls.append(local_files_only)
            if local_files_only:
                raise OSError(f"{model_name} is not in the local cache")

    monkeypatch.setattr(sentence_transformers, "CrossEncoder", UncachedCrossEncoder)
    reranker._load_model.cache_clear()
    try:
        model = reranker._load_model()
    finally:
        reranker._load_model.cache_clear()
    assert isinstance(model, UncachedCrossEncoder)
    assert calls == [True, False]
