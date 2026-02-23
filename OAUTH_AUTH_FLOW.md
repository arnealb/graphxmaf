# OAuth 2.0 Delegation via Azure API Management with MCP and PRM

## Overview

This document describes the authentication architecture used in this project, based on the pattern described in ["Integrating OAuth 2.0 Delegation via Azure API Management with MCP and PRM"](https://bonanipaulchaudhury.medium.com/integrating-oauth-2-0-delegation-via-azure-api-management-with-mcp-and-prm-why-it-matters-f6c993ef591f).

The goal is to replace a hardcoded, process-scoped token (passed via environment variable to a stdio subprocess) with a proper **OAuth 2.0 delegated flow** where each HTTP request carries its own bearer token, validated at the API gateway level.

---

## Why This Change?

### The Old Approach (v1)

```
main.py
  ├── Triggers DeviceCodeCredential (azure-identity)
  ├── User visits a URL, enters a code in a browser
  ├── Token stored in GRAPH_ACCESS_TOKEN env var
  └── Spawns mcp_api_tool.py subprocess (stdio)
       └── Reads token from env var → calls Microsoft Graph
```

**Problems:**
- The token is process-scoped: every request uses the same token
- The MCP server is a subprocess — not accessible over a network
- No standard way for external clients (VS Code, Claude Desktop) to discover auth requirements
- Token is injected out-of-band (env var), not via HTTP headers
- No APIM gateway layer for policy enforcement, rate limiting, or logging

### The New Approach (v2)

```
MCP Client (main.py / VS Code / Claude Desktop)
  ├── GET /.well-known/oauth-protected-resource  ← PRM discovery
  ├── Redirected to Azure AD for login (MSAL / auth code + PKCE)
  ├── Receives access token (JWT) from Azure AD
  └── POST /mcp  (Authorization: Bearer <token>)
        │
        ▼
  Azure API Management (APIM)
  ├── validate-azure-ad-token policy checks the JWT
  ├── Rejects invalid/missing tokens with 401
  └── Forwards valid requests to the MCP server backend
        │
        ▼
  mcp_api_tool.py  (streamable-http MCP server)
  ├── Extracts Bearer token from Authorization header per-request
  ├── Creates a GraphServiceClient scoped to that token
  └── Calls Microsoft Graph on behalf of the authenticated user
        │
        ▼
  Microsoft Graph API
```

---

## Key Components

### 1. Protected Resource Metadata (PRM) — RFC 9728

The MCP server exposes a **public** endpoint:

```
GET /.well-known/oauth-protected-resource
```

Response:
```json
{
  "resource": "https://<apim-instance>.azure-api.net/<mcp-path>",
  "authorization_servers": [
    "https://login.microsoftonline.com/<tenant-id>/v2.0"
  ],
  "bearer_methods_supported": ["header"],
  "scopes_supported": ["User.Read", "Mail.Read"]
}
```

This tells any MCP-aware client:
- Which Azure AD tenant to authenticate with
- Which scopes to request
- That tokens must be passed as `Authorization: Bearer` headers

MCP clients (VS Code, Claude Desktop, custom agents) read this endpoint and automatically initiate the OAuth flow. No hardcoded auth config is needed on the client side.

### 2. OAuth 2.0 Authorization Code + PKCE Flow

Once the client reads the PRM, it performs the standard OAuth 2.0 authorization code flow with PKCE:

```
Client                    Azure AD                  MCP Server (via APIM)
  │                          │                              │
  │── GET /authorize ────────▶│                              │
  │   (response_type=code,    │                              │
  │    code_challenge=...)    │                              │
  │                          │                              │
  │◀─ Redirect (code) ────────│                              │
  │                          │                              │
  │── POST /token ───────────▶│                              │
  │   (code, code_verifier)   │                              │
  │                          │                              │
  │◀─ access_token (JWT) ─────│                              │
  │                          │                              │
  │── POST /mcp ─────────────────────────────────────────────▶│
  │   Authorization: Bearer <access_token>                   │
  │                          │                              │
  │◀─ MCP response ───────────────────────────────────────────│
```

For CLI/agent use (this project's `main.py`), a **device code flow** or **MSAL interactive** is used to acquire the token, since there is no browser callback URI.

### 3. Azure API Management — JWT Validation

APIM sits in front of the MCP server and enforces the following inbound policy:

```xml
<policies>
  <inbound>
    <base />
    <!-- Validate the Azure AD JWT token -->
    <validate-azure-ad-token
        tenant-id="<your-tenant-id>"
        header-name="Authorization"
        failed-validation-httpcode="401"
        failed-validation-error-message="Unauthorized. Access token is missing or invalid.">
      <client-application-ids>
        <application-id><your-client-app-id></application-id>
      </client-application-ids>
    </validate-azure-ad-token>
    <!-- Forward the Authorization header to the backend MCP server -->
    <set-header name="Authorization" exists-action="override">
      <value>@(context.Request.Headers.GetValueOrDefault("Authorization"))</value>
    </set-header>
  </inbound>
  <backend>
    <base />
  </backend>
  <outbound>
    <base />
  </outbound>
</policies>
```

APIM rejects any request without a valid Azure AD JWT. Valid requests are forwarded to the MCP server with the `Authorization` header intact.

### 4. MCP Server — Per-Request Token Extraction

The MCP server (`mcp_api_tool.py`) now:

- Runs as a **Streamable HTTP** server (not a stdio subprocess)
- Reads the `Authorization: Bearer <token>` header from each incoming MCP request via the FastMCP `Context` object
- Creates a `GraphServiceClient` scoped to that token **for each request**
- This enables multi-user scenarios: different users can connect simultaneously with different tokens

```python
@mcp.tool()
async def whoami(ctx: Context) -> str:
    token = _extract_token(ctx)        # reads from ctx.request_context.request.headers
    g = _make_graph_client(token)      # creates per-request GraphServiceClient
    user = await g.get_user()
    return f"Name: {user.display_name}"
```

---

## Step-by-Step Authentication Flow

```
Step 1: Client discovers auth requirements
─────────────────────────────────────────
Client → GET /.well-known/oauth-protected-resource
Server → { "authorization_servers": [...], "scopes_supported": [...] }

Step 2: Client acquires a token from Azure AD
──────────────────────────────────────────────
Client → Azure AD: Authorization Code + PKCE (or Device Code for CLI)
Azure AD → Client: access_token (JWT signed by Azure AD)

Step 3: Client calls the MCP server via APIM
─────────────────────────────────────────────
Client → APIM → POST /mcp
         Headers: { Authorization: "Bearer eyJ0eXAi..." }
         Body: { "method": "tools/call", "params": { "name": "whoami" } }

Step 4: APIM validates the JWT
──────────────────────────────
APIM checks:
  - Token is signed by Azure AD (checks JWKS endpoint)
  - Token audience matches the registered app
  - Token is not expired
  - Token issuer matches the configured tenant

If invalid → 401 Unauthorized (never reaches the MCP server)
If valid   → request forwarded to MCP server backend

Step 5: MCP server extracts the token and calls Graph
──────────────────────────────────────────────────────
MCP server reads Authorization header from the HTTP request context
Creates a GraphServiceClient with the bearer token
Calls Microsoft Graph on behalf of the authenticated user
Returns result to the MCP client
```

---

## Azure AD App Registration Requirements

For this to work, you need an Azure AD app registration configured as follows:

| Setting | Value |
|---|---|
| App type | Public client (for device code / interactive) |
| Redirect URI | `http://localhost` (for local dev) or your APIM callback URL |
| API permissions | `User.Read`, `Mail.Read` (delegated) |
| Token type | Access tokens (not ID tokens) |
| Supported account types | Accounts in this organizational directory only |

The `clientId` and `tenantId` in `config.cfg` must match this app registration.

---

## Local Development (Without APIM)

During local development, the MCP server can run without APIM. In this case:

1. Start the MCP server: `python mcp_api_tool.py`  (listens on `http://localhost:8000/mcp`)
2. Start the agent:  `python main.py`  (authenticates with MSAL, connects to the local MCP server)

The token is still validated indirectly — if the token is invalid, Microsoft Graph will return 401 when the tool tries to call it.

For production, deploy the MCP server behind APIM and update `mcpServerUrl` in `config.cfg` to the APIM endpoint.

---

## Configuration

`config.cfg`:
```ini
[azure]
clientId     = <your-azure-ad-app-client-id>
tenantId     = <your-azure-ad-tenant-id>
graphUserScopes = User.Read Mail.Read
mcpServerUrl = http://localhost:8000/mcp    ; or your APIM URL in production
```

Environment variables (optional overrides):
```bash
MCP_RESOURCE_URI=https://<apim>.azure-api.net/<path>  # used in PRM response
```

---

## Security Properties

| Property | Old (v1) | New (v2) |
|---|---|---|
| Token scope | Process-wide (shared by all requests) | Per-request (each HTTP call carries its own token) |
| Transport | stdio (local subprocess only) | Streamable HTTP (network-accessible) |
| Auth enforcement | None (token assumed valid) | APIM `validate-azure-ad-token` policy |
| Multi-user support | No | Yes |
| Auth discovery | Manual configuration | Automatic via PRM (`/.well-known/oauth-protected-resource`) |
| Token storage | Environment variable | MSAL token cache (`~/.token_cache.bin`) |
| Standard compliance | Proprietary | OAuth 2.1 + RFC 9728 (PRM) |

---

## References

- [OAuth 2.0 Protected Resource Metadata — RFC 9728](https://datatracker.ietf.org/doc/rfc9728/)
- [MCP Authorization Specification](https://modelcontextprotocol.io/specification/draft/basic/authorization)
- [Secure access to MCP servers in Azure API Management](https://learn.microsoft.com/en-us/azure/api-management/secure-mcp-servers)
- [validate-azure-ad-token APIM policy](https://learn.microsoft.com/en-us/azure/api-management/validate-azure-ad-token-policy)
- [MSAL for Python](https://learn.microsoft.com/en-us/entra/msal/python/)
