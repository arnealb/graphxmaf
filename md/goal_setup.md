# Multi-Agent System — Architecture Overview

## Doel
Een multi-agent systeem dat via Microsoft 365 Copilot aanspreekbaar is, waarbij een orchestrator bepaalt welke gespecialiseerde agents nodig zijn om een user query te beantwoorden.

## Architectuur

```
User → Copilot → Orchestrator MCP Server (één "ask" tool)
                        ↓
                  Orchestrator LLM (Azure OpenAI)
                  plant welke agents nodig zijn
                        ↓
          ┌─────────────┼─────────────┐
          ↓             ↓             ↓
    Graph Agent    SF Agent    SmartSales Agent
    (LLM + MCP)   (LLM + MCP)   (LLM + MCP)
          ↓             ↓             ↓
    Graph MCP      SF MCP      SmartSales MCP
     Server        Server         Server
          ↓             ↓             ↓
    Microsoft     Salesforce     SmartSales
      Graph          API            API
```

## Orchestrator Flow

1. Copilot stuurt user query naar Orchestrator MCP Server (via `ask` tool)
2. Orchestrator LLM analyseert de query en plant welke agents nodig zijn
3. Sub-agents worden aangeroepen (parallel of sequentieel) — elk is een agentic loop (LLM + MCP tools)
4. Orchestrator LLM combineert de resultaten tot één antwoord
5. Antwoord gaat terug naar Copilot → gebruiker

## Wat er draait

| Component | Status | Locatie |
|---|---|---|
| Graph MCP Server | ✅ Draait | Azure Container App (`graph-mcp`) |
| Salesforce MCP Server | ✅ Draait | Azure Container App |
| SmartSales MCP Server | ✅ Draait | Azure Container App |
| Copilot Declarative Agent | ✅ Geprovisioned | Teams/M365 app `jjdev` |
| Orchestrator MCP Server | ❌ Nog te bouwen | — |

## Copilot Integratie (vandaag opgezet)

- **App Registration**: `8f75486a-80ed-41ba-9337-6c0deb6dc98d` (Graph MCP Server)
- **Tenant**: `b112dc60-a22d-4ff4-b07a-cb1dc8d6fdf5`
- **MCP URL**: `https://graph-mcp.whitemushroom-38caf70a.swedencentral.azurecontainerapps.io/mcp`
- **OAuth**: Proxy endpoints op de MCP server (`/authorize`, `/token`, `/.well-known/*`)
- **OBO flow**: Inkomend `api://...` token wordt gewisseld voor Graph token
- **Redirect URIs**: `http://localhost:33418/`, `https://teams.microsoft.com/api/platform/v1.0/oAuthRedirect`

## Key Files — Graph MCP Server

| File | Rol |
|---|---|
| `mcp_server.py` | MCP server + OAuth proxy + OBO exchange |
| `graph/mcp_router.py` | Registreert tools, dispatcht naar repository |
| `graph/repository.py` | Graph API calls |
| `graph/tools.yaml` | Tool definities |
| `config.cfg` | Azure AD credentials |

## Key Files — Copilot App Package (`jj/appPackage/`)

| File | Rol |
|---|---|
| `manifest.json` | Teams app manifest |
| `declarativeAgent.json` | Agent definitie + link naar plugin |
| `ai-plugin.json` | Plugin met 11 functies + MCP runtime |
| `mcp-tools.json` | MCP tool schemas |
| `m365agents.yml` | Provisioning config (OAuth register + deploy) |

## Opgeloste Issues (vandaag)

1. `AADSTS900144` — scope ontbrak in authorize request → `scopes_supported` gefixed in resource metadata
2. `AADSTS500011` — Application ID URI niet ingesteld → `api://...` URI + scope aangemaakt
3. `AADSTS50011` redirect mismatch — `127.0.0.1` → `localhost` rewrite in authorize + token proxy
4. Token exchange 400 — redirect_uri mismatch tussen authorize/token → rewrite in beide proxies
5. `MissingPluginFunction` — manifest had geen functions → MCP tools fetch + oauth/register config gefixed
6. `invalid_client` — client_secret ontbrak in token proxy → geïnjecteerd
7. Graph 401 — inkomend token was voor eigen API, niet Graph → OBO flow geïmplementeerd

## Volgende Stap

Orchestrator MCP Server bouwen die:
- Eén `ask` tool exposed aan Copilot
- Orchestrator LLM bevat die de query analyseert
- Sub-agents (Graph, Salesforce, SmartSales) aanspreekt via MCP
- Resultaten combineert tot één antwoord