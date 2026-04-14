# # Alles deployen
# .\deploy.ps1

# # Alleen graph-mcp
# .\deploy.ps1 -Services graph

# # Alleen orchestrator
# .\deploy.ps1 -Services orchestrator

# # Graph + orchestrator samen
# .\deploy.ps1 -Services graph, orchestrator

# # Alleen salesforce
# .\deploy.ps1 -Services salesforce

param(
    [ValidateSet("all", "graph", "orchestrator", "smartsales", "salesforce")]
    [string[]]$Services = @("all"),

    [string]$ACR = "graphxmafacr2",
    [string]$RG = "Global-Search-Agent"
)


$TAG = (Get-Date -Format "yyyyMMdd-HHmm")
$ACR_URL = "$ACR.azurecr.io"

Write-Host ""
Write-Host "=== Deploy tag: $TAG ===" -ForegroundColor Cyan
Write-Host "=== Resource group: $RG ===" -ForegroundColor Cyan
Write-Host ""

# ── Service definitions ──────────────────────────────────────────────────────
$all = @{
    graph = @{
        dockerfile = "Dockerfile.graph"
        image      = "$ACR_URL/graph-mcp"
        app        = "graph-mcp"
    }
    orchestrator = @{
        dockerfile = "Dockerfile.orchestrator"
        image      = "$ACR_URL/orchestrator-mcp"
        app        = "orchestrator-mcp"
    }
    smartsales = @{
        dockerfile = "Dockerfile.smartsales"
        image      = "$ACR_URL/smartsales-mcp"
        app        = "smartsales-mcp"
    }
    salesforce = @{
        dockerfile = "Dockerfile.salesforce"
        image      = "$ACR_URL/salesforce-mcp"
        app        = "salesforce-mcp"
    }
}

# ── Resolve which services to deploy ─────────────────────────────────────────
if ($Services -contains "all") {
    $targets = $all.Keys
} else {
    $targets = $Services
}

# ── ACR login ────────────────────────────────────────────────────────────────
Write-Host "Logging into ACR..." -ForegroundColor Yellow
az acr login --name $ACR
if ($LASTEXITCODE -ne 0) {
    Write-Error "ACR login failed. Run 'az login' first?"
    exit 1
}

# ── Build, push, deploy ─────────────────────────────────────────────────────
foreach ($svc in $targets) {
    if (-not $all.ContainsKey($svc)) {
        Write-Warning "Unknown service: $svc - skipping"
        continue
    }

    $cfg = $all[$svc]
    $fullImage = "$($cfg.image):$TAG"

    Write-Host ""
    Write-Host "-- $svc ----------------------------------" -ForegroundColor Green

    # Build
    Write-Host "Building $fullImage ..." -ForegroundColor Yellow
    docker build -f $cfg.dockerfile -t $fullImage .
    if ($LASTEXITCODE -ne 0) { Write-Error "Build failed for $svc"; continue }

    # Push
    Write-Host "Pushing ..." -ForegroundColor Yellow
    docker push $fullImage
    if ($LASTEXITCODE -ne 0) { Write-Error "Push failed for $svc"; continue }

    # Deploy
    Write-Host "Updating container app $($cfg.app) ..." -ForegroundColor Yellow
    az containerapp update --name $cfg.app --resource-group $RG --image $fullImage
    if ($LASTEXITCODE -ne 0) { Write-Error "Deploy failed for $svc"; continue }

    # Health check — verify the new revision is ready
    Start-Sleep -Seconds 5
    $rev = az containerapp show --name $cfg.app --resource-group $RG --query "properties.latestRevisionName" -o tsv
    $ready = az containerapp show --name $cfg.app --resource-group $RG --query "properties.latestReadyRevisionName" -o tsv
    if ($rev -ne $ready) {
        Write-Warning "${svc}: revision $rev is NOT ready (latest ready: $ready) - container may be crashing"
    } else {
        Write-Host "$svc deployed successfully! (revision: $rev)" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "=== Done! ===" -ForegroundColor Cyan