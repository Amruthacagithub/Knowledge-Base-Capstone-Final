"""
Application configuration — loads environment variables from .env file.
Works locally (Docker Postgres + Qdrant) and online (Supabase + Qdrant Cloud).
"""
import os
import tempfile
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

_LOCAL_STACK = os.getenv("LOCAL_STACK", os.getenv("QDRANT_LOCAL", "")).strip().lower() in {
    "1",
    "true",
    "yes",
}

# PostgreSQL — use DATABASE_URL for Supabase; otherwise build from parts (local Docker)
_database_url = os.getenv("DATABASE_URL", "").strip()
if _LOCAL_STACK:
    _database_url = ""
if _database_url:
    DATABASE_URL = _database_url
else:
    POSTGRES_USER = os.getenv("POSTGRES_USER", "ekip")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "").strip()
    if not POSTGRES_PASSWORD:
        raise RuntimeError("POSTGRES_PASSWORD is required when DATABASE_URL is not set")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "ekip")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
    DATABASE_URL = (
        f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )

# Qdrant — QDRANT_URL + QDRANT_API_KEY for Qdrant Cloud; else host/port (local Docker)
QDRANT_URL = os.getenv("QDRANT_URL", "").strip()
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "").strip()
if _LOCAL_STACK or os.getenv("QDRANT_LOCAL", "").strip().lower() in {"1", "true", "yes"}:
    QDRANT_URL = ""
    QDRANT_API_KEY = ""
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "enterprise_docs")

# Gemini — primary key (backward compatible)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Authentication and JWT
AUTH_MODE = os.getenv("AUTH_MODE", "password").strip().lower()
if AUTH_MODE not in {"password", "demo"}:
    raise RuntimeError("AUTH_MODE must be password or demo")

JWT_SECRET = os.getenv("JWT_SECRET", "").strip()
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET is required")
if AUTH_MODE == "password" and len(JWT_SECRET) < 32:
    raise RuntimeError("JWT_SECRET must contain at least 32 characters")
JWT_ALGORITHM = "HS256"
JWT_ISSUER = os.getenv("JWT_ISSUER", "trust-rag").strip() or "trust-rag"
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "trust-rag-api").strip() or "trust-rag-api"
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "30"))
if not 5 <= ACCESS_TOKEN_MINUTES <= 1440:
    raise RuntimeError("ACCESS_TOKEN_MINUTES must be between 5 and 1440")
BOOTSTRAP_USER_PASSWORD = os.getenv("BOOTSTRAP_USER_PASSWORD", "")

# CORS — comma-separated origins (add your Vercel URL in production)
_default_cors = (
    "http://localhost:5173,http://localhost:5174,"
    "http://127.0.0.1:5173,http://127.0.0.1:5174,http://localhost:3000"
)
CORS_ORIGINS = os.getenv("CORS_ORIGINS", _default_cors)
ALLOWED_HOSTS = os.getenv(
    "ALLOWED_HOSTS",
    "localhost,127.0.0.1,testserver,*.run.app",
)
LOGIN_RATE_LIMIT_PER_MINUTE = int(os.getenv("LOGIN_RATE_LIMIT_PER_MINUTE", "10"))
SEARCH_RATE_LIMIT_PER_MINUTE = int(os.getenv("SEARCH_RATE_LIMIT_PER_MINUTE", "60"))
if LOGIN_RATE_LIMIT_PER_MINUTE < 1 or SEARCH_RATE_LIMIT_PER_MINUTE < 1:
    raise RuntimeError("Rate limits must be positive")

# Paths
DOCUMENTS_DIR = Path(os.getenv("DOCUMENTS_DIR", PROJECT_ROOT / "documents")).resolve()
BM25_INDEX_DIR = Path(os.getenv("BM25_INDEX_DIR", PROJECT_ROOT / "indexdir")).resolve()
DOCUMENT_STORAGE_BACKEND = os.getenv("DOCUMENT_STORAGE_BACKEND", "local").strip().lower()
if DOCUMENT_STORAGE_BACKEND not in {"local", "gcs"}:
    raise RuntimeError("DOCUMENT_STORAGE_BACKEND must be local or gcs")
