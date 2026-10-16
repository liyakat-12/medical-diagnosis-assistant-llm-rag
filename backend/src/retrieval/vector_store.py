"""
Chroma-backed vector store for storing and searching chunk embeddings.

We keep two separate persistent collections on disk, one per embedding
mode ("general" / "medical"), so Objective 3 (comparing retrieval quality
between a general-purpose and a domain-specific embedding model) can run
both side by side without re-indexing.
"""
from __future__ import annotations

from dataclasses import dataclass

import chromadb

from src.embeddings.embedding_models import (
    collection_name_for,
    get_embedding_model,
    vector_store_dir_for,
)
from src.ingestion.loader import Chunk, build_chunks


@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    distance: float
    metadata: dict
    rerank_score: float | None = None


class VectorStore:
    def __init__(self, mode: str):
        self.mode = mode.strip().lower()
        self.embedder = get_embedding_model(self.mode)
        self.client = chromadb.PersistentClient(path=str(vector_store_dir_for(self.mode)))
        self.collection = self.client.get_or_create_collection(
            name=collection_name_for(self.mode),
            metadata={"hnsw:space": "cosine"},
        )

    def reset(self) -> None:
        try:
            self.client.delete_collection(collection_name_for(self.mode))
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(
            name=collection_name_for(self.mode),
            metadata={"hnsw:space": "cosine"},
        )

    def build(self, chunks: list[Chunk] | None = None, batch_size: int = 64) -> int:
        """(Re)build the index from scratch using the given (or all) chunks."""
        chunks = chunks if chunks is not None else build_chunks()
        self.reset()

        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            texts = [c.text for c in batch]
            embeddings = self.embedder.encode(texts)
            self.collection.add(
                ids=[c.chunk_id for c in batch],
                embeddings=embeddings.tolist(),
                documents=texts,
                metadatas=[c.metadata for c in batch],
            )
        return len(chunks)

    def count(self) -> int:
        return self.collection.count()

    def search(self, query: str, top_k: int = 4) -> list[RetrievedChunk]:
        query_embedding = self.embedder.encode_one(query)
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k,
        )
        retrieved = []
        ids = results["ids"][0]
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        dists = results["distances"][0]
        for chunk_id, text, meta, dist in zip(ids, docs, metas, dists):
            retrieved.append(RetrievedChunk(chunk_id=chunk_id, text=text, distance=dist, metadata=meta))
        return retrieved


if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "medical"
    store = VectorStore(mode)
    n = store.build()
    print(f"Indexed {n} chunks into '{mode}' collection ({store.count()} total in store)")

    results = store.search("I have chest pain and shortness of breath", top_k=3)
    for r in results:
        print("-" * 60)
        print(f"[{r.metadata['title']}] distance={r.distance:.4f} triage={r.metadata['triage_level']}")
        print(r.text[:200])
