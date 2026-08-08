"""
Document loading and chunking.

Each source document is a markdown file with a small YAML-like front matter
block (id, title, source, url, condition, triage_level) followed by the
body text. We split the body into overlapping word-window chunks so the
retriever can return focused passages rather than whole documents, while
every chunk still carries its parent document's citation metadata.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from src import config

FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


@dataclass
class Document:
    id: str
    title: str
    source: str
    url: str
    condition: str
    triage_level: str
    body: str


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    source: str
    url: str
    condition: str
    triage_level: str
    text: str
    metadata: dict = field(default_factory=dict)


def _parse_front_matter(raw: str) -> tuple[dict, str]:
    match = FRONT_MATTER_RE.match(raw)
    if not match:
        raise ValueError("Document is missing the required '---' front matter block")
    header_block, body = match.groups()
    meta: dict[str, str] = {}
    for line in header_block.splitlines():
        if not line.strip() or ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta, body.strip()


def load_documents(directory: Path | None = None) -> list[Document]:
    """Load every .md document in the knowledge base directory."""
    directory = directory or config.KNOWLEDGE_BASE_DIR
    documents: list[Document] = []
    for path in sorted(directory.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        meta, body = _parse_front_matter(raw)
        # Strip the leading "# Title" heading line from the body since it
        # duplicates the metadata title.
        body = re.sub(r"^#\s+.*\n+", "", body, count=1)
        documents.append(
            Document(
                id=meta.get("id", path.stem),
                title=meta.get("title", path.stem),
                source=meta.get("source", "Unknown source"),
                url=meta.get("url", ""),
                condition=meta.get("condition", meta.get("title", path.stem)),
                triage_level=meta.get("triage_level", "consult_doctor"),
                body=body,
            )
        )
    return documents


def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> list[str]:
    """Split text into overlapping windows of `chunk_size` words."""
    chunk_size = chunk_size or config.CHUNK_SIZE_WORDS
    overlap = overlap or config.CHUNK_OVERLAP_WORDS
    words = text.split()
    if not words:
        return []
    if len(words) <= chunk_size:
        return [text.strip()]

    chunks = []
    start = 0
    step = max(chunk_size - overlap, 1)
    while start < len(words):
        window = words[start : start + chunk_size]
        chunks.append(" ".join(window))
        if start + chunk_size >= len(words):
            break
        start += step
    return chunks


def build_chunks(documents: Iterable[Document] | None = None) -> list[Chunk]:
    """Load documents (if not given) and split each into cited chunks."""
    documents = list(documents) if documents is not None else load_documents()
    chunks: list[Chunk] = []
    for doc in documents:
        pieces = chunk_text(doc.body)
        for i, piece in enumerate(pieces):
            chunks.append(
                Chunk(
                    chunk_id=f"{doc.id}::chunk{i}",
                    doc_id=doc.id,
                    title=doc.title,
                    source=doc.source,
                    url=doc.url,
                    condition=doc.condition,
                    triage_level=doc.triage_level,
                    text=piece,
                    metadata={
                        "doc_id": doc.id,
                        "title": doc.title,
                        "source": doc.source,
                        "url": doc.url,
                        "condition": doc.condition,
                        "triage_level": doc.triage_level,
                    },
                )
            )
    return chunks


if __name__ == "__main__":
    docs = load_documents()
    all_chunks = build_chunks(docs)
    print(f"Loaded {len(docs)} documents -> {len(all_chunks)} chunks")
    for c in all_chunks[:3]:
        print("-" * 60)
        print(c.chunk_id, "|", c.title, "|", c.triage_level)
        print(c.text[:200])
