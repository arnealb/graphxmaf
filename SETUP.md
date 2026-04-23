# Setup Guide: Multi-Agent Copilot System

This guide explains how to recreate this multi-agent system from scratch — Azure infrastructure, container deployment, and the Microsoft 365 Copilot declarative agent.

---

## Architecture Overview

```
Microsoft 365 Copilot
        │
        │ OAuth (Authorization Code + OBO)
        ▼
┌─────────────────────────────────────────────┐
│  Orchestrator MCP Server  (port 8003)        │
│  • Exposes single `ask` tool to Copilot      │
│  • OBO exchange: Copilot token → Graph token │
│  • PlanningOrchestrator:                     │
│      1. Planner  → JSON execution plan       │
│      2. DAG execute → parallel sub-agents    │
│      3. Synthesizer → final answer           │
└──────────┬──────────┬──────────┬─────────────┘
           │          │          │
           ▼          ▼          ▼
    Graph MCP    Salesforce   SmartSales
    (port 8000)  MCP (8001)   MCP (8002)
    MS Graph     Salesforce   SmartSales
    API          REST API     REST API
```

All four MCP servers run as **Azure Container Apps** in the same environment.
The local `main.py` starts only the sub-agents in devui for individual testing.

---

## Prerequisites

- Azure subscription with Container Apps enabled
- Microsoft 365 tenant with Copilot license
- Azure CLI (`az`) installed and logged in
- Docker installed (for building images)
- Python 3.12
- Node.js 18+ (for M365 Agents Toolkit)
- VS Code with [Microsoft 365 Agents Toolkit](https://aka.ms/teams-toolkit) extension

---

## 1. Azure App Registrations

You need **three** App Registrations in Azure AD (Entra ID).

### 1.1 Graph MCP — `graph-mcp`

This registration backs the Graph MCP server. Copilot does NOT talk to it directly — only the orchestrator does via OBO.

1. Portal → **Microsoft Entra ID → App registrations → New registration**
2. Name: `graph-mcp`
3. Supported account types: **Single tenant**
4. Redirect URI: `http://localhost:5001` (Web) — only needed for local dev
5. After creation:
   - **Expose an API → Set Application ID URI**: `api://<client-id>`
   - Add scope: `access_as_user` (Admins and users can consent)
   - Add a **client secret** (Certificates & secrets → New client secret)
6. **API Permissions** (for local dev auth flow — Graph delegated):
   - `User.Read`, `User.Read.All`, `Mail.Read`, `Calendars.Read`,
     `Contacts.Read`, `Files.Read.All`, `People.Read`
   - Grant admin consent

**Note these values:**
```
clientId     = <graph-mcp application (client) ID>
tenantId     = <your tenant ID>
clientSecret = <the secret value you created>
```

### 1.2 Orchestrator MCP — `orchestrator-mcp`

This registration is what Copilot authenticates against. Copilot gets a token scoped to this app, and the orchestrator exchanges it for a Graph token via OBO.

1. New registration: name `orchestrator-mcp`
2. Supported account types: **Single tenant**
3. After creation:
   - **Expose an API → Set Application ID URI**: `api://<orchestrator-client-id>`
   - Add scope: `access_as_user`
   - Add a **client secret**
4. **API Permissions**:
   - Microsoft Graph → Delegated: `User.Read`, `User.Read.All`, `Mail.Read`, `Calendars.Read`, `Contacts.Read`, `Files.Read.All`, `People.Read`
   - Grant admin consent
5. **Add the Graph MCP app as a pre-authorized application** (optional, but allows seamless OBO without user consent prompt):
   - Expose an API → Authorized client applications → Add the `graph-mcp` client ID

**Note these values:**
```
clientId     = <orchestrator application (client) ID>
clientSecret = <the secret value>
```

### 1.3 Salesforce MCP — `salesforce-mcp`

1. New registration: name `salesforce-mcp`
2. Redirect URI: `http://localhost:8001/auth/salesforce/callback` (Web)
3. Expose an API → scope `access_as_user`
4. Add a client secret

---

## 2. Salesforce Connected App

1. Salesforce Setup → **App Manager → New Connected App**
2. Enable OAuth Settings:
   - Callback URL: `https://salesforce-mcp.<env>.azurecontainerapps.io/auth/salesforce/callback`
   - Scopes: `api`, `refresh_token`, `offline_access`
3. Note: Consumer Key → `SF_CLIENT_ID`, Consumer Secret → `SF_CLIENT_SECRET`

---

## 3. SmartSales Credentials

SmartSales uses a client-credentials OAuth flow (no browser). You need:

```
GRANT_TYPE             = client_credentials
CLIENT_ID_SMARTSALES   = <smartsales client id>
CLIENT_SECRET_SMARTSALES = <smartsales client secret>
CODE_SMARTSALES        = <smartsales code/scope>
```

---

## 4. Azure Container Apps Environment

```bash
# Variables — adjust to your names
RESOURCE_GROUP=rg-multiagent
LOCATION=swedencentral
ENV_NAME=multiagent-env
REGISTRY_NAME=multiagentacr   # must be globally unique

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create Azure Container Registry
az acr create --resource-group $RESOURCE_GROUP \
    --name $REGISTRY_NAME --sku Basic

# Create Container Apps Environment
az containerapp env create \
    --name $ENV_NAME \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION
```

---

## 5. Build and Push Docker Images

From the `graphxmaf/` root directory:

```bash
# Log in to ACR
az acr login --name $REGISTRY_NAME

ACR=$REGISTRY_NAME.azurecr.io

# Build and push all four images
docker build -f Dockerfile.graph      -t $ACR/graph-mcp:latest      .
docker build -f Dockerfile.salesforce -t $ACR/salesforce-mcp:latest  .
docker build -f Dockerfile.smartsales -t $ACR/smartsales-mcp:latest  .
docker build -f Dockerfile.orchestrator -t $ACR/orchestrator-mcp:latest .

docker push $ACR/graph-mcp:latest
docker push $ACR/salesforce-mcp:latest
docker push $ACR/smartsales-mcp:latest
docker push $ACR/orchestrator-mcp:latest
```

---

## 6. Deploy Container Apps

### 6.1 Graph MCP

```bash
az containerapp create \
  --name graph-mcp \
  --resource-group $RESOURCE_GROUP \
  --environment $ENV_NAME \
  --image $ACR/graph-mcp:latest \
  --registry-server $ACR \
  --ingress external --target-port 8000 \
  --env-vars \
    MCP_RESOURCE_URI=https://graph-mcp.<unique-env>.azurecontainerapps.io \
    AZURE_OPENAI_ENDPOINT=<your-aoai-endpoint> \
    AZURE_OPENAI_API_KEY=secretref:aoai-key \
    deployment=<your-gpt4o-deployment-name>
```

Set secrets separately:
```bash
az containerapp secret set \
  --name graph-mcp --resource-group $RESOURCE_GROUP \
  --secrets aoai-key=<your-openai-key>
```

**After deploy**, note the URL: `https://graph-mcp.<env>.azurecontainerapps.io`
Update `config.cfg` → `[azure]` → `mcpServerUrl`.

### 6.2 Salesforce MCP

```bash
az containerapp create \
  --name salesforce-mcp \
  --resource-group $RESOURCE_GROUP \
  --environment $ENV_NAME \
  --image $ACR/salesforce-mcp:latest \
  --registry-server $ACR \
  --ingress external --target-port 8001 \
  --env-vars \
    MCP_RESOURCE_URI=https://salesforce-mcp.<env>.azurecontainerapps.io \
    SF_CLIENT_ID=<salesforce-consumer-key> \
    SF_CLIENT_SECRET=secretref:sf-secret \
    SF_LOGIN_URL=https://test.salesforce.com \
    SF_OAUTH_CALLBACK_URL=https://salesforce-mcp.<env>.azurecontainerapps.io/auth/salesforce/callback \
    AZURE_OPENAI_ENDPOINT=<aoai-endpoint> \
    AZURE_OPENAI_API_KEY=secretref:aoai-key \
    deployment=<deployment-name>
```

After deploy, update `config.cfg` → `[salesforce]` → `mcpServerUrl`.
**Also update** the Salesforce Connected App callback URL to the deployed URL.

### 6.3 SmartSales MCP

```bash
az containerapp create \
  --name smartsales-mcp \
  --resource-group $RESOURCE_GROUP \
  --environment $ENV_NAME \
  --image $ACR/smartsales-mcp:latest \
  --registry-server $ACR \
  --ingress external --target-port 8002 \
  --env-vars \
    MCP_RESOURCE_URI=https://smartsales-mcp.<env>.azurecontainerapps.io \
    GRANT_TYPE=client_credentials \
    CLIENT_ID_SMARTSALES=<smartsales-client-id> \
    CLIENT_SECRET_SMARTSALES=secretref:ss-secret \
    CODE_SMARTSALES=<smartsales-code> \
    AZURE_OPENAI_ENDPOINT=<aoai-endpoint> \
    AZURE_OPENAI_API_KEY=secretref:aoai-key \
    deployment=<deployment-name>
```

Update `config.cfg` → `[smartsales]` → `mcpServerUrl`.

### 6.4 Orchestrator MCP

```bash
az containerapp create \
  --name orchestrator-mcp \
  --resource-group $RESOURCE_GROUP \
  --environment $ENV_NAME \
  --image $ACR/orchestrator-mcp:latest \
  --registry-server $ACR \
  --ingress external --target-port 8003 \
  --env-vars \
    MCP_RESOURCE_URI=https://orchestrator-mcp.<env>.azurecontainerapps.io \
    ORCH_CLIENT_ID=<orchestrator-app-registration-client-id> \
    ORCH_CLIENT_SECRET=secretref:orch-secret \
    GRAPH_MCP_URL=https://graph-mcp.<env>.azurecontainerapps.io/mcp \
    SS_MCP_URL=https://smartsales-mcp.<env>.azurecontainerapps.io/mcp \
    SF_MCP_URL=https://salesforce-mcp.<env>.azurecontainerapps.io/mcp \
    AZURE_OPENAI_ENDPOINT=<aoai-endpoint> \
    AZURE_OPENAI_API_KEY=secretref:aoai-key \
    deployment=<deployment-name>
```

Note the final URL: `https://orchestrator-mcp.<env>.azurecontainerapps.io`

---

## 7. config.cfg

Fill in `config.cfg` in the project root:

```ini
[azure]
clientId      = <graph-mcp client id>
tenantId      = <tenant id>
graphUserScopes = https://graph.microsoft.com/User.Read https://graph.microsoft.com/Mail.Read https://graph.microsoft.com/Calendars.Read https://graph.microsoft.com/Contacts.Read https://graph.microsoft.com/Files.Read.All https://graph.microsoft.com/People.Read
clientSecret  = <graph-mcp client secret>
mcpServerUrl  = https://graph-mcp.<env>.azurecontainerapps.io/mcp

[orchestrator]
clientId      = <orchestrator client id>
clientSecret  = <orchestrator client secret>

[salesforce]
mcpServerUrl  = https://salesforce-mcp.<env>.azurecontainerapps.io/mcp
loginUrl      = https://test.salesforce.com
oauthCallbackUrl = http://localhost:8001/auth/salesforce/callback
tokenStore    = file

[smartsales]
mcpServerUrl  = https://smartsales-mcp.<env>.azurecontainerapps.io/mcp
```

---

## 8. .env File

Create a `.env` file in the project root (never commit this):

```env
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
AZURE_OPENAI_API_KEY=<your-key>
deployment=<gpt-4o-deployment-name>

# Salesforce
SF_CLIENT_ID=<salesforce-consumer-key>
SF_CLIENT_SECRET=<salesforce-consumer-secret>
SF_LOGIN_URL=https://test.salesforce.com
SF_OAUTH_CALLBACK_URL=http://localhost:8001/auth/salesforce/callback

# SmartSales
GRANT_TYPE=client_credentials
CLIENT_ID_SMARTSALES=<smartsales-client-id>
CLIENT_SECRET_SMARTSALES=<smartsales-client-secret>
CODE_SMARTSALES=<smartsales-code>

# Orchestrator (for local orchestrator/mcp_server.py)
ORCH_CLIENT_ID=<orchestrator-client-id>
ORCH_CLIENT_SECRET=<orchestrator-client-secret>
GRAPH_MCP_URL=https://graph-mcp.<env>.azurecontainerapps.io/mcp
SS_MCP_URL=https://smartsales-mcp.<env>.azurecontainerapps.io/mcp
SF_MCP_URL=https://salesforce-mcp.<env>.azurecontainerapps.io/mcp
```

---

## 9. Microsoft 365 Agents Toolkit — Copilot Declarative Agent

The `jj/` folder is the Teams/Copilot app that connects to the deployed orchestrator.

### Prerequisites
- VS Code with **Microsoft 365 Agents Toolkit** (ATK) extension installed
- M365 account with Copilot license, signed in to ATK

### Steps

1. **Open the `jj/` folder** in VS Code.

2. **Update URLs** in `jj/m365agents.yml`:
   - Replace all `orchestrator-mcp.<env>.azurecontainerapps.io` URLs with your deployed orchestrator URL.
   - Update `baseUrl`, `authorizationUrl`, and `tokenUrl`.

3. **Update `jj/appPackage/ai-plugin.json`**:
   - Set `"url"` under `runtimes[0].spec` to your orchestrator `/mcp` URL.

4. **Provision via ATK (vscode toolkit extension)**:
   - In VS Code Activity Bar: Agents Toolkit icon → **Provision**
   - ATK will:
     - Create a Teams App in Developer Portal
     - Register the OAuth connection (`orchestratormcp`) with your Client ID/Secret
     - Build the app package `.zip`
   - When prompted for OAuth, provide:
     - Client ID: `<orchestrator-app-registration-client-id>`
     - Client Secret: `<orchestrator-client-secret>`

5. **Publish**:
   - ATK → **Publish** → submits to Teams Admin Center for approval
   - Or sideload directly for testing: ATK → **Preview in Copilot**

6. **Test**: Open Microsoft 365 Copilot, select your agent, and ask a question.

---

## 10. Agent Roles

| Agent | Source | Tools exposed |
|-------|--------|---------------|
| **GraphAgent** | `agents/graph_agent.py` | All Microsoft Graph tools (emails, calendar, OneDrive, contacts, users) |
| **SalesforceAgent** | `agents/salesforce_agent.py` | Salesforce CRM (accounts, contacts, leads, opportunities) |
| **SmartSalesAgent** | `agents/smartsales_agent.py` | SmartSales locations and catalog |
| **PlanningOrchestrator** | `agents/planning_orchestrator.py` | Routes to sub-agents via a JSON plan (no direct tools) |

---

## 11. Common Troubleshooting

| Problem | Likely cause | Fix |
|---------|-------------|-----|
| OBO exchange fails (401) | Orchestrator App Registration missing Graph permissions | Add delegated Graph scopes + admin consent |
| Copilot shows "no tools" | `mcp-tools.json` out of date | Re-run ATK: Fetch Action from MCP |
| SmartSales auth fails on startup | Wrong env vars | Check `CLIENT_ID_SMARTSALES`, `CLIENT_SECRET_SMARTSALES`, `CODE_SMARTSALES` |
| Salesforce session not found | OAuth callback URL mismatch | Update Salesforce Connected App callback URL |
| Container App cold start timeout | First request takes 30-60s | Increase timeout in orchestrator init, or set min replicas to 1 |
| Graph API 403 | Missing consent on required scopes | Re-run admin consent in Azure Portal |
