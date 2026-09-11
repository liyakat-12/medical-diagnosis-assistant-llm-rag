"""
Build (or rebuild) the vector store index(es).

Usage:
    python scripts/build_index.py            # builds both general + medical
    python scripts/build_index.py medical     # builds only one
    python scripts/build_index.py general
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from src.ingestion.loader import build_chunks, load_documents
from src.retrieval.vector_store import VectorStore


def build_one(mode: str, chunks) -> None:
    print(f"\n=== Building '{mode}' index ===")
    start = time.time()
    store = VectorStore(mode)
    n = store.build(chunks)
    elapsed = time.time() - start
    print(f"Indexed {n} chunks into '{mode}' collection in {elapsed:.1f}s ({store.count()} total)")


def main() -> None:
    modes = sys.argv[1:] or ["general", "medical"]
    docs = load_documents()
    chunks = build_chunks(docs)
    print(f"Loaded {len(docs)} documents -> {len(chunks)} chunks")

    for mode in modes:
        build_one(mode, chunks)


if __name__ == "__main__":
    main()
