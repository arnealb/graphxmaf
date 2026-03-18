# Salesforce OAuth 2.0 Authorization Code Flow

> This document replaces the JWT-Bearer section in `salesforce_agent.md`.
> The JWT flow still exists in `salesforce/auth.py` but is no longer used by
> the MCP server or `main.py`.

---

## Architecture overview

```
Browser / user
  └─ GET /auth/salesforce/login
       └─ 302 → Salesforce OAuth consent page
            └─ GET /auth/salesforce/callback?code=...&state=...
                 ├─ exchange code → SF token endpoint
                 ├─ StoredTokens saved to token_store
                 └─ JSON { "session_token": "<uuid>" }

MCP client (main.py / agent)
  └─ Authorization: Bearer <session_token (UUID)>
       └─ mcp_server._resolve_session(session_token)
            ├─ token_store.get(session_token) → StoredTokens
            ├─ is_expired(buffer=300s)?
            │     yes → refresh_access_token() → token_store.save()
            └─ SalesforceRepository(access_token, instance_url) → SOQL
```

The **session token** is a UUID — it is what the MCP client puts in the
`Authorization: Bearer` header.  The raw Salesforce access token never leaves
the MCP server process.

---

## New files & modules

### `salesforce/token_store.py`

| Symbol | Purpose |
|--------|---------|
| `StoredTokens` | Dataclass: `access_token`, `refresh_token`, `instance_url`, `expires_at`, `user_id`, `username` |
| `StoredTokens.is_expired(buffer=300)` | True if token expires within `buffer` seconds |
| `StoredTokens.from_token_response(dict)` | Build from a raw SF `/services/oauth2/token` response |
| `SalesforceTokenStore` (ABC) | `get`, `save`, `delete`, `generate_session_token` |
| `JsonFileTokenStore` | Dev store: JSON file (`.salesforce_tokens.json`), asyncio-locked |
| `AzureKeyVaultTokenStore` | Prod store: secrets named `sf-session-<uuid>` in Key Vault |
| `build_token_store()` | Factory — reads `SF_TOKEN_STORE` env var |

### New functions in `salesforce/auth.py`

| Function | What it does |
|----------|-------------|
| `build_authorization_url(...)` | Returns the SF `/services/oauth2/authorize?...` redirect URL |
| `async exchange_code_for_tokens(...)` | POST to SF token endpoint with `grant_type=authorization_code` |
| `async refresh_access_token(...)` | POST to SF token endpoint with `grant_type=refresh_token` |

`SalesforceCredentials` gained an optional `expires_at: float` field.

---

## OAuth routes on the MCP server

All routes are served by `salesforce/mcp_server.py` (FastMCP custom routes).

### `GET /auth/salesforce/login`

| Query param | Purpose |
|------------|---------|
| `redirect_after` | (optional) URL to redirect to after login |

1. Generates a CSRF `state` UUID and stores it in `_pending_states`.
2. Calls `build_authorization_url(client_id, redirect_uri, login_url, state)`.
3. Returns `302 → <SF authorize URL>`.

### `GET /auth/salesforce/callback`

| Query param | Required |
|------------|---------|
| `code` | Yes — authorization code from SF |
| `state` | Yes — must match a value in `_pending_states` |

1. Validates state (CSRF protection).
2. Calls `exchange_code_for_tokens(code, client_id, client_secret, redirect_uri, login_url)`.
3. Builds `StoredTokens.from_token_response(token_data)`.
4. Calls `token_store.save(session_token, tokens)`.
5. Returns `200 { "session_token": "<uuid>", "username": "..." }`.

### `POST /auth/salesforce/logout`

Reads the `Authorization: Bearer <session_token>` header, calls
`token_store.delete(session_token)`.

---

## Session resolution (`_resolve_session`)

Called on **every** MCP tool invocation:

```
session_token (UUID from Bearer header)
  │
  ├─ token_store.get(session_token)
  │     None  → RuntimeError("Re-authenticate at /auth/salesforce/login")
  │
  ├─ tokens.is_expired(buffer=300s)?
  │     No  → use as-is
  │     Yes →
  │       refresh_access_token(refresh_token, client_id, client_secret, login_url)
  │         OK     → StoredTokens.from_token_response(refreshed)
  │                   preserve existing refresh_token if not returned
  │                   token_store.save(session_token, new_tokens)
  │         Error  → token_store.delete(session_token)
  │                   RuntimeError("Token refresh failed. Re-authenticate.")
  │
  └─ return SalesforceCredentials(access_token, instance_url, expires_at)
```

---

## Token lifecycle

