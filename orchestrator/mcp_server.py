"""
Orchestrator MCP Server

Exposes a single `ask` tool to Microsoft 365 Copilot.
On each call it:
  1. Extracts the Copilot bearer token and exchanges it for a Graph token via OBO.
  2. Creates a per-request GraphAgent (MCPStreamableHTTPTool → deployed graph-mcp).
  3. Reuses the shared SmartSalesAgent (initialised lazily on first request).
  4. Reuses the shared SalesforceAgent (initialised lazily on first request).
  5. Runs an OrchestratorAgent that routes to whichever sub-agents are needed and
     synthesises the results into one answer.

OAuth proxy routes (/authorize, /token, /.well-known/*) are wired identically to
the graph-mcp server so Copilot's OAuth flow works unchanged.
"""

import configparser
import logging
import os
from typing import Annotated
from urllib.parse import parse_qs, parse_qsl, urlencode, urlparse

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP, Context
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

from agent_framework import Agent, FunctionTool, MCPStreamableHTTPTool
from agent_framework.azure import AzureOpenAIChatClient

from agents.graph_agent import create_graph_agent
from agents.salesforce_agent import create_salesforce_agent
from agents.smartsales_agent import create_smartsales_agent

load_dotenv()
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")

# ── Config ────────────────────────────────────────────────────────────────────

_config = configparser.ConfigParser()
_config.read(["config.cfg"])
_azure = _config["azure"]
_orch = _config["orchestrator"] if _config.has_section("orchestrator") else {}
_ss_cfg = _config["smartsales"] if _config.has_section("smartsales") else {}

_TENANT_ID = _azure["tenantId"]
_CLIENT_ID = _orch.get("clientId", os.environ.get("ORCH_CLIENT_ID", ""))
_CLIENT_SECRET = _orch.get("clientSecret", os.environ.get("ORCH_CLIENT_SECRET", ""))
_GRAPH_SCOPES = _azure["graphUserScopes"].split()

_RESOURCE_URI = os.environ.get("MCP_RESOURCE_URI", "http://localhost:8003")
_BASE_URL = _RESOURCE_URI.removesuffix("/mcp")
_AZURE_BASE = f"https://login.microsoftonline.com/{_TENANT_ID}/oauth2/v2.0"

# Scope Copilot requests — tied to this orchestrator's App Registration.
_SCOPE = f"openid profile offline_access api://{_CLIENT_ID}/access_as_user"

# URLs of the already-deployed MCP servers.
_GRAPH_MCP_URL = _orch.get(
    "graphMcpUrl",
    os.environ.get(
        "GRAPH_MCP_URL",
        "https://graph-mcp.whitemushroom-38caf70a.swedencentral.azurecontainerapps.io/mcp",
    ),
)
log.warning("[config] GRAPH_MCP_URL = %s", _GRAPH_MCP_URL)

_SS_MCP_URL = os.environ.get(
    "SS_MCP_URL",
    _ss_cfg.get("mcpServerUrl", "http://localhost:8002/mcp"),
)
log.warning("[config] SS_MCP_URL = %s", _SS_MCP_URL)

_SF_MCP_URL = os.environ.get(
    "SF_MCP_URL",
    _config["salesforce"].get("mcpServerUrl", "http://localhost:8001/mcp")
    if _config.has_section("salesforce")
    else "http://localhost:8001/mcp",
)
log.warning("[config] SF_MCP_URL = %s", _SF_MCP_URL)

# Azure OpenAI (same env vars as the rest of the project).
_AOAI_DEPLOYMENT = os.environ.get("deployment", "")
_AOAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
_AOAI_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "")
_AOAI_VERSION = "2024-12-01-preview"

# ── FastMCP ───────────────────────────────────────────────────────────────────

mcp = FastMCP("orchestrator", port=8003, host="0.0.0.0")

# ── Shared agent state (initialised lazily on first request) ──────────────────

_ss_agent: Agent | None = None
_sf_agent: Agent | None = None
_sf_login_url: str | None = None


def _aoai_client() -> AzureOpenAIChatClient:
    return AzureOpenAIChatClient(
        deployment_name=_AOAI_DEPLOYMENT,
        endpoint=_AOAI_ENDPOINT,
        api_key=_AOAI_KEY,
        api_version=_AOAI_VERSION,
    )


# ── SmartSales init ──────────────────────────────────────────────────────────

