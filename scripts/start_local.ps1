# Everyday start: Docker + API + UI (Windows). Called by start.bat

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Trust-RAG — START"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path ".\venv\Scripts\python.exe")) {
    Write-Host "ERROR: venv missing. Run setup.bat first." -ForegroundColor Red
    exit 1
}
if (-not (Test-Path ".\.env")) {
    Write-Host "ERROR: .env missing. Run setup.bat first." -ForegroundColor Red
    exit 1
}

docker info 1>$null 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker is not running. Start Docker Desktop, then re-run start.bat" -ForegroundColor Red
    exit 1
}

$env:LOCAL_STACK = "1"
if (-not $env:POSTGRES_PORT) { $env:POSTGRES_PORT = "5432" }
$portProbe = Test-NetConnection -ComputerName 127.0.0.1 -Port $env:POSTGRES_PORT -WarningAction SilentlyContinue
if ($portProbe.TcpTestSucceeded -and $env:POSTGRES_PORT -eq "5432") {
    Write-Host "Port 5432 in use — using 5433 for Postgres."
    $env:POSTGRES_PORT = "5433"
}

Write-Host "=== Starting Postgres + Qdrant ==="
docker compose up -d

# Read password for the tip line
$demoPassword = "(see BOOTSTRAP_USER_PASSWORD in .env)"
$match = Select-String -Path .env -Pattern "^BOOTSTRAP_USER_PASSWORD=(.+)$" | Select-Object -First 1
if ($match) { $demoPassword = $match.Matches.Groups[1].Value.Trim() }

$pg = $env:POSTGRES_PORT
$backendCmd = @"
cd /d `"$Root`"
set LOCAL_STACK=1
set POSTGRES_PORT=$pg
title Trust-RAG Backend
echo Backend starting on http://127.0.0.1:8000 ...
.\venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
pause
"@

$frontendCmd = @"
cd /d `"$Root`"
title Trust-RAG Frontend
echo Frontend starting on http://127.0.0.1:5173 ...
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173
pause
"@

Write-Host "=== Opening Backend window ==="
Start-Process cmd.exe -ArgumentList "/k", $backendCmd

Start-Sleep -Seconds 2

Write-Host "=== Opening Frontend window ==="
Start-Process cmd.exe -ArgumentList "/k", $frontendCmd

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Two windows were opened (Backend + UI)"
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Wait ~15–30 seconds for models to load, then open:"
Write-Host "  http://127.0.0.1:5173"
Write-Host ""
Write-Host "Login:  harshini@company.com"
Write-Host "Pass:   $demoPassword"
Write-Host ""
Write-Host "To stop later: double-click stop.bat"
Write-Host ""
