# Claude Code Handoff — Multi-Agent System voor Copilot

## Context

Ik bouw een multi-agent systeem voor mijn masterproef dat via Microsoft 365 Copilot aanspreekbaar is.

## Huidige situatie

### Wat draait er al

1. **Graph MCP Server** — Azure Container App (`graph-mcp`)
   - URL: `https://graph-mcp.whitemushroom-38caf70a.swedencentral.azurecontainerapps.io/mcp`
   - 11 tools: whoami, list_email, read_email, search_email, list_calendar, search_calendar, list_contacts, search_files, read_file, read_multiple_files, findpeople
   - OAuth proxy endpoints (`/authorize`, `/token`, `/.well-known/*`)
   - OBO flow: wisselt inkomend `api://...` token om voor Graph token
   - App Registration: `8f75486a-80ed-41ba-9337-6c0deb6dc98d`
   - Tenant: `b112dc60-a22d-4ff4-b07a-cb1dc8d6fdf5`

2. **Salesforce MCP Server** — Azure Container App (al werkend)

3. **SmartSales MCP Server** — Azure Container App (al werkend)

4. **Copilot Declarative Agent** (`jjdev`) — geprovisioned via M365 Agents Toolkit in VS Code
   - Teams App ID: `372bc365-d3bd-40d5-bb8d-12fa76e409c3`
   - Praat momenteel DIRECT met Graph MCP Server (moet straks naar Orchestrator wijzen)
   - App package in `jj/appPackage/` (manifest.json, ai-plugin.json, declarativeAgent.json, mcp-tools.json)
   - Provisioning config in `jj/m365agents.yml`

### Huidige flow (werkt, maar niet de gewenste architectuur)

```
User → Copilot → Graph MCP Server → Microsoft Graph
         ↑
   Copilot's LLM kiest de tools (geen aparte agent)
```

## Gewenste architectuur

```
User → Copilot → Orchestrator MCP Server (één "ask" tool)
                        ↓
                  Orchestrator LLM (Azure OpenAI)
                  analyseert query, plant welke agents nodig zijn
                        ↓
          ┌─────────────┼─────────────┐
          ↓             ↓             ↓
    Graph Agent    SF Agent    SmartSales Agent
    (eigen LLM)   (eigen LLM)   (eigen LLM)
    agentic loop   agentic loop   agentic loop
          ↓             ↓             ↓
    Graph MCP      SF MCP      SmartSales MCP
     Server        Server         Server
          ↓             ↓             ↓
    Microsoft     Salesforce     SmartSales
      Graph          API            API
```

### Key design decisions

- **Copilot** stuurt enkel de user query door naar Orchestrator (één `ask` tool)
- **Orchestrator LLM** beslist welke sub-agents nodig zijn (kan er meerdere kiezen)
- **Sub-agents** zijn elk een aparte LLM (Azure OpenAI) met MCP client die hun MCP server aanspreekt
- Elke sub-agent doet een **agentic loop**: meerdere tool calls tot hij een antwoord heeft
- **Orchestrator combineert** de resultaten van alle sub-agents tot één antwoord
- De bestaande MCP servers (Graph, SF, SmartSales) **blijven ongewijzigd** draaien

### Orchestrator pseudocode

```python
@mcp.tool(name="ask", description="Ask the multi-agent system a question")
async def ask(ctx: Context, query: str) -> str:
    # 1. Orchestrator LLM beslist welke agents nodig zijn
    plan = await orchestrator_llm.plan(query)
    # bijv. plan = ["graph", "salesforce"]

    # 2. Roep benodigde agents aan (parallel of sequentieel)
    results = {}
    for agent_name in plan.agents:
        results[agent_name] = await call_agent(agent_name, plan.sub_query[agent_name])

    # 3. Orchestrator LLM combineert resultaten tot één antwoord
    final_answer = await orchestrator_llm.synthesize(query, results)
    return final_answer
```

## Wat er gebouwd moet worden

### 1. Orchestrator MCP Server (nieuwe Azure Container App)

```
orchestrator/
├── mcp_server.py          → MCP server met één "ask" tool + OAuth proxy
├── orchestrator.py        → Planning logica (welke agents nodig?)
├── agents/
│   ├── graph_agent.py     → LLM + MCP client → Graph MCP Server
│   ├── sf_agent.py        → LLM + MCP client → Salesforce MCP Server
│   └── ss_agent.py        → LLM + MCP client → SmartSales MCP Server
├── config.cfg
├── Dockerfile
└── requirements.txt
```

- OAuth proxy kan grotendeels gekopieerd worden van de Graph MCP Server
- OBO flow is nodig voor Graph Agent (token doorsturen)
- Salesforce/SmartSales agents hebben hun eigen auth

### 2. Toolkit config updaten (eenmalig)

- `ai-plugin.json`: MCP URL veranderen naar Orchestrator, 11 tools vervangen door één `ask` tool
- `m365agents.yml`: OAuth register updaten naar Orchestrator endpoints
- Opnieuw provisioneren via de toolkit

## Technische details

### Azure resources

- Resource group: `Global-Search-Agent`
- ACR: `graphxmafacr2.azurecr.io`
- Deploy commando patroon:
  ```powershell
  $TAG = (Get-Date -Format "yyyyMMdd-HHmm")
  docker build -f Dockerfile.graph -t graphxmafacr2.azurecr.io/graph-mcp:$TAG .
  docker push graphxmafacr2.azurecr.io/graph-mcp:$TAG
  az containerapp update --name graph-mcp --resource-group "Global-Search-Agent" --image graphxmafacr2.azurecr.io/graph-mcp:$TAG
  ```

### Key files Graph MCP Server (referentie voor orchestrator)

- `mcp_server.py` — MCP server + OAuth proxy + OBO exchange
- `graph/mcp_router.py` — Tool registratie + dispatch
- `graph/repository.py` — Graph API calls
- `graph/tools.yaml` — Tool definities
- `auth/token_credential.py` — StaticTokenCredential voor Graph SDK
- `config.cfg` — Azure AD credentials (clientId, clientSecret, tenantId, graphUserScopes)

### Issues opgelost vandaag (referentie)

1. Scope ontbrak in authorize request → `scopes_supported` gefixed in resource metadata
2. Application ID URI niet ingesteld → `api://...` URI + `access_as_user` scope aangemaakt
3. Redirect URI mismatch → `127.0.0.1` → `localhost` rewrite in authorize + token proxy
4. Token exchange mismatch → rewrite in beide proxies (authorize + token)
5. MissingPluginFunction → MCP tools fetch + oauth/register config met authorizationUrl, tokenUrl, apiSpecPath
6. invalid_client → client_secret geïnjecteerd in token proxy
7. Graph 401 → OBO flow geïmplementeerd (inkomend api:// token → Graph token)

## Instructie voor Claude Code

Bekijk mijn hele project structuur. Help me de Orchestrator MCP Server bouwen:
1. Hergebruik de OAuth proxy structuur van de Graph MCP Server
2. Bouw de orchestrator logica met Azure OpenAI
3. Bouw de sub-agents als MCP clients die de bestaande MCP servers aanspreken
4. Maak het deployable als Azure Container App