async def _init_smartsales() -> None:
    global _ss_agent
    try:
        parsed = urlparse(_SS_MCP_URL)
        base = f"{parsed.scheme}://{parsed.netloc}"
        log.warning("[init_smartsales] GET %s/auth/smartsales/session", base)
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{base}/auth/smartsales/session", timeout=20)

        log.warning("[init_smartsales] Response: %s %s", resp.status_code, resp.text[:200])

        if resp.status_code != 200:
            log.warning("[init_smartsales] FAILED — skipping SmartSales")
            return

        session_token = resp.json()["session_token"]
        log.warning("[init_smartsales] Session ready: %s", session_token)

        ss_http = httpx.AsyncClient(headers={"Authorization": f"Bearer {session_token}"})
        ss_mcp = MCPStreamableHTTPTool(name="smartsales", url=_SS_MCP_URL, http_client=ss_http)

        _ss_agent = create_smartsales_agent(ss_mcp)
        log.warning("[init_smartsales] SmartSalesAgent created successfully")
    except Exception as e:
        log.warning("[init_smartsales] EXCEPTION: %s", e)
        _ss_agent = None


# ── Salesforce init ──────────────────────────────────────────────────────────

async def _init_salesforce() -> None:
    global _sf_agent
    try:
        parsed = urlparse(_SF_MCP_URL)
        base = f"{parsed.scheme}://{parsed.netloc}"
        log.warning("[init_salesforce] GET %s/auth/salesforce/session", base)
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{base}/auth/salesforce/session", timeout=20)

        log.warning("[init_salesforce] Response: %s %s", resp.status_code, resp.text[:200])

        if resp.status_code != 200:
            global _sf_login_url
            parsed = urlparse(_SF_MCP_URL)
            _sf_login_url = f"{parsed.scheme}://{parsed.netloc}/auth/salesforce/login"
            log.warning("[init_salesforce] No session — login at %s", _sf_login_url)
            return

        session_token = resp.json()["session_token"]
        log.warning("[init_salesforce] Session ready: %s", session_token)

        sf_http = httpx.AsyncClient(headers={"Authorization": f"Bearer {session_token}"})
        sf_mcp = MCPStreamableHTTPTool(name="salesforce", url=_SF_MCP_URL, http_client=sf_http)

        _sf_agent = create_salesforce_agent(sf_mcp)
        log.warning("[init_salesforce] SalesforceAgent created successfully")
    except Exception as e:
        log.warning("[init_salesforce] EXCEPTION: %s", e)
        _sf_agent = None


# ── Per-request Graph agent ───────────────────────────────────────────────────

def _build_graph_agent(graph_token: str) -> Agent:
    """Create a GraphAgent with a fresh OBO-derived token for this request."""
    graph_http = httpx.AsyncClient(headers={"Authorization": f"Bearer {graph_token}"})
    graph_mcp = MCPStreamableHTTPTool(name="graph", url=_GRAPH_MCP_URL, http_client=graph_http)
    return create_graph_agent(graph_mcp)


# ── Orchestrator agent ────────────────────────────────────────────────────────

