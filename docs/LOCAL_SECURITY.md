# Local Security Notes (Trust-RAG)

Scope: local development and agent-reviewed demos only. This document does **not** replace enterprise OIDC, distributed rate limiting, penetration testing, or production credential rotation (plan gate 9E — skipped for local completion).

## Authentication modes

| Mode | Variable | Use |
|------|----------|-----|
| **Password** | `AUTH_MODE=password` | Recommended for local Trust-RAG demos. Argon2-hashed users, revocable JWT sessions. |
| **Demo** | `AUTH_MODE=demo` | Accepts any seeded email without a password. **Do not expose to the network.** |

Copy `.env.example` to `.env` and set:

- `JWT_SECRET` — use a long random value (≥32 bytes). Never commit `.env`.
- `BOOTSTRAP_USER_PASSWORD` — initial password for seeded users when the database is empty.

Rotate `JWT_SECRET` and user passwords before any shared or staging deployment.

## Secrets and repository hygiene

Never commit:

- `.env` (listed in `.gitignore`)
- `deploy/cloudrun.env.yaml` (listed in `.gitignore`)
- API keys (`GEMINI_API_KEY`, `QDRANT_API_KEY`, database passwords)

Generated runtime artifacts are also ignored:

- `indexdir/` — Whoosh BM25 index
- `postgres_data/`, `qdrant_data/` — Docker volumes
- `.cache/` — Hugging Face / sentence-transformers model downloads
- `frontend/test-results/` — Playwright output

## Rate limiting

`backend/services/rate_limit.py` implements a **per-process** sliding-window limiter. It protects a single uvicorn worker from abuse but is **not** shared across replicas. Multi-instance deployments need Redis or an API gateway limiter.

## Prompt-source quarantine

Before generation and claim verification, retrieved source text passes through `backend/services/prompt_safety.py`. Instruction-like patterns (override prompts, role tags, credential exfiltration requests) are quarantined and replaced with a neutral placeholder. The quarantine is deliberately high-precision; some legitimate security runbooks may be omitted from the model context.

## Trust feature flags

Local demos enable evidence extraction, graph traversal, temporal APIs, and claim verification via `.env.example` defaults. Disable any flag you do not need to reduce attack surface during development.

## What local completion does not cover

- Enterprise OIDC / SSO
- Distributed throttling (Redis)
- External penetration test
- Automated credential rotation in production
- Public internet exposure of demo auth

Cloud deployment hardening is intentionally outside this local project handover. Do not expose demo authentication to the public internet.
