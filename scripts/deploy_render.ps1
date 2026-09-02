# Deploy full stack to Render via Blueprint API, then point Vercel at the API URL.
param(
    [string]$RenderApiKey = $env:RENDER_API_KEY,
    [string]$Repo = "https://github.com/Harshinireddy05/Knowledge-Base-Capstone-Final",
    [string]$Branch = "main",
    [string]$VercelUrl = "https://knowledge-base-trust-rag.vercel.app"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Get-DotEnvValue([string]$Key) {
    $line = Select-String -Path ".env" -Pattern "^$Key=(.*)$" | Select-Object -First 1
    if ($line) { return $line.Matches.Groups[1].Value.Trim() }
    return ""
}

if (-not $RenderApiKey) { $RenderApiKey = Get-DotEnvValue "RENDER_API_KEY" }
if (-not $RenderApiKey) {
    throw @"
RENDER_API_KEY is required.
1. Open https://dashboard.render.com/u/settings#api-keys
2. Create API key
3. Add to .env:  RENDER_API_KEY=rnd_...
   Or run:  `$env:RENDER_API_KEY='rnd_...'; .\scripts\deploy_render.ps1
"@
}

$jwt = Get-DotEnvValue "JWT_SECRET"
$bootstrap = Get-DotEnvValue "BOOTSTRAP_USER_PASSWORD"
$gemini = Get-DotEnvValue "GEMINI_API_KEY"
if (-not $jwt -or -not $bootstrap -or -not $gemini) {
    throw "JWT_SECRET, BOOTSTRAP_USER_PASSWORD, and GEMINI_API_KEY must be in .env"
}

$headers = @{
    Authorization = "Bearer $RenderApiKey"
    Accept        = "application/json"
    "Content-Type" = "application/json"
}

Write-Host "=== Render owner workspaces ==="
$owners = Invoke-RestMethod -Uri "https://api.render.com/v1/owners?limit=20" -Headers $headers
$owner = $owners[0].owner
if (-not $owner) { throw "No Render workspace found for this API key" }
$ownerId = $owner.id
Write-Host "Using owner: $($owner.name) ($ownerId)"

Write-Host "=== Checking for existing blueprint / services ==="
$services = Invoke-RestMethod -Uri "https://api.render.com/v1/services?limit=50" -Headers $headers
$existing = $services | Where-Object { $_.service.name -eq "knowledge-base-api" } | Select-Object -First 1
if ($existing) {
    $apiUrl = "https://$($existing.service.serviceDetails.url)"
    Write-Host "Service already exists: $apiUrl"
} else {
    Write-Host "=== Creating Blueprint from GitHub repo ==="
    Write-Host "NOTE: render.yaml + Dockerfile must be on branch $Branch of $Repo"
    $spec = Get-Content -Raw -Path (Join-Path $Root "render.yaml")
    $body = @{
        name     = "knowledge-base-trust-rag"
        ownerId  = $ownerId
        repo     = $Repo
        branch   = $Branch
        autoSync = $true
        envVars  = @(
            @{ key = "JWT_SECRET"; value = $jwt }
            @{ key = "BOOTSTRAP_USER_PASSWORD"; value = $bootstrap }
            @{ key = "GEMINI_API_KEY"; value = $gemini }
        )
    } | ConvertTo-Json -Depth 6

    try {
        $bp = Invoke-RestMethod -Method POST -Uri "https://api.render.com/v1/blueprints" -Headers $headers -Body $body
        Write-Host "Blueprint created: $($bp.id)"
        Write-Host "Watch deploy: https://dashboard.render.com"
        Start-Sleep -Seconds 30
    } catch {
        $err = $_.ErrorDetails.Message
        Write-Host "Blueprint API response: $err"
        Write-Host ""
        Write-Host "=== Manual fallback (5 minutes) ==="
        Write-Host "1. Push render.yaml + Dockerfile to GitHub main"
        Write-Host "2. https://dashboard.render.com/blueprints -> New Blueprint Instance"
        Write-Host "3. Connect repo: $Repo"
        Write-Host "4. Set secrets: JWT_SECRET, BOOTSTRAP_USER_PASSWORD, GEMINI_API_KEY"
        throw $_
    }

    $services = Invoke-RestMethod -Uri "https://api.render.com/v1/services?limit=50" -Headers $headers
    $existing = $services | Where-Object { $_.service.name -eq "knowledge-base-api" } | Select-Object -First 1
    if (-not $existing) {
        throw "API service not visible yet. Check Render dashboard — first deploy can take 10-15 minutes."
    }
    $apiUrl = "https://$($existing.service.serviceDetails.url)"
}

Write-Host "=== API URL: $apiUrl ==="

Write-Host "=== Updating Vercel VITE_API_URL ==="
$vercelHeaders = @{ Authorization = "Bearer $(vercel whoami 2>$null)" }
echo $apiUrl | vercel env rm VITE_API_URL production --yes 2>$null
echo $apiUrl | vercel env add VITE_API_URL production
vercel deploy --prod --yes | Out-Null

Write-Host ""
Write-Host "Done."
Write-Host "  Frontend: $VercelUrl"
Write-Host "  Backend:  $apiUrl"
Write-Host "  Health:   $apiUrl/api/health"
Write-Host "First boot runs DB migrate + ingest (10-20 min). Check Render logs."