def _build_orchestrator(
    graph_agent: Agent,
    ss_agent: Agent | None,
    sf_agent: Agent | None,
    sf_status:str=""
) -> Agent:
    """Assemble the orchestrator with FunctionTools wrapping each sub-agent."""

    async def ask_graph_agent(
        query: Annotated[str, "The full question to send to the Microsoft Graph agent"],
    ) -> str:
        response = await graph_agent.run(query)
        return response.text or "(no response from GraphAgent)"

    async def ask_smartsales_agent(
        query: Annotated[str, "The full question to send to the SmartSales agent"],
    ) -> str:
        global _ss_agent
        response = await ss_agent.run(query)
        result = response.text or ""
        if "SESSION_ERROR:" in result:
            _ss_agent = None
            await _init_smartsales()
            if _ss_agent is not None:
                response = await _ss_agent.run(query)
                return response.text or ""
            return "(SmartSales kon niet opnieuw worden geïnitialiseerd)"
        return result

    async def ask_salesforce_agent(
        query: Annotated[str, "The full question to send to the Salesforce agent"],
    ) -> str:
        global _sf_agent
        response = await sf_agent.run(query)
        result = response.text or ""
        if "SESSION_ERROR:" in result:
            _sf_agent = None
            return "(Salesforce session expired — retrying on next request)"
        return result

    # Graph is always available.
    tools = [
        FunctionTool(
            name="ask_graph_agent",
            description=(
                "Route a question to the Microsoft Graph agent. "
                "Use this for anything related to emails, OneDrive files, calendar events, "
                "contacts, or identifying the current Microsoft 365 user."
            ),
            func=ask_graph_agent,
            approval_mode="never_require",
        ),
    ]

    # SmartSales is optional.
    if ss_agent is not None:
        tools.append(
            FunctionTool(
                name="ask_smartsales_agent",
                description=(
                    "Route a question to the SmartSales agent. "
                    "Use this for anything related to SmartSales locations, catalog items, "
                    "or orders: searching, listing, and retrieving by name, city, country, or uid."
                ),
                func=ask_smartsales_agent,
                approval_mode="never_require",
            )
        )

    # Salesforce is optional.
    if sf_agent is not None:
        tools.append(
            FunctionTool(
                name="ask_salesforce_agent",
                description=(
                    "Route a question to the Salesforce agent. "
                    "Use this for anything related to Salesforce CRM data: "
                    "accounts, leads, contacts, opportunities, and campaigns."
                ),
                func=ask_salesforce_agent,
                approval_mode="never_require",
            )
        )

    return Agent(
        client=_aoai_client(),
        name="OrchestratorAgent",
        description="Routes queries to Graph, SmartSales, or Salesforce sub-agents and combines their results",
        instructions=f"""
            You are a central orchestrator that coordinates three specialised agents:

            1. ask_graph_agent — handles everything Microsoft 365:
               emails, OneDrive files, calendar events, contacts, user identity.
            2. ask_smartsales_agent — handles SmartSales data:
               locations, catalog items, and orders.
            3. ask_salesforce_agent — handles Salesforce CRM data:
               accounts, leads, contacts, opportunities, and campaigns.

            ROUTING RULES
            - Microsoft 365 / Office data → ask_graph_agent
            - SmartSales data             → ask_smartsales_agent
            - Salesforce CRM data         → ask_salesforce_agent
            - Query spans multiple systems → call relevant tools, then combine

            STRICT TOOL SELECTION RULES
            - Only call a tool when the user's request explicitly requires it.
            - Pass the user's original question (rephrased if needed) to the sub-agent.
            - Never guess or fabricate data — only report what sub-agents return.
            - If a single tool call returns sufficient information, do NOT call the other tools.

            SUB-AGENT RESPONSES
            - Sub-agents return raw JSON from their tool calls, not prose.
            - Parse the structured fields (id, name, email, etc.) to answer the user.

            COMBINING RESULTS
            - When multiple agents are called, synthesise into one coherent answer.
            - Clearly indicate the source (e.g. "From Microsoft 365: …" / "From SmartSales: …" / "From Salesforce: …").
            - Present a unified, structured summary — do not concatenate raw outputs.

            OUTPUT
            - Be concise and factual.
            - Use bullet points or sections when presenting data from multiple sources.
            - Present dates in a human-readable format.
            {sf_status}
        """,
        tools=tools,
    )


# ── The one MCP tool exposed to Copilot ──────────────────────────────────────

@mcp.tool(
    name="ask",
    description=(
        "Ask the multi-agent system a question. "
        "Handles Microsoft 365 data (emails, calendar, files, contacts), "
        "SmartSales data (locations, catalog items, orders), "
        "and Salesforce CRM data (accounts, leads, contacts, opportunities)."
    ),
)
async def ask(ctx: Context, query: str) -> str:
    global _ss_agent, _sf_agent

    # 1. Extract the incoming Copilot token.
    http_request = ctx.request_context.request
    if http_request is None:
        raise RuntimeError("No HTTP request in context.")
    auth = http_request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise RuntimeError("Missing or invalid Authorization header.")
    assertion = auth[7:]

    # 2. OBO exchange → Graph token.
    graph_token = await _obo_exchange(assertion)

    # 3. Lazy init SmartSales (once).
    if _ss_agent is None:
        log.warning("[ask] SmartSales not initialized yet — trying now")
        await _init_smartsales()

    # 4. Lazy init Salesforce (once).
    if _sf_agent is None:
        log.warning("[ask] Salesforce not initialized yet — trying now")
        await _init_salesforce()

    # If Salesforce still unavailable, inject login hint into query context.
    sf_status = ""
    if _sf_agent is None and _sf_login_url is not None:
        sf_status = f"\n\nNOTE: Salesforce is not authenticated. If the user asks for Salesforce data, respond with: 'Salesforce is currently not authenticated. Please log in first at: {_sf_login_url}'"

    # 5. Build per-request GraphAgent.
    graph_agent = _build_graph_agent(graph_token)

    # 6. Build orchestrator with available agents.
    if _ss_agent is not None or _sf_agent is not None or sf_status:
        # ook als sf_status niet leeg is -> aka user moet inloggen -> 
        orchestrator = _build_orchestrator(graph_agent, _ss_agent, _sf_agent, sf_status)
    else:
        log.warning("[ask] No sub-agents available — using GraphAgent only")
        orchestrator = graph_agent

    # 7. Run.
    log.info("[ask] query=%r", query[:120])
    response = await orchestrator.run(query)
    result = response.text or "(no response)"
    log.info("[ask] done, response length=%d", len(result))
    return result


