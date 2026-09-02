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
    Write-Host "=== Validating render.yaml ==="
    $yamlPath = Join-Path $Root "render.yaml"
    $validate = curl.exe -s -X POST "https://api.render.com/v1/blueprints/validate" `
        -H "Authorization: Bearer $RenderApiKey" `
        -F "ownerId=$ownerId" `
        -F "file=@$yamlPath" | ConvertFrom-Json
    if (-not $validate.valid) {
        $payment = @($validate.errors | Where-Object { $_.error -eq "need_payment_info" })
        if ($payment.Count -gt 0) {
            Write-Host "Render requires a payment method for the plans in render.yaml (Postgres + starter services)."
            Write-Host "Add one at: https://dashboard.render.com/billing"
            Write-Host ""
        }
        Write-Host ($validate | ConvertTo-Json -Depth 6)
        throw "render.yaml validation failed. Fix errors above, then create the Blueprint in the dashboard."
    }
    Write-Host "render.yaml is valid."

    Write-Host ""
    Write-Host "=== Create Blueprint in Render Dashboard (required; no create API) ==="
    Write-Host "1. https://dashboard.render.com/blueprints -> New Blueprint Instance"
    Write-Host "2. Repo: $Repo  branch: $Branch"
    Write-Host "3. Secrets when prompted:"
    Write-Host "     JWT_SECRET"
    Write-Host "     BOOTSTRAP_USER_PASSWORD"
    Write-Host "     GEMINI_API_KEY"
    Write-Host ""
    Write-Host "Waiting for knowledge-base-api service (poll up to 30 min)..."
    $deadline = (Get-Date).AddMinutes(30)
    while ((Get-Date) -lt $deadline) {
        $services = Invoke-RestMethod -Uri "https://api.render.com/v1/services?limit=50" -Headers $headers
        $existing = $services | Where-Object { $_.service.name -eq "knowledge-base-api" } | Select-Object -First 1
        if ($existing) { break }
        Start-Sleep -Seconds 30
    }
    if (-not $existing) {
        throw "API service not found yet. Finish Blueprint setup in the dashboard, then re-run this script."
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
    Write-Host "First boot runs DB migrate and ingest (5-10 minutes on free tier). Check Render logs."
