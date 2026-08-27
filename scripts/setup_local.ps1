# First-time local setup (Windows). Called by setup.bat
# Creates venv, installs deps, writes .env, Docker + ingest.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Trust-RAG — first-time SETUP"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

function Require-Cmd($name) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        Write-Host "ERROR: '$name' not found on PATH." -ForegroundColor Red
        Write-Host "Install it, then re-run setup.bat"
        exit 1
    }
}

Require-Cmd python
Require-Cmd npm
Require-Cmd docker

Write-Host "Checking Docker is running..."
docker info 1>$null 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker is not running. Start Docker Desktop and re-run setup.bat" -ForegroundColor Red
    exit 1
}

# --- Python venv ---
if (-not (Test-Path ".\venv\Scripts\python.exe")) {
    Write-Host "=== Creating Python venv ==="
    python -m venv venv
}

$py = ".\venv\Scripts\python.exe"
Write-Host "=== Installing PyTorch (CPU) ==="
& $py -m pip install --upgrade pip
& $py -m pip install torch==2.12.0 --index-url https://download.pytorch.org/whl/cpu
Write-Host "=== Installing Python requirements ==="
& $py -m pip install -r requirements.txt

# --- .env ---
$demoPassword = "TrustDemo2026"
if (-not (Test-Path ".\.env")) {
    Write-Host "=== Creating .env from .env.example ==="
    Copy-Item .env.example .env
    $envText = Get-Content .env -Raw
    $envText = $envText -replace "BOOTSTRAP_USER_PASSWORD=choose-an-initial-user-password", "BOOTSTRAP_USER_PASSWORD=$demoPassword"
    # Ensure JWT is long enough if someone truncated the example
    if ($envText -notmatch "JWT_SECRET=.{32,}") {
        $envText = $envText -replace "JWT_SECRET=.*", "JWT_SECRET=ekip-dev-secret-change-in-prod-ok"
    }
    Set-Content -Path .env -Value $envText -NoNewline
    Write-Host "Demo login password set to: $demoPassword" -ForegroundColor Green
} else {
    Write-Host "=== .env already exists (left unchanged) ==="
    $match = Select-String -Path .env -Pattern "^BOOTSTRAP_USER_PASSWORD=(.+)$" | Select-Object -First 1
    if ($match) { $demoPassword = $match.Matches.Groups[1].Value.Trim() }
}

# --- Frontend ---
Write-Host "=== Installing frontend npm packages ==="
npm --prefix frontend install

# --- Data stack ---
Write-Host "=== Docker + database + ingest (this can take several minutes) ==="
$env:LOCAL_STACK = "1"
$env:BOOTSTRAP_USER_PASSWORD = $demoPassword
& "$Root\scripts\run_local_trust_stack.ps1"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  SETUP COMPLETE"
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next: double-click  start.bat  (or run .\start.bat)"
Write-Host ""
Write-Host "Then open  http://127.0.0.1:5173"
Write-Host "Login email examples:"
Write-Host "  harshini@company.com   (Engineer)"
Write-Host "  bhaskar@company.com    (Admin)"
Write-Host "  amrutha@company.com    (HR)"
Write-Host "Password:  $demoPassword"
Write-Host ""
Write-Host "You only need setup.bat once (or after pulling big dependency changes)."
Write-Host ""
