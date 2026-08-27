# Architecture

## Purpose

TechNova Knowledge Base is an internal document assistant. It answers questions over HR, Engineering, and Sales material while enforcing role-based access control and providing source citations.

## Components

| Component | Responsibility |
|---|---|
| React + Vite frontend | Login, chat, citations, document library, upload, version and Trust-RAG panels |
| FastAPI backend | Authentication, authorization, retrieval orchestration, generation, API endpoints |
| PostgreSQL | Users, roles, documents, immutable versions, chunks, ingest jobs, evidence, traces, conflicts, and sessions |
| Qdrant | Permission-filtered vector retrieval over document chunks |
| Whoosh | Local BM25 keyword index used with Qdrant for hybrid retrieval |
| Gemini (optional) | Structured answer-claim generation; cited-excerpt fallback is used when unavailable |

## Request flow

```text
Browser → FastAPI authentication → RBAC check → query planner
        → Qdrant + BM25 hybrid retrieval → cross-encoder reranker
        → optional graph or temporal retrieval → answer generation
        → optional claim verification → cited response and trace
```

The planner selects one deterministic route: `local`, `global`, `multi_hop`, `temporal`, or `comparison`. Retrieval is authorized before candidates reach reranking or generation. Qdrant applies role filters server-side; BM25 results receive the same access check before fusion.

## Trust-RAG features

- Evidence extraction identifies Engineering entities, claims, and relationships with deterministic rules and stored provenance.
- The evidence graph traverses only visible, current document relationships and records bounded ID-only traces.
- Documents have immutable versions, effective dates, diffs, and conservative conflict candidates. Only Admin can review conflicts.
- Verified generation asks Gemini for strict JSON claims, quarantines instruction-like source text, scores claims against cited evidence with a CPU NLI model, and renders only supported claims.

The four Trust features are controlled through `.env`: `EVIDENCE_EXTRACTION_ENABLED`, `EVIDENCE_GRAPH_ENABLED`, `TEMPORAL_API_ENABLED`, and `CLAIM_VERIFICATION_ENABLED`.

## Access model

| Role | Access |
|---|---|
| Employee | Public documents |
| HR / Engineer / Sales | Public documents plus restricted documents in that department |
| Admin | All documents, upload, and conflict review |

Passwords use Argon2 hashes. Sessions are short-lived JWTs backed by revocable database session records. The API also applies trusted-host/CORS controls, response security headers, and per-process login/search rate limits.

## Corpus and ingestion

The manifest contains 58 entries: 48 Markdown sources and 10 generated PDF companions. Ingestion parses and chunks files, writes document/version/chunk metadata to PostgreSQL, embeds chunks into Qdrant, and rebuilds the local BM25 index. Run `python scripts/ingest.py` after changing corpus files or the manifest.

## Local runtime

Docker supplies PostgreSQL and Qdrant. The setup/start scripts in the repository root provision the local stack and run the API at `http://127.0.0.1:8000` and frontend at `http://127.0.0.1:5173`.