# ── OBO helper ────────────────────────────────────────────────────────────────

async def _obo_exchange(assertion: str) -> str:
    """Exchange the incoming api://... token for a Graph-scoped token via OBO."""
    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "client_id": _CLIENT_ID,
        "client_secret": _CLIENT_SECRET,
        "assertion": assertion,
        "scope": " ".join(_GRAPH_SCOPES),
        "requested_token_use": "on_behalf_of",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{_AZURE_BASE}/token", data=data)
    if resp.status_code != 200:
        log.error("[OBO] failed: %s %s", resp.status_code, resp.text[:300])
        raise RuntimeError(f"OBO exchange failed: {resp.text[:200]}")
    log.info("[OBO] success")
    return resp.json()["access_token"]


# ── OAuth proxy routes (identical pattern to graph-mcp) ──────────────────────

def _rewrite_redirect(uri: str) -> str:
    return uri.replace("127.0.0.1", "localhost") if uri else uri


async def protected_resource_metadata(_request: Request) -> JSONResponse:
    return JSONResponse({
        "resource": _RESOURCE_URI,
        "authorization_servers": [
            f"https://login.microsoftonline.com/{_TENANT_ID}/v2.0"
        ],
        "bearer_methods_supported": ["header"],
        "scopes_supported": _SCOPE.split(),
    })


async def authorization_server_metadata(_request: Request) -> JSONResponse:
    return JSONResponse({
        "issuer": f"https://login.microsoftonline.com/{_TENANT_ID}/v2.0",
        "authorization_endpoint": f"{_BASE_URL}/authorize",
        "token_endpoint": f"{_BASE_URL}/token",
        "response_types_supported": ["code"],
        "code_challenge_methods_supported": ["S256"],
        "scopes_supported": _SCOPE.split(),
    })


async def authorize_proxy(request: Request) -> RedirectResponse:
    params = dict(parse_qsl(str(request.url.query)))
    log.info("[authorize_proxy] params=%s", params)
    params["scope"] = _SCOPE
    if "redirect_uri" in params:
        params["redirect_uri"] = _rewrite_redirect(params["redirect_uri"])
    url = f"{_AZURE_BASE}/authorize?{urlencode(params)}"
    log.info("[authorize_proxy] redirecting to: %s", url)
    return RedirectResponse(url=url)


async def token_proxy(request: Request) -> Response:
    log.info("[token_proxy] HIT")
    body = await request.body()
    log.info("[token_proxy] body: %s", body[:200])
    params = parse_qs(body.decode(), keep_blank_values=True)

    if "scope" not in params or not params["scope"]:
        params["scope"] = [_SCOPE]
    if "redirect_uri" in params:
        params["redirect_uri"] = [_rewrite_redirect(params["redirect_uri"][0])]
    params["client_secret"] = [_CLIENT_SECRET]

    encoded_body = urlencode({k: v[0] for k, v in params.items()})
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_AZURE_BASE}/token",
            content=encoded_body.encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    log.info("[token_proxy] Azure response: %s %s", resp.status_code, resp.text[:300])
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type="application/json",
    )


_ROUTES = {
    "/.well-known/oauth-protected-resource": protected_resource_metadata,
    "/.well-known/oauth-authorization-server": authorization_server_metadata,
    "/authorize": authorize_proxy,
    "/token": token_proxy,
}


# ── Middleware ────────────────────────────────────────────────────────────────

class RoutingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        log.debug("[middleware] %s %s", request.method, request.url.path)
        handler = _ROUTES.get(request.url.path)
        if handler:
            return await handler(request)
        if request.url.path == "/mcp":
            auth = request.headers.get("authorization", "")
            if not auth.lower().startswith("bearer "):
                return Response(
                    status_code=401,
                    headers={
                        "WWW-Authenticate": (
                            f'Bearer realm="{_RESOURCE_URI}",'
                            f' resource_metadata="{_RESOURCE_URI}/.well-known/oauth-protected-resource"'
                        )
                    },
                )
        return await call_next(request)


# ── App ───────────────────────────────────────────────────────────────────────

app = mcp.streamable_http_app()
app.add_middleware(RoutingMiddleware)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)