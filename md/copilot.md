Hier is een volledig overzicht van alles wat je nodig hebt:

---

## Wat draait er al ✅

**MCP Server** (`graph-mcp-server.azurewebsites.net`)
- Exposeert Microsoft Graph tools via FastMCP
- Ontvangt Bearer token en voert Graph calls uit

**Bot Server** (`graph-bot-server.azurewebsites.net`)
- Ontvangt berichten van Teams/Copilot
- Roept de agent aan met het user token
- Stuurt antwoord terug

**Azure Bot** (`graph-bot-v1`)
- Verbindt Teams/Copilot met de bot server
- Messaging endpoint correct ingesteld
- OAuth Connection `graph-connection` aangemaakt

**App Registration** (`5b6e8b68-088c-469b-8d96-f1416e57d3e9`)
- Alle Graph permissies correct
- `api://...` scope aangemaakt

---

## Wat nog moet gebeuren ❌

**1. Teams app manifest uploaden**
- `manifest.zip` maken (klaar om te doen)
- Uploaden via Teams — **IT admin nodig** voor tenant-wide deployment, of jij kan het zelf sideloaden als developer

**2. OBO flow testen in Teams**
- Eerste keer inloggen via sign-in card
- Daarna automatisch token via SSO

**3. Optioneel later: Copilot extensie**
- Vereist Copilot M365 licentie
- Manifest aanpassen met `copilotExtensions` sectie

---

## Samenvatting voor IT admin

Wat jij aan de IT admin moet vragen:
1. **Sideloading toestaan** in Teams Admin Center (of de `manifest.zip` voor jou uploaden)
2. **Admin consent geven** voor de Graph permissies op de app registration

Dat is alles — de rest staat klaar.



```bash
# ============================================================
# Graph Agent - Volledig Deployment Script
# Vul alle variabelen in onder "CONFIGURATIE" in voor gebruik
# ============================================================

# ============================================================
# CONFIGURATIE - pas deze waarden aan
# ============================================================

# Azure
$SUBSCRIPTION_ID         = "<jouw-subscription-id>"
$RESOURCE_GROUP          = "rg-graph-mcp"
$LOCATION                = "norwayeast"  # of "westeurope", "eastus", etc.

# Container Registry
$ACR_NAME                = "<jouw-acr-naam>"  # bijv. "graphmcpregistry"

# App Service
$APP_SERVICE_PLAN        = "plan-graph-mcp"
$MCP_APP_NAME            = "graph-mcp-server"
$BOT_APP_NAME            = "graph-bot-server"

# Azure Bot
$BOT_NAME                = "graph-bot-v1"
$BOT_RESOURCE_GROUP      = "graph-agent-test"  # mag zelfde zijn als RESOURCE_GROUP

# App Registration (Entra ID)
$APP_ID                  = "<jouw-app-registration-client-id>"
$APP_SECRET              = "<jouw-app-registration-client-secret>"
$TENANT_ID               = "<jouw-tenant-id>"

# Azure OpenAI
$OPENAI_ENDPOINT         = "<jouw-azure-openai-endpoint>"
$OPENAI_API_KEY          = "<jouw-azure-openai-api-key>"
$OPENAI_DEPLOYMENT       = "<jouw-deployment-naam>"  # bijv. "gpt-4o-mini"

# Graph scopes
$GRAPH_SCOPES            = "https://graph.microsoft.com/User.Read https://graph.microsoft.com/Mail.Read https://graph.microsoft.com/Calendars.Read https://graph.microsoft.com/Contacts.Read https://graph.microsoft.com/Files.Read https://graph.microsoft.com/Chat.Read"

# OAuth connection naam (moet overeenkomen met wat je in Azure Bot hebt ingesteld)
$OAUTH_CONNECTION_NAME   = "graph-connection"

# ============================================================
# STAP 1 - Inloggen op Azure
# ============================================================
Write-Host "`n[1/8] Inloggen op Azure..." -ForegroundColor Cyan
az login
az account set --subscription $SUBSCRIPTION_ID

# ============================================================
# STAP 2 - Resource Group aanmaken
# ============================================================
Write-Host "`n[2/8] Resource groups aanmaken..." -ForegroundColor Cyan
az group create --name $RESOURCE_GROUP --location $LOCATION
az group create --name $BOT_RESOURCE_GROUP --location $LOCATION

