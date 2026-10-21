"""
Embedding model wrappers.

We expose two interchangeable embedding backends so we can quantitatively
compare a general-purpose sentence embedding model against a domain-specific
medical embedding model (Objective 3 of the project):

  - "general": sentence-transformers/all-MiniLM-L6-v2
  - "medical": pritamdeka/S-PubMedBert-MS-MARCO (PubMedBERT fine-tuned
               for semantic search)

Both expose the same .encode(texts) -> np.ndarray interface so the rest of
the pipeline (indexing, retrieval) never needs to know which one is active.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from src import config


def _device() -> str:
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def load_sentence_transformer(model_name: str):
    """Load from the local Hugging Face cache first so a missing network does not stall."""
    from sentence_transformers import SentenceTransformer

    device = _device()
    try:
        return SentenceTransformer(model_name, device=device, local_files_only=True)
    except Exception:
        return SentenceTransformer(model_name, device=device)


class EmbeddingModel:
    """Thin wrapper around a sentence-transformers model."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = load_sentence_transformer(model_name)

    def encode(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        return self._model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )

    def encode_one(self, text: str) -> np.ndarray:
        return self.encode([text])[0]


@lru_cache(maxsize=4)
def get_embedding_model(mode: str) -> EmbeddingModel:
    """Return a cached embedding model instance for the given mode."""
    mode = mode.strip().lower()
    if mode == "general":
        return EmbeddingModel(config.GENERAL_EMBEDDING_MODEL)
    if mode == "medical":
        return EmbeddingModel(config.MEDICAL_EMBEDDING_MODEL)
    raise ValueError(f"Unknown embedding mode '{mode}'. Use 'general' or 'medical'.")


def collection_name_for(mode: str) -> str:
    return "kb_general" if mode == "general" else "kb_medical"


def vector_store_dir_for(mode: str):
    return config.VECTOR_STORE_GENERAL_DIR if mode == "general" else config.VECTOR_STORE_MEDICAL_DIR
