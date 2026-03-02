# Architectuur & Request-flow — graphxmaf

## Overzicht

```
Gebruiker
   │
   ▼
[main.py]  ──── MSAL auth (device code / cache) ──▶ Azure AD token
   │
   ├─ start lokale MCP server (subprocess: mcp_api_tool.py :8000)
   │
   ├─ maak httpx.AsyncClient  (Authorization: Bearer <token>)
   │
   ├─ MCPStreamableHTTPTool("graph", url="http://localhost:8000/mcp")
   │
   └─ create_graph_agent(graph_mcp)
         └─ Agent(OpenAIChatClient, tools=[graph_mcp])
               │
               ▼
         agent_framework.devui.serve()  →  browser UI op :8080
```

---

## Lagen

| Laag | Bestand | Rol |
|---|---|---|
| **Entry point** | `main.py` | Auth, server opstarten, agent bouwen |
| **AI agent** | `agent.py` | LLM + MCP tool wrappen in `Agent` |
| **MCP server** | `mcp_api_tool.py` | FastMCP HTTP server, tool-definities |
| **Domain agent** | `entities/graph_agent.py` | Businesslogica, caching, formattering |
| **Repository** | `graph/repository.py` | Graph SDK calls, OData filters |
| **Auth helper** | `auth/token_credential.py` | Bearer token als `azure.core.credentials` |
| **Data models** | `data/classes.py` | Dataclasses: Email, File, Contact, … |
| **Interface** | `entities/IGraphRepository.py` | Abstract base voor repository |

---

## Authenticatie

### Client-side (main.py)
1. `msal.PublicClientApplication` met `client_id` + `tenant_id` uit `config.cfg`.
2. Eerst proberen via **token cache** (`.token_cache.bin`).
3. Als geen cache → **device code flow**: gebruiker gaat naar `login.microsoftonline.com` en vult code in.
4. Resulterende `access_token` wordt opgeslagen en meegestuurd als `Authorization: Bearer <token>` header bij elk HTTP request naar de MCP server.

### Server-side (mcp_api_tool.py)
- Exposeert `/.well-known/oauth-protected-resource` (PRM endpoint) zodat MCP clients weten hoe ze moeten authenticeren.
- `_extract_token(ctx)`: haalt de Bearer token uit de inkomende HTTP request.
- `StaticTokenCredential` (auth/token_credential.py): wrapet de token als `azure.core.credentials.AccessToken` zodat de Graph SDK hem kan gebruiken.

---

## Request-flow: van gebruiker tot Microsoft Graph

```
Gebruiker typt vraag in browser UI (:8080)
   │
   ▼
Agent (OpenAI LLM via agent_framework)
   │   beslist welke tool nodig is
   ▼
MCPStreamableHTTPTool
   │   HTTP POST naar http://localhost:8000/mcp
   │   header: Authorization: Bearer <token>
   ▼
FastMCP server (mcp_api_tool.py)
   │   _extract_token(ctx)  →  token uit header
   │   _make_agent(token)   →  GraphAgent (of uit cache)
   ▼
GraphAgent (entities/graph_agent.py)
   │   businesslogica + in-memory caching
   ▼
GraphRepository (graph/repository.py)
   │   msgraph-sdk  (GraphServiceClient)
   │   OData query parameters samenstellen
   ▼
Microsoft Graph API (graph.microsoft.com)
   │   HTTP response
   ▼
GraphRepository  →  dataclasses (Email, File, …)
GraphAgent       →  formatteert naar tekst string
MCP tool         →  stuurt string terug naar LLM
LLM              →  antwoord naar gebruiker
```

---

## Concrete Graph-aanroepen per tool

### `whoami`
```
GET /me?$select=displayName,mail,userPrincipalName
```

### `findpeople(name)`
Drie parallelle zoekopdrachten, resultaten samenvoegen:
1. **Directory**: `GET /users?$filter=startswith(displayName,'...')` (top 5)
2. **Mail**: `GET /me/messages?$search="..."&$select=from,toRecipients,ccRecipients` (top 5)
3. **Contacts**: `GET /me/contacts?$select=displayName,emailAddresses` (top 5)

