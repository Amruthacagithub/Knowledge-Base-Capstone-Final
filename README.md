# Knowledge Base / Trust-RAG — Capstone Final

**Repository:** https://github.com/Harshinireddy05/Knowledge-Base-Capstone-Final

**Internal Knowledge Assistant** for a fictional company (TechNova) — employees search HR, Engineering, and Sales documents and get cited AI answers under **role-based access control (RBAC)**.

This project delivers **Trust-RAG**: query planning, evidence graphs, document version/conflict workflows, and claim-level verification on top of a production-style RAG stack. Trust features are toggled with environment flags for local demos.

---

## What teammates should read first

1. **This README** — prerequisites, setup, running, and testing.
2. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — system design and feature map.
3. [docs/DEMO.md](docs/DEMO.md) — concise presentation walkthrough.
4. [docs/EVALUATION.md](docs/EVALUATION.md) — reproducible results and limitations.

---

## Features

- **RBAC:** users only see allowed documents (Admin / HR / Engineer / Sales / Employee).
- **Hybrid search:** vector (Qdrant) + BM25 (Whoosh) with a five-route planner.
- **AI answers:** Google Gemini (optional locally); without a key you still get cited excerpts.
- **Trust-RAG (local demo flags on):** evidence extraction, graph paths, temporal versions/conflicts, claim verification (CPU NLI), Trust UI panels.
- **Corpus:** **58** manifest entries — **48** Markdown + **10** PDF companions (HR / Engineering / Sales).
- **UI:** chat + citations, document library, version timeline, claim status, light/dark theme.

---

## Prerequisites (any laptop)

- **Python 3.10+**
- **Node.js 18+**
- **Docker** (Docker Desktop on Windows/macOS, or Docker Engine on Linux)
- **No GPU / CUDA required** — models run on CPU
- **Gemini API key optional** for local demos

Recommended: ~8 GB free RAM if claim verification (NLI) is enabled.

---

## Fast path for teammates (almost one-click)

**Prerequisites once:** Python 3.10+, Node 18+, Docker Desktop (running).

| | Windows | macOS / Linux |
|--|---------|----------------|
| **First time only** | Double-click `setup.bat` | `chmod +x setup.sh start.sh stop.sh` then `./setup.sh` |
| **Every day** | Double-click `start.bat` | `./start.sh` |
| **Stop** | Double-click `stop.bat` | `./stop.sh` |

After start, open **http://127.0.0.1:5173**  
Default password created by setup: **`TrustDemo2026`** (printed by the script; also in `.env`)  
Try: `harshini@company.com` (Engineer) or `bhaskar@company.com` (Admin)

`setup` installs deps + builds the DB/index (slow, once).  
`start` only brings Docker + API + UI back up (fast).

---

## Quick start (manual)

### 1. Clone and enter the project

```bash
git clone https://github.com/Harshinireddy05/Knowledge-Base-Capstone-Final.git
cd Knowledge-Base-Capstone-Final
```

### 2. Python venv + dependencies

**Windows (PowerShell):**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install torch==2.12.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

**macOS / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install torch==2.12.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
cp .env.example .env
```

### 3. Edit `.env` (required)

Set at least:

```dotenv
POSTGRES_PASSWORD=choose-a-local-password
AUTH_MODE=password
JWT_SECRET=choose-at-least-32-random-characters
BOOTSTRAP_USER_PASSWORD=choose-an-initial-user-password
MODEL_DEVICE=cpu
DOCUMENT_STORAGE_BACKEND=local

