from __future__ import annotations

from src.embeddings.embedding_models import get_embedding_model
from src.pipeline.rag_pipeline import run_pipeline


def test_greeting_and_general_skip_retrieval_and_record_timings():
    greeting = run_pipeline("hello")
    general = run_pipeline("Which is better, a car or a bike?")
    assert greeting.timings["retrieve_ms"] == 0
    assert general.timings["retrieve_ms"] == 0
    assert greeting.timings["total_ms"] >= 0
    assert general.timings["total_ms"] >= 0
    assert general.timings["classify_ms"] >= 0


def test_embedding_model_is_cached():
    first = get_embedding_model("general")
    second = get_embedding_model("general")
    assert first is second