### `search_email`
```
GET /me/messages
  ?$select=id,subject,from,receivedDateTime,webLink
  &$filter=contains(from/emailAddress/address,'...')
           and contains(subject,'...')
           and receivedDateTime ge ...
           and receivedDateTime le ...
  &$top=25
```

### `list_email`
```
GET /me/mailFolders/inbox/messages
  ?$select=id,from,isRead,receivedDateTime,subject,webLink
  &$top=25
  &$orderby=receivedDateTime DESC
```

### `read_email(message_id)`
Eerst in-memory cache controleren, anders:
```
GET /me/messages/{id}
  ?$select=id,subject,from,receivedDateTime,body,webLink
```

### `search_files(query)`
```
GET /drives/{drive_id}/items/root/search(q='{query}')
  ?$select=id,name,webUrl,size,createdDateTime,...
  &$top=25
```
Drive ID wordt eerst opgehaald via `GET /me/drive`.

### `list_contacts`
```
GET /me/contacts
  ?$select=id,displayName,emailAddresses
  &$top=15
```

### `list_calendar`
Twee calls:
```
GET /me/events?$filter=start/dateTime ge '{now}'&$orderby=start/dateTime&$top=10
GET /me/events?$filter=start/dateTime lt '{now}'&$orderby=start/dateTime desc&$top=10
```

### `search_calendar`
```
GET /me/events
  ?$filter=contains(subject,'...')
           and contains(location/displayName,'...')
           and start/dateTime ge '...'
           and start/dateTime le '...'
  &$top=25
```
Attendee-filter wordt **client-side** gedaan (Graph OData ondersteunt dit niet direct):
→ `findpeople(attendee)` aanroepen, daarna events filteren op email-adressen.

---

## In-memory caching (GraphAgent)

`GraphAgent` houdt per server-instantie (= per token) een cache bij:

| Cache | Key | Gevuld door |
|---|---|---|
| `_email_cache` | message id | `list_email`, `search_email` |
| `_file_cache` | item id | `list_files`, `search_files` |
| `_contact_cache` | contact id | `list_contacts` |
| `_event_cache` | event id | `list_calendar` |
| `_people_cache` | email address | `find_people` |

`read_email` kijkt eerst in cache voor het opgeslagen bericht; pas als het er niet in staat, doet het een Graph API call.

---

## Configuratie

`config.cfg`:
```ini
[azure]
clientId     = <app registration id>
tenantId     = <tenant id>
graphUserScopes = User.Read Mail.Read Calendars.Read Contacts.Read Files.Read Chat.Read
mcpServerUrl = http://localhost:8000/mcp
```

`.env`:
- `deployment` — naam van het Azure OpenAI deployment (gebruikt door `OpenAIChatClient`)

---

## Lokaal vs. cloud

`main.py` detecteert automatisch of de MCP server lokaal of remote is:

```python
if _is_local_url(mcp_url):        # localhost / 127.0.0.1
    server_proc = _start_local_mcp_server(server_env)
```

- **Lokaal**: `mcp_api_tool.py` wordt gestart als subprocess, poort 8000.
- **Cloud (APIM)**: alleen de `httpx.AsyncClient` met Bearer token is nodig; de server draait al elders.

---

## Dependencies

| Package | Waarvoor |
|---|---|
| `msal` | MSAL OAuth2 / device code flow |
| `azure-identity` | `DeviceCodeCredential` (fallback in repo) |
| `msgraph-sdk` | Typed Graph API client |
| `mcp` / `fastmcp` | MCP server (Streamable HTTP transport) |
| `httpx` | HTTP client voor MCP calls |
| `openai` | LLM backend (via agent_framework) |
| `agent-framework` | Agent loop + devUI + `MCPStreamableHTTPTool` |
| `starlette` | Web framework onder FastMCP |
