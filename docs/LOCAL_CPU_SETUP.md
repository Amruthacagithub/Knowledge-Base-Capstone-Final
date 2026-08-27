# Local CPU-Only Setup

Trust-RAG runs locally without a GPU, CUDA, or a Gemini API key. PostgreSQL and Qdrant run in Docker; embedding and reranking run in the Python process on CPU.

Works on **Windows**, **macOS**, and **Linux**.

## Requirements

- Python 3.10 or newer
- Node.js 18 or newer
- Docker Desktop (Windows/macOS) or Docker Engine (Linux)
- Internet access during first installation and first model download

Recommended free resources: 6 GB RAM and 3 GB disk space for retrieval. Claim verification adds an approximately 570 MB NLI model and benefits from 8 GB RAM. After models are cached, inference can run without downloading them again.

## Clean Setup

### Windows (PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install torch==2.12.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install torch==2.12.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
cp .env.example .env
```

In `.env`, set local-only values for:

```dotenv
POSTGRES_PASSWORD=choose-a-local-password
AUTH_MODE=password
JWT_SECRET=choose-at-least-32-random-characters
BOOTSTRAP_USER_PASSWORD=choose-an-initial-user-password
MODEL_DEVICE=cpu
DOCUMENT_STORAGE_BACKEND=local

# Trust-RAG local demo (full pipeline)
EVIDENCE_EXTRACTION_ENABLED=true
EVIDENCE_GRAPH_ENABLED=true
TEMPORAL_API_ENABLED=true
CLAIM_VERIFICATION_ENABLED=true
```

Leave `DATABASE_URL` and `QDRANT_URL` **commented out** for local Docker.

`scripts/init_db.py` hashes `BOOTSTRAP_USER_PASSWORD` with Argon2 for any seeded account that does not yet have a password. Remove `BOOTSTRAP_USER_PASSWORD` from `.env` after initialization; the running API does not need it. Access tokens expire after 30 minutes by default and logout revokes the server-side session.

### Cloud URLs in `.env` but running locally

If `.env` still contains Supabase `DATABASE_URL` or Qdrant Cloud `QDRANT_URL`, local Docker ingest and smoke tests will fail unless you override them:

```bash
export LOCAL_STACK=1              # bash
$env:LOCAL_STACK = "1"          # PowerShell
```

Optional Postgres host port when 5432 is busy:

```bash
export POSTGRES_PORT=5433
$env:POSTGRES_PORT = "5433"
```

`scripts/run_local_trust_stack.sh` / `.ps1` set `LOCAL_STACK=1` and switch to port 5433 when 5432 is already in use.

For an explicitly insecure local evaluator/demo only, set `AUTH_MODE=demo` and start Vite with `VITE_DEMO_LOGIN_ENABLED=true`. Never use demo mode in a shared or deployed environment.

`GEMINI_API_KEY` may remain empty. Search will fall back to cited source excerpts.

Local uploads use `DOCUMENT_STORAGE_BACKEND=local` by default. The optional GCS storage adapter is configured through `DOCUMENT_STORAGE_BACKEND`, `GCS_DOCUMENT_BUCKET`, and `GCS_DOCUMENT_PREFIX`; parsing still runs from an ephemeral local cache.

### One-command stack bootstrap

```powershell
# Windows
.\scripts\run_local_trust_stack.ps1
```

```bash
# macOS / Linux
chmod +x scripts/*.sh
./scripts/run_local_trust_stack.sh
```

This starts Docker, initializes the database, builds the PDF corpus, ingests documents, and runs the CPU runtime check.

### Trust feature endpoints

When the trust flags above are enabled:

- `GET /api/graph/entities?query=billing`
- `GET /api/graph/entities/{entity_id}/paths?query=billing+dependency`
- `GET /api/documents/{id}/versions`
- Search responses include `query_plan`, `claims`, and `evidence_graph` when applicable.

Hidden and nonexistent graph entities intentionally return the same 404 response.

Structured claim verification uses a CPU NLI model when `CLAIM_VERIFICATION_ENABLED=true`. Without Gemini, the verified path still fails safely to cited search excerpts. The first enabled run downloads the NLI model. Run `scripts/check_cpu_runtime.py` with the flag enabled to include NLI inference in the CPU assertion.

Optional NLI override:

```dotenv
NLI_MODEL=cross-encoder/nli-deberta-v3-small
```

Start and initialize manually:

```bash
docker compose up -d
python scripts/init_db.py
python scripts/build_pdf_corpus.py
python scripts/ingest.py
python scripts/check_cpu_runtime.py
```

Expected data invariant for the current clean corpus:

```text
48 unique Markdown documents (+ 10 PDF companions)
58 manifest entries total
```

## Port 5432 Already In Use

Use another host port without stopping the unrelated database:

```bash
export POSTGRES_PORT=55432   # or 5433
docker compose up -d
```

Set the same port in `.env` (or keep `LOCAL_STACK=1` and export `POSTGRES_PORT` in every terminal that runs Python):

```dotenv
POSTGRES_PORT=55432
```

## Run

Backend:

```bash
# Windows
.\venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

# macOS / Linux
./venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Frontend, in another terminal:

```bash
npm --prefix frontend install
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173
```

Sign in with a seeded email and the bootstrap password used during initialization.

Open:

- UI: http://127.0.0.1:5173
- API docs: http://127.0.0.1:8000/docs
- health: http://127.0.0.1:8000/api/health

## Verify

```bash
python -m pytest tests -m "not integration" -q
python scripts/evaluate.py
npm --prefix frontend run test
npm --prefix frontend run build
```

Full Trust evaluation suite:

```powershell
.\scripts\run_full_local_verification.ps1
```

```bash
./scripts/run_full_local_verification.sh
```

With the backend running:

```bash
export SMOKE_API_PASSWORD='the-seeded-user-password'
export SMOKE_TRUST_CHECKS=true
python scripts/smoke_api.py
unset SMOKE_API_PASSWORD SMOKE_TRUST_CHECKS
```

PowerShell equivalents: `$env:SMOKE_API_PASSWORD='...'` and `Remove-Item Env:SMOKE_API_PASSWORD`.

Set `SMOKE_TRUST_CHECKS=auto` (default) to probe whether trust features are enabled on the server.

## CPU Contract

`MODEL_DEVICE` defaults to `cpu`, and all Sentence Transformer/CrossEncoder models receive it explicitly. `scripts/check_cpu_runtime.py` fails if any enabled model is not running on CPU.

The Docker image also installs PyTorch from the official CPU wheel index and does not require an ignored prebuilt Whoosh directory.

Verified on 2026-07-25:

```text
clean image build: PASS
image size: 549,427,034 bytes (~524 MiB)
container torch: 2.12.0+cpu
container CUDA available: false
container embedding inference: PASS on CPU
container reranking inference: PASS on CPU
```
