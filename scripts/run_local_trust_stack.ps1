# Start and verify the local Trust-RAG stack (CPU-only, no Gemini required).
# Usage: .\scripts\run_local_trust_stack.ps1
# Requires: Docker Desktop, venv, .env with BOOTSTRAP_USER_PASSWORD set.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path ".\venv\Scripts\python.exe")) {
    Write-Error "venv not found. Run: python -m venv venv ; .\venv\Scripts\Activate.ps1 ; pip install -r requirements.txt"
}

if (-not (Test-Path ".\.env")) {
    Write-Error ".env not found. Copy-Item .env.example .env and set BOOTSTRAP_USER_PASSWORD."
}

# .env may point at cloud services; local Docker stack must use localhost.
Write-Host "=== Forcing local stack (LOCAL_STACK=1) ==="
$env:LOCAL_STACK = "1"

# If host port 5432 is taken, use 5433 for this project's Postgres container.
if (-not $env:POSTGRES_PORT) {
    $env:POSTGRES_PORT = "5432"
}
$portProbe = Test-NetConnection -ComputerName 127.0.0.1 -Port $env:POSTGRES_PORT -WarningAction SilentlyContinue
# TcpTestSucceeded = something is already listening on the port.
if ($portProbe.TcpTestSucceeded -and $env:POSTGRES_PORT -eq "5432") {
    Write-Host "Port 5432 is in use; using POSTGRES_PORT=5433 for docker compose."
    $env:POSTGRES_PORT = "5433"
}

Write-Host "=== Starting Docker services ==="
docker compose up -d

Write-Host "=== Initializing database ==="
.\venv\Scripts\python.exe scripts\init_db.py

Write-Host "=== Building PDF corpus (if needed) ==="
.\venv\Scripts\python.exe scripts\build_pdf_corpus.py

Write-Host "=== Ingesting documents ==="
.\venv\Scripts\python.exe scripts\ingest.py

Write-Host "=== Checking CPU runtime ==="
.\venv\Scripts\python.exe scripts\check_cpu_runtime.py

Write-Host ""
Write-Host "=== Stack ready ==="
Write-Host "Start backend:  .\venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"
Write-Host "Start frontend: npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173"
Write-Host ""
Write-Host "Smoke test (after backend is running):"
Write-Host '  $env:SMOKE_API_PASSWORD="your-bootstrap-password"'
Write-Host "  .\venv\Scripts\python.exe scripts\smoke_api.py"
Write-Host '  Remove-Item Env:SMOKE_API_PASSWORD'