# ============================================================
# STAP 3 - Container Registry aanmaken
# ============================================================
Write-Host "`n[3/8] Container Registry aanmaken..." -ForegroundColor Cyan
az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku Basic --admin-enabled true
az acr login --name $ACR_NAME

# ============================================================
# STAP 4 - App Service Plan aanmaken
# ============================================================
Write-Host "`n[4/8] App Service Plan aanmaken..." -ForegroundColor Cyan
az appservice plan create `
  --name $APP_SERVICE_PLAN `
  --resource-group $RESOURCE_GROUP `
  --is-linux `
  --sku B1

# ============================================================
# STAP 5 - Docker images builden en pushen
# ============================================================
Write-Host "`n[5/8] Docker images builden en pushen..." -ForegroundColor Cyan

# MCP server
docker build -f Dockerfile -t "$ACR_NAME.azurecr.io/graph-mcp-server:latest" .
docker push "$ACR_NAME.azurecr.io/graph-mcp-server:latest"

# Bot server
docker build -f Dockerfile.bot -t "$ACR_NAME.azurecr.io/graph-bot-server:latest" .
docker push "$ACR_NAME.azurecr.io/graph-bot-server:latest"

# ============================================================
# STAP 6 - Web Apps aanmaken
# ============================================================
Write-Host "`n[6/8] Web Apps aanmaken..." -ForegroundColor Cyan

$ACR_PASSWORD = az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv

# MCP server web app
az webapp create `
  --resource-group $RESOURCE_GROUP `
  --plan $APP_SERVICE_PLAN `
  --name $MCP_APP_NAME `
  --deployment-container-image-name "$ACR_NAME.azurecr.io/graph-mcp-server:latest"

az webapp config appsettings set `
  --resource-group $RESOURCE_GROUP `
  --name $MCP_APP_NAME `
  --settings `
    WEBSITES_PORT="8000" `
    MCP_RESOURCE_URI="https://$MCP_APP_NAME.azurewebsites.net" `
    DOCKER_REGISTRY_SERVER_URL="https://$ACR_NAME.azurecr.io" `
    DOCKER_REGISTRY_SERVER_USERNAME="$ACR_NAME" `
    DOCKER_REGISTRY_SERVER_PASSWORD="$ACR_PASSWORD"

# Bot server web app
az webapp create `
  --resource-group $RESOURCE_GROUP `
  --plan $APP_SERVICE_PLAN `
  --name $BOT_APP_NAME `
  --deployment-container-image-name "$ACR_NAME.azurecr.io/graph-bot-server:latest"

az webapp config appsettings set `
  --resource-group $RESOURCE_GROUP `
  --name $BOT_APP_NAME `
  --settings `
    WEBSITES_PORT="3978" `
    MicrosoftAppId="$APP_ID" `
    MicrosoftAppPassword="$APP_SECRET" `
    MicrosoftAppTenantId="$TENANT_ID" `
    MicrosoftAppType="SingleTenant" `
    MCP_SERVER_URL="https://$MCP_APP_NAME.azurewebsites.net/mcp" `
    GRAPH_SCOPES="$GRAPH_SCOPES" `
    OAUTH_CONNECTION_NAME="$OAUTH_CONNECTION_NAME" `
    AZURE_OPENAI_ENDPOINT="$OPENAI_ENDPOINT" `
    AZURE_OPENAI_API_KEY="$OPENAI_API_KEY" `
    deployment="$OPENAI_DEPLOYMENT" `
    "AGENTAPPLICATION__USERAUTHORIZATION__HANDLERS__GRAPH__SETTINGS__AZUREBOTOAUTHCONNECTIONNAME=$OAUTH_CONNECTION_NAME" `
    "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID=$APP_ID" `
    "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET=$APP_SECRET" `
    "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID=$TENANT_ID" `
    "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__AUTHTYPE=ClientSecret" `
    DOCKER_REGISTRY_SERVER_URL="https://$ACR_NAME.azurecr.io" `
    DOCKER_REGISTRY_SERVER_USERNAME="$ACR_NAME" `
    DOCKER_REGISTRY_SERVER_PASSWORD="$ACR_PASSWORD"

