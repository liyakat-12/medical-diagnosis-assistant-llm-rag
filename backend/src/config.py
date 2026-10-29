"""
Central configuration for the Medical Diagnosis Assistant.

All paths and tunable settings live here so the rest of the codebase
never hardcodes a path or reads os.environ directly.
"""
from __future__ import annotations

import os
from pathlib import Path

# Set before chromadb / huggingface imports so they do not wait on the network.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("CHROMA_TELEMETRY_IMPLEMENTATION", "none")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "2")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from dotenv import load_dotenv

# backend/src/config.py → project root is two levels above backend/
BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent
load_dotenv(ROOT_DIR / ".env")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
KNOWLEDGE_BASE_DIR = ROOT_DIR / "knowledge_base" / "sample_documents"
DATA_DIR = ROOT_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
VECTOR_STORE_GENERAL_DIR = DATA_DIR / "vector_store_general"
VECTOR_STORE_MEDICAL_DIR = DATA_DIR / "vector_store_medical"
USERS_PATH = DATA_DIR / "users.json"
CHATS_PATH = DATA_DIR / "chats.json"
EVAL_DATASETS_DIR = ROOT_DIR / "evaluation" / "datasets"
EVAL_RESULTS_DIR = ROOT_DIR / "evaluation" / "results"

# ---------------------------------------------------------------------------
# App / auth / MongoDB
# ---------------------------------------------------------------------------
APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
APP_DEBUG = os.getenv("APP_DEBUG", "true").strip().lower() in {"1", "true", "yes"}
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "mediassist")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-change-me")
JWT_ACCESS_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_EXPIRE_MINUTES", "30"))
JWT_REFRESH_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_EXPIRE_DAYS", "14"))
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]
COOKIE_SECURE = APP_ENV == "production"
ACCESS_COOKIE = "mediassist_access"
REFRESH_COOKIE = "mediassist_refresh"
DEMO_EMAIL = os.getenv("DEMO_EMAIL", "demo@clinic.local")
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "demo123")
DEMO_NAME = os.getenv("DEMO_NAME", "Demo Patient")
CHAT_HISTORY_WINDOW = int(os.getenv("CHAT_HISTORY_WINDOW", "8"))
EMERGENCY_REGION = os.getenv("EMERGENCY_REGION", "IN").strip().upper() or "IN"
EMERGENCY_NUMBER = os.getenv("EMERGENCY_NUMBER", "112").strip() or "112"
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "20"))
LLM_MEDICAL_MAX_TOKENS = int(os.getenv("LLM_MEDICAL_MAX_TOKENS", "450"))
LLM_GENERAL_MAX_TOKENS = int(os.getenv("LLM_GENERAL_MAX_TOKENS", "1200"))

_UNSAFE_JWT_SECRETS = {
    "",
    "dev-only-change-me",
    "change-this-to-a-long-random-string",
    "replace-with-a-long-unique-local-secret",
    "changeme",
    "secret",
    "jwt-secret",
}


def is_production() -> bool:
    return APP_ENV in {"production", "prod"}


def jwt_secret_is_unsafe(secret: str | None = None) -> bool:
    value = (JWT_SECRET if secret is None else secret) or ""
    stripped = value.strip()
    if stripped.lower() in {item.lower() for item in _UNSAFE_JWT_SECRETS}:
        return True
    return len(stripped) < 24


def mongo_uri_mode(uri: str | None = None) -> str:
    """Return 'memory' or 'persistent'. Raises ValueError for unsupported URIs."""
    value = (MONGODB_URI if uri is None else uri).strip()
    lowered = value.lower()
    if lowered in {"memory", "mongomock"}:
        return "memory"
    if lowered.startswith("mongodb://") or lowered.startswith("mongodb+srv://"):
        return "persistent"
    raise ValueError(
        "MONGODB_URI must be mongodb://..., mongodb+srv://..., or memory. "
        "MediAssist will not switch databases automatically."
    )


