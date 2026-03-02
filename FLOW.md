# Application Flow

## Overview

Two processes run side by side. `main.py` starts both and connects them.

```
┌─────────────────────────────────────────────────────────┐
│  Process 1 – main.py (agent host)          port 8080    │
│  Browser UI  →  Agent (LLM)  →  MCP client             │
└──────────────────────┬──────────────────────────────────┘
                       │  HTTP  (Bearer token)
┌──────────────────────▼──────────────────────────────────┐
│  Process 2 – mcp_api_tool.py (MCP server)  port 8000    │
│  FastMCP  →  tool handlers  →  GraphRepository.raw()    │
└──────────────────────┬──────────────────────────────────┘
                       │  HTTPS  (Bearer token)
                 Microsoft Graph API
```

---

## Startup sequence (`main.py`)

```
1. Read config.cfg  →  clientId, tenantId, scopes, mcpServerUrl

2. MSAL authenticate
   └─ check .token_cache.bin for a cached token
   └─ if none → device code flow (user visits URL, enters code)
   └─ save token back to .token_cache.bin
   └─ returns: access_token (JWT, delegated, user context)

3. If mcpServerUrl is localhost:
   └─ spawn  mcp_api_tool.py  as a subprocess
   └─ poll port 8000 until ready (up to 15 s)

4. Build httpx.AsyncClient with  Authorization: Bearer <token>
   (this client is reused for every MCP call)

5. Wrap client in MCPStreamableHTTPTool("graph", url=mcpServerUrl)

6. create_graph_agent(graph_mcp)  →  Agent with LLM + MCP tool

7. agent_framework.devui.serve(port=8080, auto_open=True)
   └─ opens browser, blocks until user closes
   └─ on exit: terminate MCP server subprocess
```

---

## MCP server startup (`mcp_api_tool.py`)

```
1. FastMCP("graph", port=8000)  →  mcp instance

2. Read config.cfg  →  _azure_settings, _TENANT_ID, _GRAPH_SCOPES

3. Register custom route:
   GET /.well-known/oauth-protected-resource
   └─ returns PRM JSON (auth server URL, supported scopes)
      so MCP-aware clients know how to authenticate

4. Define _extract_token(ctx)
   └─ reads ctx.request_context.request.headers["authorization"]
   └─ strips "Bearer " prefix and returns the raw JWT

5. register_graph_tools(mcp, _azure_settings, _extract_token)
   └─ see section below

6. Register custom route:
   POST /mcp-json  (REST bridge, see section below)

7. mcp.run(transport="streamable-http")
   └─ FastMCP builds a Starlette app
   └─ uvicorn serves it on port 8000
   └─ MCP protocol endpoint:  POST/GET /mcp
```

---

## Tool registration (`graph/mcp_router.py` + `graph/endpoints.yaml`)

`register_graph_tools` is called once at startup. It reads `endpoints.yaml` and
registers one FastMCP tool per entry.

```
endpoints.yaml  (9 entries)
│
└─ for each endpoint:
     tool_name = "graph-{ep.name}"
     │
     ├─ make_handler(ep)  creates an async handler closure
     │   ├─ real signature:  handler(ctx: Context, **kwargs)
     │   └─ __signature__ override:
     │       ctx: Context
     │       + one str param per pathParam   (required)
     │       + one str|None param per query  (optional, default=None)
     │
     └─ mcp.tool(name=tool_name)(handler)
         └─ FastMCP introspects __signature__ via inspect.signature()
         └─ builds a Pydantic model with individual named fields
         └─ stores Tool in mcp._tool_manager._tools[tool_name]
```

Why `__signature__` is necessary: FastMCP's argument validation uses
`inspect.signature()` to generate the Pydantic model. Without it, `**kwargs`
collapses to a single field `kwargs: Any` and the LLM would need to pass
`{"kwargs": {...}}` instead of flat params.

### Registered tools

| Tool name              | Path                                  | Params                          |
|------------------------|---------------------------------------|---------------------------------|
| `graph-whoami`         | `GET /me`                             | select                          |
| `graph-findpeople`     | `GET /users`                          | filter, select, top             |
| `graph-list-mail-messages` | `GET /me/messages`              | filter, search, select, top, orderby |
| `graph-get-mail-message`   | `GET /me/messages/{message_id}` | message_id *(path)*             |
| `graph-list-events`    | `GET /me/events`                      | filter, select, top, orderby    |
| `graph-search-events`  | `GET /me/events`                      | filter, select, top, orderby    |
| `graph-list-files`     | `GET /me/drive/root/children`         | filter, select, top, orderby    |
| `graph-search-files`   | `GET /me/drive/root/search(q='{q}')` | q *(path)*, select, top         |
| `graph-list-contacts`  | `GET /me/contacts`                    | filter, select, top, orderby    |