# ============================================================
# STAP 7 - Azure Bot aanmaken en configureren
# ============================================================
Write-Host "`n[7/8] Azure Bot aanmaken..." -ForegroundColor Cyan
az bot create `
  --resource-group $BOT_RESOURCE_GROUP `
  --name $BOT_NAME `
  --kind registration `
  --msa-app-id $APP_ID `
  --endpoint "https://$BOT_APP_NAME.azurewebsites.net/api/messages"

Write-Host "`nAzure Bot aangemaakt. Ga nu handmatig naar Azure Portal en voeg OAuth Connection toe:" -ForegroundColor Yellow
Write-Host "  Azure Bot -> Settings -> Configuration -> Add OAuth Connection Settings" -ForegroundColor Yellow
Write-Host "  Name:          $OAUTH_CONNECTION_NAME" -ForegroundColor Yellow
Write-Host "  Provider:      Azure Active Directory v2" -ForegroundColor Yellow
Write-Host "  Client ID:     $APP_ID" -ForegroundColor Yellow
Write-Host "  Client Secret: $APP_SECRET" -ForegroundColor Yellow
Write-Host "  Tenant ID:     $TENANT_ID" -ForegroundColor Yellow
Write-Host "  Scopes:        User.Read Mail.Read Calendars.Read Contacts.Read Files.Read Chat.Read" -ForegroundColor Yellow

# ============================================================
# STAP 8 - Teams manifest aanmaken
# ============================================================
Write-Host "`n[8/8] Teams manifest aanmaken..." -ForegroundColor Cyan

New-Item -ItemType Directory -Force -Path manifest | Out-Null

$manifest = @"
{
  "`$schema": "https://developer.microsoft.com/en-us/json-schemas/teams/v1.17/MicrosoftTeams.schema.json",
  "manifestVersion": "1.17",
  "version": "1.0.0",
  "id": "$APP_ID",
  "packageName": "com.graphagent.bot",
  "developer": {
    "name": "Graph Agent",
    "websiteUrl": "https://$BOT_APP_NAME.azurewebsites.net",
    "privacyUrl": "https://$BOT_APP_NAME.azurewebsites.net",
    "termsOfUseUrl": "https://$BOT_APP_NAME.azurewebsites.net"
  },
  "name": {
    "short": "Graph Agent",
    "full": "Graph Agent - Microsoft 365"
  },
  "description": {
    "short": "Graph Agent voor Microsoft 365",
    "full": "Een agent die je emails, agenda, contacten en bestanden kan opvragen via Microsoft Graph."
  },
  "icons": {
    "color": "color.png",
    "outline": "outline.png"
  },
  "accentColor": "#0078D4",
  "bots": [
    {
      "botId": "$APP_ID",
      "scopes": ["personal", "team", "groupchat"],
      "isNotificationOnly": false,
      "supportsCalling": false,
      "supportsVideo": false,
      "supportsFiles": false
    }
  ],
  "permissions": ["identity", "messageTeamMembers"],
  "validDomains": [
    "$BOT_APP_NAME.azurewebsites.net",
    "token.botframework.com"
  ],
  "webApplicationInfo": {
    "id": "$APP_ID",
    "resource": "api://$APP_ID"
  }
}
"@

$manifest | Out-File -FilePath "manifest/manifest.json" -Encoding utf8

# Maak placeholder icons
Add-Type -AssemblyName System.Drawing
$bmp = New-Object System.Drawing.Bitmap 192,192
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.Clear([System.Drawing.Color]::FromArgb(0,120,212))
$bmp.Save("manifest/color.png")
$bmp2 = New-Object System.Drawing.Bitmap 32,32
$g2 = [System.Drawing.Graphics]::FromImage($bmp2)
$g2.Clear([System.Drawing.Color]::FromArgb(0,120,212))
$bmp2.Save("manifest/outline.png")

Compress-Archive -Path manifest/* -DestinationPath manifest.zip -Force

# ============================================================
# KLAAR
# ============================================================
Write-Host "`n============================================================" -ForegroundColor Green
Write-Host " Deployment voltooid!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host " MCP Server:  https://$MCP_APP_NAME.azurewebsites.net" -ForegroundColor Green
Write-Host " Bot Server:  https://$BOT_APP_NAME.azurewebsites.net" -ForegroundColor Green
Write-Host " manifest.zip klaar voor upload in Teams" -ForegroundColor Green
Write-Host "============================================================`n" -ForegroundColor Green
Write-Host "VOLGENDE STAPPEN:" -ForegroundColor Yellow
Write-Host " 1. Voeg OAuth Connection toe in Azure Portal (zie boven)" -ForegroundColor Yellow
Write-Host " 2. Upload manifest.zip via Teams -> Apps -> Upload an app" -ForegroundColor Yellow
Write-Host " 3. Test de bot in Teams" -ForegroundColor Yellow
```