GCS_DOCUMENT_BUCKET = os.getenv("GCS_DOCUMENT_BUCKET", "").strip()
GCS_DOCUMENT_PREFIX = os.getenv("GCS_DOCUMENT_PREFIX", "uploads").strip("/") or "uploads"
DOCUMENT_CACHE_DIR = Path(
    os.getenv(
        "DOCUMENT_CACHE_DIR",
        Path(tempfile.gettempdir()) / "trust-rag-documents",
    )
).resolve()
if DOCUMENT_STORAGE_BACKEND == "gcs" and not GCS_DOCUMENT_BUCKET:
    raise RuntimeError("GCS_DOCUMENT_BUCKET is required for GCS document storage")

# Embedding model
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

# Reranker model
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# Three-way natural-language inference for claim verification.
NLI_MODEL = os.getenv(
    "NLI_MODEL",
    "cross-encoder/nli-deberta-v3-small",
).strip()

# Local inference defaults to CPU so no GPU or CUDA runtime is required.
MODEL_DEVICE = os.getenv("MODEL_DEVICE", "cpu").strip().lower() or "cpu"

# Evidence extraction is opt-in until the annotated quality gate is met.
EVIDENCE_EXTRACTION_ENABLED = os.getenv(
    "EVIDENCE_EXTRACTION_ENABLED",
    "false",
).strip().lower() in {"1", "true", "yes", "on"}
EVIDENCE_GRAPH_ENABLED = os.getenv(
    "EVIDENCE_GRAPH_ENABLED",
    "false",
).strip().lower() in {"1", "true", "yes", "on"}
TEMPORAL_API_ENABLED = os.getenv(
    "TEMPORAL_API_ENABLED",
    "false",
).strip().lower() in {"1", "true", "yes", "on"}
CLAIM_VERIFICATION_ENABLED = os.getenv(
    "CLAIM_VERIFICATION_ENABLED",
    "false",
).strip().lower() in {"1", "true", "yes", "on"}

# Cloud free tier: disable vector search / reranker to avoid torch on 512MB instances.
VECTOR_SEARCH_ENABLED = os.getenv(
    "VECTOR_SEARCH_ENABLED",
    "true",
).strip().lower() in {"1", "true", "yes", "on"}
RERANKER_ENABLED = os.getenv(
    "RERANKER_ENABLED",
    "true",
).strip().lower() in {"1", "true", "yes", "on"}


def get_gemini_api_keys() -> list[str]:
    """
    Ordered Gemini API keys: GEMINI_API_KEY, then GEMINI_API_KEY_2, _3, …
    Skips empty values and duplicates. At least one key is required for LLM answers.
    """
    keys: list[str] = []
    seen: set[str] = set()

    def add(key: str | None) -> None:
        if key and key.strip() and key.strip() not in seen:
            seen.add(key.strip())
            keys.append(key.strip())

    add(os.getenv("GEMINI_API_KEY"))
    n = 2
    while True:
        extra = os.getenv(f"GEMINI_API_KEY_{n}")
        if not extra:
            break
        add(extra)
        n += 1

    return keys


def get_gemini_models() -> list[str]:
    """
    Ordered Gemini models: primary then fallbacks when overloaded (503) or rate-limited.
    Override with GEMINI_MODEL and GEMINI_MODEL_FALLBACK (comma-separated) in .env.
    """
    primary = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite").strip()
    fallback_raw = os.getenv(
        "GEMINI_MODEL_FALLBACK",
        "gemini-3.1-flash-lite,gemini-2.5-flash,gemini-3.5-flash,gemini-3-flash-preview",
    )
    models: list[str] = []
    seen: set[str] = set()
    for name in [primary, *fallback_raw.split(",")]:
        name = name.strip()
        if name and name not in seen:
            seen.add(name)
            models.append(name)
    return models or ["gemini-2.5-flash-lite"]