---

## Request flow — AI agent path

This is the path taken when a user types a question in the browser.

```
User types: "show emails from Arne"
│
▼
agent_framework Agent  (port 8080)
│  LLM decides tool + params:
│    tool = "graph-list-mail-messages"
│    params = { "search": "\"arne\"" }
▼
MCPStreamableHTTPTool
│  POST http://localhost:8000/mcp
│  headers: { Authorization: Bearer <token> }
│  body: MCP JSON-RPC  tools/call  { name, arguments }
▼
FastMCP  (mcp_api_tool.py)
│  validates MCP protocol message
│  calls mcp._tool_manager.call_tool(name, arguments, context)
│    └─ context.request_context.request = the incoming HTTP request
▼
tool handler  (closure from mcp_router.py)
│  _extract_token(ctx)
│    └─ reads Authorization header from the HTTP request
│    └─ returns the Bearer JWT
│  get_repo(token, azure_settings)
│    └─ cache hit: reuse existing GraphRepository for this token
│    └─ cache miss: GraphRepository(StaticTokenCredential(token))
│  build path  (substitute pathParams, URL-encode values)
│  build query dict  (prefix each key with $)
│    └─ quote_odata_datetimes: wraps bare ISO timestamps in single quotes
▼
GraphRepository.raw(path, method, query)
│  get_user_token()  →  calls StaticTokenCredential.get_token()
│                        returns the same JWT wrapped in AccessToken
│  httpx.AsyncClient.request(
│    method,
│    "https://graph.microsoft.com/v1.0" + path,
│    params=query,
│    headers={ Authorization: Bearer <token> }
│  )
▼
Microsoft Graph API
│  returns JSON
▼
str(data)  →  back up the call stack  →  LLM  →  browser UI
```

---

## Request flow — REST bridge path (`/mcp-json`)

A direct HTTP call that bypasses the LLM, useful for testing.

```
POST http://localhost:8000/mcp-json
Authorization: Bearer <token>
{ "tool": "graph-list-mail-messages", "params": { "search": "\"arne\"" } }
│
▼
mcp_json_bridge  (custom Starlette route)
│  parse JSON body  →  tool_name, params
│  mcp._tool_manager.get_tool(tool_name)
│    └─ returns Tool or 404 with known_tools list
│  build RequestContext(
│    request_id = "bridge",
│    session    = None,         ← safe: handlers never use session
│    request    = starlette_request   ← carries the Authorization header
│  )
│  ctx = Context(request_context=rc, fastmcp=mcp)
│  mcp._tool_manager.call_tool(tool_name, params, context=ctx)
▼
same handler path as above  (token extraction → repo.raw → Graph API)
▼
JSONResponse({ "result": "..." })
```

---

## Authentication details

### Token flow

```
User's browser                  Azure AD                   App
      │                              │                       │
      │  ← device code flow ────────│──────── MSAL ────────▶│
      │    visit URL + enter code    │                       │
      │ ─────────────────────────▶  │                       │
      │              access_token ──│──────────────────────▶│
                                                            stored in
                                                         .token_cache.bin
```

The same `access_token` is used for two things:
1. Passed as `Authorization: Bearer` header from `main.py` → MCP server
2. Passed through the MCP server → Graph API (the server extracts it from the
   incoming request and forwards it unchanged)

This is **delegated auth**: the token represents the end user, not the app.
Graph API enforces the user's own permissions.

### Per-request token handling

`GraphRepository` is cached by token string. Each unique token gets its own
`GraphRepository` instance wrapping a `StaticTokenCredential`. When `raw()` is
called, `get_user_token()` returns the same token via `StaticTokenCredential`,
which simply re-wraps it as an `AccessToken` with a 1-hour expiry hint.

---

## File map

```
main.py                 entry point: auth, process management, agent host
mcp_api_tool.py         FastMCP server: routes, token extraction, bridge
graph/
  endpoints.yaml        declarative tool definitions (9 endpoints)
  mcp_router.py         reads YAML → registers FastMCP tools
  repository.py         GraphRepository.raw() – raw httpx Graph calls
auth/
  token_credential.py   StaticTokenCredential: wraps a JWT as azure credential
agent.py                LLM agent definition + tool instructions
config.cfg              Azure app registration + scopes + server URL
```