def validate_runtime_config() -> None:
    """Fail closed in production; warn in development. Never logs secret values."""
    import logging

    log = logging.getLogger("mediassist.config")
    production = is_production()
    if jwt_secret_is_unsafe():
        message = (
            "JWT_SECRET is missing, shorter than 24 characters, or a known placeholder. "
            "Set a unique secret. Rotating JWT_SECRET invalidates existing access and refresh cookies."
        )
        if production:
            raise RuntimeError(message)
        log.warning(message)
    try:
        mode = mongo_uri_mode()
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc
    log.info("Database mode=%s db=%s", mode, MONGODB_DB_NAME)
    if "*" in CORS_ORIGINS:
        message = (
            "CORS_ORIGINS cannot include * while the API sends credentialed cookies. "
            "List explicit frontend origins instead."
        )
        if production:
            raise RuntimeError(message)
        log.warning(message)
    provider = LLM_PROVIDER.strip().lower()
    if provider == "groq" and _looks_like_placeholder(GROQ_API_KEY):
        message = (
            "LLM_PROVIDER=groq but GROQ_API_KEY is missing or a placeholder. "
            "Set a real Groq key, or set LLM_PROVIDER=mock for offline template answers."
        )
        if production:
            raise RuntimeError(message)
        log.warning(message)
    if provider == "openai" and _looks_like_placeholder(OPENAI_API_KEY):
        message = (
            "LLM_PROVIDER=openai but OPENAI_API_KEY is missing or a placeholder. "
            "Set a real OpenAI key, or set LLM_PROVIDER=mock for offline template answers."
        )
        if production:
            raise RuntimeError(message)
        log.warning(message)

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
# sentence_transformers (Torch, local/dev) | fastembed (ONNX, low-memory production)
EMBEDDING_BACKEND = os.getenv("EMBEDDING_BACKEND", "sentence_transformers").strip().lower()

# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------
TOP_K = int(os.getenv("TOP_K", "4"))
RERANK_ENABLED = os.getenv("RERANK_ENABLED", "true").strip().lower() in {"1", "true", "yes"}
RERANK_CANDIDATES = int(os.getenv("RERANK_CANDIDATES", "12"))
RERANK_MODEL = os.getenv("RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
# Drop noisy matches when the best retrieved chunk is weaker than this (0–1).
# Applied to rerank sigmoid scores when a cross-encoder is enabled.
MIN_RELEVANCE_SCORE = float(os.getenv("MIN_RELEVANCE_SCORE", "0.22"))
# Dense cosine similarity (1 - distance) floor used alongside rerank scores so
# clinically relevant hits are not discarded when the cross-encoder is poorly
# calibrated on short symptom / body-map queries.
MIN_VECTOR_SCORE = float(os.getenv("MIN_VECTOR_SCORE", "0.38"))

# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------
# "mock" = offline template answers from retrieved passages (no API key needed)
# "groq" = free cloud API | "openai" = paid | "ollama" = local model
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock").strip().lower()
# When local notes are a weak match, a real LLM (Groq/OpenAI/Ollama) may fill
# the same urgency / match / source cards from general knowledge.
LLM_KB_FALLBACK = os.getenv("LLM_KB_FALLBACK", "true").strip().lower() in {"1", "true", "yes"}

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Groq: free tier, no credit card required, OpenAI-compatible API.
# Get a key at https://console.groq.com/keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
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
    """Return the effective LLM provider.

    Development may fall back to mock when a cloud key is missing.
    Production never silently substitutes mock for a misconfigured cloud provider;
    validate_runtime_config() fails closed at startup instead.
    """
    provider = LLM_PROVIDER.strip().lower()
    if provider == "mock":
        return "mock"
    if provider == "groq" and _looks_like_placeholder(GROQ_API_KEY):
        if is_production():
            raise RuntimeError(
                "LLM_PROVIDER=groq but GROQ_API_KEY is missing or a placeholder."
            )
        return "mock"
    if provider == "openai" and _looks_like_placeholder(OPENAI_API_KEY):
        if is_production():
            raise RuntimeError(
                "LLM_PROVIDER=openai but OPENAI_API_KEY is missing or a placeholder."
            )
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
