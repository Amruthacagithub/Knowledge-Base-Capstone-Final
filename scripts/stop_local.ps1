# Stop local Trust-RAG processes and Docker services (Windows).

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "=== Stopping frontend/backend windows (by title) ==="
Get-Process cmd -ErrorAction SilentlyContinue | Where-Object {
    $_.MainWindowTitle -match "Trust-RAG Backend|Trust-RAG Frontend"
} | Stop-Process -Force -ErrorAction SilentlyContinue

# Also free ports if orphaned python/node remain
foreach ($port in 8000, 5173) {
    $lines = netstat -ano | Select-String ":$port\s+.*LISTENING"
    foreach ($line in $lines) {
        if ($line -match "\s+(\d+)\s*$") {
            $procId = [int]$Matches[1]
            Write-Host "Stopping PID $procId on port $port"
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        }
    }
}

Write-Host "=== Stopping Docker services ==="
docker compose stop

Write-Host ""
Write-Host "Stopped. Run start.bat when you want to use the app again."
Write-Host ""