# Trust-RAG local demo (recommended for teammates)
EVIDENCE_EXTRACTION_ENABLED=true
EVIDENCE_GRAPH_ENABLED=true
TEMPORAL_API_ENABLED=true
CLAIM_VERIFICATION_ENABLED=true
```

Leave cloud `DATABASE_URL` / `QDRANT_URL` **commented out** for local Docker.  
If your `.env` still has cloud URLs, set `LOCAL_STACK=1` (the stack scripts do this for you).

### 4. Bootstrap Docker + DB + ingest

**Windows:**

```powershell
.\scripts\run_local_trust_stack.ps1
```

**macOS / Linux:**

```bash
chmod +x scripts/*.sh
./scripts/run_local_trust_stack.sh
```

This starts Postgres + Qdrant, runs `init_db`, builds PDFs if needed, ingests all **58** documents, and checks CPU models.

If port **5432** is already used on your machine, the script switches to **5433** automatically. You can also set:

```bash
export POSTGRES_PORT=5433   # bash
$env:POSTGRES_PORT = "5433" # PowerShell
```

### 5. Run the app (two terminals)

**Backend:**

```bash
# Windows
.\venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

# macOS / Linux
./venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

If you used `POSTGRES_PORT=5433`, keep `LOCAL_STACK=1` and `POSTGRES_PORT=5433` in that terminal too.

**Frontend:**

```bash
npm --prefix frontend install
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173
```

Open:

- UI: http://127.0.0.1:5173  
- API docs: http://127.0.0.1:8000/docs  
- Health: http://127.0.0.1:8000/api/health  

Sign in with a demo email below and the **bootstrap password** you put in `.env`.

---

## Demo users

| Email | Role |
|-------|------|
| bhaskar@company.com | Admin |
| amrutha@company.com | HR |
| harshini@company.com | Engineer |
| tanvi@company.com | Sales |
| arijith@company.com | Employee only |

Password = `BOOTSTRAP_USER_PASSWORD` from your `.env` (after `init_db`).

---

## Testing

**Windows:**

```powershell
.\scripts\run_full_local_verification.ps1
```

**macOS / Linux:**

```bash
./scripts/run_full_local_verification.sh
```

Or step by step:

```bash
# Backend unit tests (no Docker required)
python -m pytest tests -m "not integration" -q

# Frontend
npm --prefix frontend run lint
npm --prefix frontend run test

# API smoke (backend must be running)
export SMOKE_API_PASSWORD='your-bootstrap-password'   # PowerShell: $env:SMOKE_API_PASSWORD='...'
export SMOKE_TRUST_CHECKS=true
python scripts/smoke_api.py
```

Live browser e2e (optional):

```bash
export PLAYWRIGHT_RUN_E2E=1
export SMOKE_API_PASSWORD='your-bootstrap-password'
npm --prefix frontend run test:e2e
```

---

## Project structure

```
project/
├── backend/           # FastAPI, RAG + Trust pipeline
├── frontend/          # React + Vite (+ Playwright e2e)
├── documents/         # 58-entry manifest + HR/Engineering/Sales files
├── evaluation/        # Frozen benchmarks + REVIEW_NOTES.md
├── scripts/           # init, ingest, eval, stack helpers (.ps1 + .sh)
├── tests/             # pytest suite
├── docs/              # Current architecture, demo, and evaluation documentation
├── migrations/        # Alembic 0001–0008
└── archive/           # Local-only clutter (gitignored; not needed to run)
```

---

## Docs map

| Doc | Purpose |
|-----|---------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Components, data flow, data model, and security controls |
| [DEMO.md](docs/DEMO.md) | Short, reliable presentation walkthrough |
| [EVALUATION.md](docs/EVALUATION.md) | Validation commands, results, and known limits |
| [LOCAL_CPU_SETUP.md](docs/LOCAL_CPU_SETUP.md) | Detailed CPU-only setup and local-stack troubleshooting |
| [LOCAL_SECURITY.md](docs/LOCAL_SECURITY.md) | Local security scope, authentication, and repository hygiene |

---

## Honest limits (say this in demos)

- Graph vs hybrid **path gain is 0.0** on the local comparison set — hybrid already finds many multi-hop paths.
- Claim NLI is good but not perfect (~0.88 holdout macro F1).
- Evals are **agent-reviewed**, not independent human IRB.
- Enterprise OIDC / Redis rate limits / pentest (**Phase 9E**) are **out of local scope**.

---

## After changing documents

```bash
python scripts/ingest.py
```

Re-run ingest after manifest changes, PDF rebuild, or chunk-schema updates.
