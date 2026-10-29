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

Runtime backends:
  - sentence_transformers: Torch MiniLM / PubMedBERT (local eval, higher RAM)
  - fastembed: ONNX MiniLM for general mode (fits Render free-tier ~512Mi)
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


def _l2_normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-12)
    return matrix / norms


class EmbeddingModel:
    """Thin wrapper around a sentence-transformers or FastEmbed model."""

    def __init__(self, model_name: str, backend: str | None = None):
        self.model_name = model_name
        self.backend = (backend or config.EMBEDDING_BACKEND).strip().lower()
        if self.backend in {"fastembed", "onnx"}:
            if model_name != config.GENERAL_EMBEDDING_MODEL:
                raise ValueError(
                    "fastembed backend currently supports only the general MiniLM model. "
                    "Use EMBEDDING_MODE=general with EMBEDDING_BACKEND=fastembed."
                )
            from fastembed import TextEmbedding

            # Same MiniLM checkpoint as GENERAL_EMBEDDING_MODEL (384-d, cosine-ready).
            self._model = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
            self._encode_impl = self._encode_fastembed
        elif self.backend in {"sentence_transformers", "st", "torch"}:
            self._model = load_sentence_transformer(model_name)
            self._encode_impl = self._encode_sentence_transformers
        else:
            raise ValueError(
                f"Unknown EMBEDDING_BACKEND '{self.backend}'. "
                "Use 'sentence_transformers' or 'fastembed'."
            )

    def _encode_sentence_transformers(self, texts: list[str], batch_size: int) -> np.ndarray:
        return self._model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )

    def _encode_fastembed(self, texts: list[str], batch_size: int) -> np.ndarray:
        # fastembed yields vectors in order; normalize for cosine space parity with ST.
        vectors = list(self._model.embed(texts, batch_size=batch_size))
        matrix = np.asarray(vectors, dtype=np.float32)
        return _l2_normalize(matrix)

    def encode(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        return self._encode_impl(texts, batch_size=batch_size)

    def encode_one(self, text: str) -> np.ndarray:
        return self.encode([text])[0]


def get_embedding_model(mode: str) -> EmbeddingModel:
    """Return a cached embedding model instance for the given mode."""
    return _cached_embedding_model(mode.strip().lower(), config.EMBEDDING_BACKEND.strip().lower())


@lru_cache(maxsize=4)
def _cached_embedding_model(mode: str, backend: str) -> EmbeddingModel:
    if mode == "general":
        return EmbeddingModel(config.GENERAL_EMBEDDING_MODEL, backend=backend)
    if mode == "medical":
        if backend in {"fastembed", "onnx"}:
            raise ValueError(
                "Medical PubMedBERT embeddings require EMBEDDING_BACKEND=sentence_transformers."
            )
        return EmbeddingModel(config.MEDICAL_EMBEDDING_MODEL, backend=backend)
    raise ValueError(f"Unknown embedding mode '{mode}'. Use 'general' or 'medical'.")


def collection_name_for(mode: str) -> str:
    return "kb_general" if mode == "general" else "kb_medical"


def vector_store_dir_for(mode: str):
    return config.VECTOR_STORE_GENERAL_DIR if mode == "general" else config.VECTOR_STORE_MEDICAL_DIR
