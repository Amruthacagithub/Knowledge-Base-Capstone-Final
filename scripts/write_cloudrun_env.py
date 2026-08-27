"""Write non-secret Cloud Run environment variables from project/.env."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import dotenv_values

NON_SECRET_KEYS = [
    "QDRANT_URL",
    "QDRANT_COLLECTION",
    "GEMINI_MODEL",
    "GEMINI_MODEL_FALLBACK",
    "CORS_ORIGINS",
    "ALLOWED_HOSTS",
    "AUTH_MODE",
    "JWT_ISSUER",
    "JWT_AUDIENCE",
    "ACCESS_TOKEN_MINUTES",
    "MODEL_DEVICE",
    "DOCUMENT_STORAGE_BACKEND",
    "GCS_DOCUMENT_BUCKET",
    "GCS_DOCUMENT_PREFIX",
    "DOCUMENT_CACHE_DIR",
    "EVIDENCE_EXTRACTION_ENABLED",
    "EVIDENCE_GRAPH_ENABLED",
    "TEMPORAL_API_ENABLED",
    "CLAIM_VERIFICATION_ENABLED",
    "LOGIN_RATE_LIMIT_PER_MINUTE",
    "SEARCH_RATE_LIMIT_PER_MINUTE",
]

SECRET_KEYS = {
    "DATABASE_URL",
    "QDRANT_API_KEY",
    "GEMINI_API_KEY",
    "GEMINI_API_KEY_2",
    "GEMINI_API_KEY_3",
    "JWT_SECRET",
}

def main():
    env = dotenv_values(PROJECT_ROOT / ".env")
    out = PROJECT_ROOT / "deploy" / "cloudrun.env.yaml"
    out.parent.mkdir(exist_ok=True)

    lines = []
    for key in NON_SECRET_KEYS:
        val = (env.get(key) or "").strip()
        if val:
            escaped = val.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{key}: "{escaped}"')

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    configured_secrets = sorted(key for key in SECRET_KEYS if env.get(key))
    print(f"Wrote {out} ({len(lines)} non-secret vars)")
    if configured_secrets:
        print(
            "Excluded secrets; bind them from Secret Manager: "
            + ", ".join(configured_secrets)
        )


if __name__ == "__main__":
    main()
