# Runs the full local verification suite documented in docs/EVALUATION.md.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Invoke-Step {
    param([string]$Label, [scriptblock]$Action)
    Write-Host "`n=== $Label ===" -ForegroundColor Cyan
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }
}

Invoke-Step "Backend pytest (non-integration)" {
    .\venv\Scripts\python.exe -m pytest tests -m "not integration" -q
}

Invoke-Step "Holdout evaluation" {
    .\venv\Scripts\python.exe scripts\evaluate_holdouts.py
}

Invoke-Step "Answer comparison" {
    .\venv\Scripts\python.exe scripts\evaluate_answer_comparison.py
}

Invoke-Step "Live verification" {
    .\venv\Scripts\python.exe scripts\evaluate_live_verified_generation.py
}

Invoke-Step "Mixed holdout 120" {
    .\venv\Scripts\python.exe scripts\evaluate_mixed_holdout.py
}

Invoke-Step "Ablations" {
    .\venv\Scripts\python.exe scripts\evaluate_ablations.py
}

Invoke-Step "Role comparison" {
    .\venv\Scripts\python.exe scripts\evaluate_role_comparison.py
}

Invoke-Step "Frontend lint" {
    npm --prefix frontend run lint
}

Invoke-Step "Frontend unit tests" {
    npm --prefix frontend run test
}

Invoke-Step "Frontend e2e (skipped unless PLAYWRIGHT_RUN_E2E=1)" {
    npm --prefix frontend run test:e2e
}

Write-Host "`nAll local verification steps passed." -ForegroundColor Green
