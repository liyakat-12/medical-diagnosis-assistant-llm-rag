"""
Central configuration for the Medical Diagnosis Assistant.

All paths and tunable settings live here so the rest of the codebase
never hardcodes a path or reads os.environ directly.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_BASE_DIR = ROOT_DIR / "knowledge_base" / "sample_documents"
DATA_DIR = ROOT_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
VECTOR_STORE_GENERAL_DIR = DATA_DIR / "vector_store_general"
VECTOR_STORE_MEDICAL_DIR = DATA_DIR / "vector_store_medical"
EVAL_DATASETS_DIR = ROOT_DIR / "evaluation" / "datasets"
EVAL_RESULTS_DIR = ROOT_DIR / "evaluation" / "results"

for _dir in (PROCESSED_DIR, VECTOR_STORE_GENERAL_DIR, VECTOR_STORE_MEDICAL_DIR, EVAL_RESULTS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------
CHUNK_SIZE_WORDS = 120
CHUNK_OVERLAP_WORDS = 30

# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------
# General-purpose sentence embedding model (baseline for Objective 3)
GENERAL_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Domain-specific medical embedding model, PubMedBERT fine-tuned for
# semantic search (comparison target for Objective 3)
MEDICAL_EMBEDDING_MODEL = "pritamdeka/S-PubMedBert-MS-MARCO"

EMBEDDING_MODE = os.getenv("EMBEDDING_MODE", "general").strip().lower()  # "general" | "medical"

# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------
TOP_K = int(os.getenv("TOP_K", "4"))

# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------
# "mock" = offline template answers from retrieved passages (no API key needed)
# "groq" = free cloud API | "openai" = paid | "ollama" = local model
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock").strip().lower()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Groq: free tier, no credit card required, OpenAI-compatible API.
# Get a key at https://console.groq.com/keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

JUDGE_MODEL = os.getenv("JUDGE_MODEL", "gpt-4o-mini")


def _looks_like_placeholder(key: str) -> bool:
    key = (key or "").strip()
    if not key:
        return True
    return "your-key-here" in key.lower() or key in {"sk-", "gsk-", "gsk_"}


def resolve_llm_provider() -> str:
    """Return the effective LLM provider, falling back to mock when keys are missing."""
    provider = LLM_PROVIDER.strip().lower()
    if provider == "mock":
        return "mock"
    if provider == "groq" and _looks_like_placeholder(GROQ_API_KEY):
        return "mock"
    if provider == "openai" and _looks_like_placeholder(OPENAI_API_KEY):
        return "mock"
    return provider

# ---------------------------------------------------------------------------
# Safety
# ---------------------------------------------------------------------------
DISCLAIMER = (
    "This tool provides general information retrieved from reference medical "
    "documents. It is NOT a medical device, cannot examine you, and does not "
    "replace a licensed clinician. Always consult a qualified healthcare "
    "professional for diagnosis and treatment."
)
