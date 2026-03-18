# Salesforce Agent — Architecture & Auth Reference

## Overview

The Salesforce integration is a full stack: auth → MCP server subprocess → tool routing → SOQL repository → AI agent → orchestrator. Everything is wired up in `main.py` at startup.

```
main.py
  ├── authenticate_salesforce()       # JWT Bearer → access_token + instance_url
  ├── _start_salesforce_mcp_server()  # spawns salesforce.mcp_server as subprocess
  ├── MCPStreamableHTTPTool           # HTTP client with Bearer token header
  └── create_salesforce_agent()       # Agent wrapping the MCP tool
        └── create_orchestrator_agent()  # routes queries to SF or Graph agent
```

---

## 1. Authentication — JWT Bearer Token Flow

**File:** `salesforce/auth.py`

Salesforce is authenticated **before** anything else starts. The app uses the **OAuth 2.0 JWT Bearer Token flow** — no interactive login, no password prompt, no MFA issues.

### How it works

1. Read `SF_CLIENT_ID` and `SF_USERNAME` from `.env`.
2. Load the RSA private key from `SF_PRIVATE_KEY_PATH` (file path, e.g. `salesforce.key`) or `SF_PRIVATE_KEY` (PEM string in env).
3. Build a signed JWT with these claims:

   | Claim | Value |
   |-------|-------|
   | `iss` | `SF_CLIENT_ID` (the Connected App's Consumer Key) |
   | `sub` | `SF_USERNAME` (e.g. `aalb@easi.net/ai-search`) |
   | `aud` | `SF_LOGIN_URL` (e.g. `https://test.salesforce.com`) |
   | `exp` | `now + 180 seconds` (Salesforce maximum) |

4. Sign the JWT with `RS256` using the private key (PyJWT + cryptography).
5. POST to `{login_url}/services/oauth2/token` with:
   ```
   grant_type = urn:ietf:params:oauth:grant-type:jwt-bearer
   assertion  = <signed JWT>
   ```
6. Parse the response → `SalesforceCredentials(access_token, instance_url)`.

### Entry point

`main.py` calls:
```python
sf_creds = authenticate_salesforce(login_url=sf_login_url)
```

`authenticate_salesforce()` reads env vars and delegates to `authenticate_jwt()`, which does the JWT construction and POST.

### Required files & env vars

| Env var | Purpose |
|---------|---------|
| `SF_CLIENT_ID` / `SF_CONSUMER_KEY` | Connected App consumer key |
| `SF_USERNAME` | Salesforce username (with sandbox alias suffix if needed) |
| `SF_PRIVATE_KEY_PATH` | Path to the RSA `.key` file (currently `salesforce.key`) |
| `SF_PRIVATE_KEY` | Alternative: PEM string directly in env |
| `SF_LOGIN_URL` | `https://test.salesforce.com` for sandbox, `https://login.salesforce.com` for prod |

**Key files in repo root:**
- `salesforce.key` — RSA private key (PEM format), used to sign the JWT
- `salesforce.crt` — Certificate (public key), uploaded to the Salesforce Connected App

### Salesforce side requirements

The Connected App in Salesforce must:
- Have the digital certificate (`salesforce.crt`) uploaded under "Use digital signatures"
- Have the user (`SF_USERNAME`) pre-authorized in the Connected App policies
- Have the OAuth scopes: `api`, `refresh_token` (at minimum)

### Error type

Any failure raises `SalesforceAuthError(RuntimeError)` with the Salesforce JSON `error_description` included.

---

## 2. MCP Server — `salesforce/mcp_server.py`

After auth, `main.py` spawns the MCP server as a **subprocess** (only when the URL is localhost):

```python
sf_proc = _start_salesforce_mcp_server(sf_server_env, sf_mcp_url)
```

The server runs at `http://localhost:8001/mcp` (FastMCP, streamable-HTTP transport).

Two critical env vars are passed to the subprocess:
- `SF_INSTANCE_URL` — the resolved Salesforce instance URL from auth (e.g. `https://yourorg.my.salesforce.com`)
- `MCP_RESOURCE_URI` — the MCP server's own base URL

### OAuth metadata endpoint

The server exposes:
```
GET /.well-known/oauth-protected-resource
→ { "resource": "<MCP_RESOURCE_URI>", "bearer_methods_supported": ["header"] }
```

This is the standard MCP OAuth discovery endpoint.

### Token extraction

Each tool call extracts the Bearer token from the incoming HTTP `Authorization` header:
```python
def _extract_token(ctx: Context) -> str:
    auth = http_request.headers.get("authorization", "")
    return auth[7:]  # strips "Bearer "
```

The token passed in is the **Salesforce access token** acquired during startup in `main.py`, forwarded via `httpx.AsyncClient(headers={"Authorization": f"Bearer {sf_creds.access_token}"})`.

---

## 3. Tool Registration — `salesforce/mcp_router.py`

Tools are not hardcoded — they are loaded dynamically from `salesforce/tools.yaml` at server startup.

```python
register_salesforce_tools(mcp, _INSTANCE_URL, _extract_token)
```

For each tool definition in the YAML:
1. Build a dynamic `async def handler(ctx, **kwargs)` closure.
2. Construct a proper `inspect.Signature` so FastMCP can introspect parameter types.
3. Register with `mcp.tool(name=..., description=...)`.

### Method alias

`find_accounts` in the YAML maps to `get_accounts` in the repository (via `_SF_METHOD_ALIASES`).

### Repo caching

`SalesforceRepository` instances are cached per access token:
```python
_repo_cache: dict[str, SalesforceRepository] = {}
```

---

## 4. Tools — `salesforce/tools.yaml`

Five tools are registered:

| Tool name | Repository method | Description |
|-----------|-------------------|-------------|
| `find_accounts` | `get_accounts` | Search accounts by name or filter by industry/type/etc. |
| `find_contacts` | `find_contacts` | Search contacts by name or email |
| `find_leads` | `find_leads` | Search leads by name, email, or company |
| `get_opportunities` | `get_opportunities` | List opportunities, filter by account ID or stage |
| `get_cases` | `get_cases` | List cases, filter by account ID or status |

Each tool supports:
- `query` — plain text keyword (triggers a `LIKE` condition on the primary name field)
- `extra_fields` — list of extra SOQL columns to SELECT (strict allowlist per object)
- `filters` — `{SoqlField: value}` dict for additional WHERE conditions (strict allowlist)

---

## 5. Repository — `salesforce/repository.py`

`SalesforceRepository` executes **SOQL queries** against the Salesforce REST API.

**API version:** `v59.0`
**Endpoint pattern:** `{instance_url}/services/data/v59.0/query?q=<soql>`

### Key design decisions

- **Allowlists** — every object has `_*_SELECTABLE` (extra fields you can SELECT) and `_*_FILTERABLE` (fields you can filter on). Anything not in these sets is silently ignored.
- **Numeric fields** — fields like `NumberOfEmployees`, `AnnualRevenue`, `Probability` use exact equality (`=`); string fields use `LIKE '%...%'`.
- **SQL injection prevention** — `_esc()` escapes single quotes before interpolating user input into SOQL.
- **Default limits** — most methods default to `top=25` records.

### Base fields per object

| Object | Always selected |
|--------|----------------|
| Account | Id, Name, Industry, Website |
| Contact | Id, FirstName, LastName, Email, Account.Name |
| Lead | Id, FirstName, LastName, Email, Company, Status |
| Opportunity | Id, Name, StageName, Amount, CloseDate, Account.Name |
| Case | Id, Subject, Status, Priority, Account.Name, CreatedDate |

### Pydantic models — `salesforce/models.py`

Each repository method returns typed Pydantic models:
- `SalesforceAccount`
- `SalesforceContact`
- `SalesforceLead`
- `SalesforceOpportunity`
- `SalesforceCase`

---

## 6. The Agent — `agents/salesforce_agent.py`

```python
def create_salesforce_agent(salesforce_mcp):
    return Agent(
        client=AzureOpenAIChatClient(deployment="gpt-4o-mini", ...),
        name="SalesforceAgent",
        tools=[salesforce_mcp],   # the MCPStreamableHTTPTool
        ...
    )
```

### LLM

Azure OpenAI — `gpt-4o-mini`, endpoint/key from `.env` (`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `deployment`), API version `2024-12-01-preview`.

### Tool selection rules (from system prompt)

- `find_accounts` → questions about companies or accounts
- `find_contacts` → questions about existing CRM people
- `find_leads` → questions about prospective customers
- `get_opportunities` → questions about deals or sales pipeline
- `get_cases` → questions about support tickets

Rules are strict: only call tools the request explicitly requires, never speculatively.

### Output format

The agent returns **raw JSON** — no prose:
- Single tool called → return the tool result directly
- Multiple tools called → return `[{"tool": "<name>", "result": <result>}, ...]`

---

## 7. Orchestrator — `agents/orchestrator_agent.py`

The `OrchestratorAgent` sits above both agents and routes queries:

```python
def create_orchestrator_agent(graph_agent: Agent, salesforce_agent: Agent) -> Agent:
```

It wraps each sub-agent as a `FunctionTool`:
- `ask_graph_agent` — Microsoft 365 data (email, calendar, OneDrive, contacts, identity)
- `ask_salesforce_agent` — CRM data (accounts, contacts, leads, opportunities, cases)

Routing rules:
- M365 data → `ask_graph_agent`
- CRM data → `ask_salesforce_agent`
- Spans both → call both, combine results (clearly labeled "From Microsoft 365:" / "From Salesforce:")

Both sub-agent tools have `approval_mode="never_require"` — no human confirmation needed.

---

## 8. Startup flow (end-to-end)

```
main.py
│
├─ 1. Read config.cfg → sf_login_url, sf_mcp_url
│
├─ 2. authenticate_salesforce(sf_login_url)
│     ├─ read SF_CLIENT_ID, SF_USERNAME, SF_PRIVATE_KEY_PATH from .env
│     ├─ load salesforce.key
│     ├─ build & sign JWT (RS256, exp=now+180s)
│     ├─ POST https://test.salesforce.com/services/oauth2/token
│     └─ return SalesforceCredentials(access_token, instance_url)
│
├─ 3. Pass SF_INSTANCE_URL to subprocess env
│
├─ 4. _start_salesforce_mcp_server(env, "http://localhost:8001/mcp")
│     ├─ python -m salesforce.mcp_server
│     ├─ FastMCP starts on :8001
│     ├─ loads tools from salesforce/tools.yaml
│     └─ waits for port 8001 to be ready
│
├─ 5. Build httpx.AsyncClient with Authorization: Bearer <access_token>
│
├─ 6. MCPStreamableHTTPTool("salesforce", url="http://localhost:8001/mcp", http_client)
│
├─ 7. create_salesforce_agent(salesforce_mcp)
│
├─ 8. create_orchestrator_agent(graph_agent, sf_agent)
│
└─ 9. serve([orchestrator, graph_agent, sf_agent], port=8080)
```

On shutdown (finally block), both the Graph and Salesforce MCP server subprocesses are terminated.

---

## 9. Configuration reference

### `config.cfg` (active section)

```ini
[salesforce]
loginUrl      = https://test.salesforce.com
mcpServerUrl_sf = https://salesforce-mcp.calmsea-ac909996.norwayeast.azurecontainerapps.io/mcp
mcpUserScopes = User.Read
```

> **Note:** `mcpServerUrl_sf` points to Azure Container Apps in production. The `_is_local_url()` check in `main.py` determines whether to spawn the local subprocess or connect to the cloud URL directly.

### `.env` (Salesforce-relevant vars)

```
SF_LOGIN_URL=https://test.salesforce.com
SF_CLIENT_ID=<consumer key from Connected App>
SF_CONSUMER_KEY=<same as SF_CLIENT_ID>
SF_USERNAME=<salesforce username>
SF_PRIVATE_KEY_PATH=salesforce.key
```

The `SF_CLIENT_SECRET`, `SF_PASSWORD`, and `SF_SECURITY_TOKEN` vars in `.env` are **not used** — they are leftovers from an older password-grant flow that was replaced by JWT.