```
expires_at = issued_at + expires_in   (default: 7200 s / 2 h)
buffer     = 300 s                    (refresh 5 min before actual expiry)

Every MCP tool call:
  is_expired(300)?
    No  → pass access_token directly to SalesforceRepository
    Yes → POST /services/oauth2/token {grant_type=refresh_token, ...}
          → new access_token + new expires_at
          → refresh_token unchanged (unless SF rotates it)
```

Salesforce returns `issued_at` as **epoch milliseconds** (string).
`from_token_response` converts it: `float(issued_at) / 1000`.

---

## Token store backends

| Backend | `SF_TOKEN_STORE` value | Storage |
|---------|----------------------|---------|
| `JsonFileTokenStore` | `file` (default) | `.salesforce_tokens.json` |
| `AzureKeyVaultTokenStore` | `azure_keyvault` | Key Vault secrets `sf-session-<uuid>` |

Optional encryption for the file store: set `SF_TOKEN_STORE_ENCRYPTION_KEY`
to a Fernet key (requires `cryptography` package).

---

## Repo cache invalidation

`mcp_router.py` caches `SalesforceRepository` instances per session:

```python
_repo_cache: dict[str, tuple[SalesforceRepository, str]] = {}
# key = session_token → (repo, cached_access_token)
```

When `_resolve_session` returns a **new** access token after a refresh, the
cached access token no longer matches and a fresh `SalesforceRepository` is
created automatically.

---

## First-time dev setup

```
1.  python -m salesforce.mcp_server        # start MCP server standalone

2.  Open in browser:
    http://localhost:8001/auth/salesforce/login

3.  Log in to Salesforce (sandbox or prod)

4.  Browser lands on callback → returns JSON:
    { "session_token": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx", "username": "..." }

5.  Copy the UUID into .env:
    SF_SESSION_TOKEN=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

6.  Ctrl+C the standalone server

7.  python main.py   ← picks up SF_SESSION_TOKEN, starts everything normally
```

---

## Startup flow in `main.py` (updated)

```
main.py
│
├─ 1. Read config.cfg → sf_mcp_url
│
├─ 2. Read SF_SESSION_TOKEN from env
│     missing → print re-auth instructions → sys.exit(1)
│
├─ 3. Build sf_server_env (os.environ.copy + MCP_RESOURCE_URI)
│     (no SF_INSTANCE_URL injection — MCP server reads it from token_store)
│
├─ 4. _start_salesforce_mcp_server(sf_server_env, sf_mcp_url)
│     └─ python -m salesforce.mcp_server
│          ├─ build_token_store()        → JsonFileTokenStore
│          ├─ _token_store singleton ready
│          └─ FastMCP registers OAuth routes + MCP tools
│
├─ 5. httpx.AsyncClient(Authorization: Bearer <session_token UUID>)
│
├─ 6. MCPStreamableHTTPTool("salesforce", url=sf_mcp_url, http_client)
│
└─ 7. create_salesforce_agent(sf_mcp) → orchestrator → serve(:8080)
```

---

## Environment variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `SF_SESSION_TOKEN` | Yes (at runtime) | — | UUID from the callback; passed as Bearer token |
| `SF_CLIENT_ID` | Yes | — | Connected App consumer key |
| `SF_CLIENT_SECRET` | Yes | — | Connected App consumer secret |
| `SF_LOGIN_URL` | No | `https://test.salesforce.com` | Sandbox or prod login URL |
| `SF_OAUTH_CALLBACK_URL` | No | `http://localhost:8001/auth/salesforce/callback` | Must match Connected App settings |
| `SF_TOKEN_STORE` | No | `file` | `file` or `azure_keyvault` |
| `SF_TOKEN_STORE_FILE` | No | `.salesforce_tokens.json` | Path for the file store |
| `SF_KEY_VAULT_URL` | If KV | — | `https://<vault>.vault.azure.net` |
| `SF_TOKEN_STORE_ENCRYPTION_KEY` | No | — | Fernet key for file encryption |

---

## Salesforce Connected App requirements

The Connected App must have:
- **OAuth scopes**: `api`, `refresh_token` (at minimum)
- **Callback URL**: `http://localhost:8001/auth/salesforce/callback` (dev)
- **Consumer secret** accessible (needed for authorization code exchange)

The digital certificate (`salesforce.crt`) and JWT private key (`salesforce.key`)
are **no longer required** for the authorization code flow.

---

## What did NOT change

| File | Status |
|------|--------|
| `salesforce/repository.py` | Unchanged |
| `salesforce/models.py` | Unchanged |
| `salesforce/tools.yaml` | Unchanged |
| `salesforce/auth.py` (JWT functions) | Unchanged — `authenticate_jwt()` and `authenticate_salesforce()` still exist |
| `agents/salesforce_agent.py` | Unchanged |
| `agents/orchestrator_agent.py` | Unchanged |
| Graph / MSAL auth in `main.py` | Unchanged |
