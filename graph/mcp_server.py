import configparser
import os
import httpx
from urllib.parse import parse_qs, urlencode, urlparse, parse_qsl

from mcp.server.fastmcp import FastMCP, Context
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, RedirectResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from graph.mcp_router import register_graph_tools
from shared.mcp_utils import extract_session_token


mcp = FastMCP("graph", port=8000, host="0.0.0.0")

_config = configparser.ConfigParser()
_config.read(["config.cfg"])
_azure_settings = _config["azure"]

_TENANT_ID = _azure_settings["tenantId"]
_CLIENT_ID = _azure_settings["clientId"]
_GRAPH_SCOPES = _azure_settings["graphUserScopes"].split(" ")
_RESOURCE_URI = os.environ.get("MCP_RESOURCE_URI", "http://localhost:8000")
_BASE_URL = _RESOURCE_URI.removesuffix("/mcp")
_AZURE_BASE = f"https://login.microsoftonline.com/{_TENANT_ID}/oauth2/v2.0"

_SCOPE = f"openid profile offline_access api://{_CLIENT_ID}/access_as_user"


def _rewrite_redirect(uri: str) -> str:
    """127.0.0.1 → localhost zodat Azure AD Web platform het accepteert."""
    return uri.replace("127.0.0.1", "localhost") if uri else uri


async def protected_resource_metadata(_request: Request) -> JSONResponse:
    return JSONResponse({
        "resource": _RESOURCE_URI,
        "authorization_servers": [
            f"https://login.microsoftonline.com/{_TENANT_ID}/v2.0"
        ],
        "bearer_methods_supported": ["header"],
        "scopes_supported": _SCOPE.split(" "),
    })


async def authorization_server_metadata(_request: Request) -> JSONResponse:
    return JSONResponse({
        "issuer": f"https://login.microsoftonline.com/{_TENANT_ID}/v2.0",
        "authorization_endpoint": f"{_BASE_URL}/authorize",
        "token_endpoint": f"{_BASE_URL}/token",
        "response_types_supported": ["code"],
        "code_challenge_methods_supported": ["S256"],
        "scopes_supported": _SCOPE.split(" "),
    })


async def authorize_proxy(request: Request) -> RedirectResponse:
    params = dict(parse_qsl(str(request.url.query)))
    print(f"[authorize_proxy] incoming params: {params}")
    params["scope"] = _SCOPE
    if "redirect_uri" in params:
        params["redirect_uri"] = _rewrite_redirect(params["redirect_uri"])
    url = f"{_AZURE_BASE}/authorize?{urlencode(params)}"
    print(f"[authorize_proxy] redirecting to: {url}")
    return RedirectResponse(url=url)


async def token_proxy(request: Request) -> Response:
    print(f"[token_proxy] HIT")
    body = await request.body()
    print(f"[token_proxy] body: {body[:200]}")
    params = parse_qs(body.decode(), keep_blank_values=True)

    if "scope" not in params or not params["scope"]:
        params["scope"] = [_SCOPE]
    if "redirect_uri" in params:
        params["redirect_uri"] = [_rewrite_redirect(params["redirect_uri"][0])]

    params["client_secret"] = [_azure_settings["clientSecret"]]
    encoded_body = urlencode({k: v[0] for k, v in params.items()})
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_AZURE_BASE}/token",
            content=encoded_body.encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    print(f"[token_proxy] Azure response: {resp.status_code} {resp.text[:500]}")
    return Response(content=resp.content, status_code=resp.status_code,
                    media_type="application/json")


_ROUTES = {
    "/.well-known/oauth-protected-resource": protected_resource_metadata,
    "/.well-known/oauth-authorization-server": authorization_server_metadata,
    "/authorize": authorize_proxy,
    "/token": token_proxy,
}


async def _extract_and_exchange_token(ctx: Context) -> str:
    """Extract the incoming token and exchange it for a Graph token via OBO."""
    # Haal het inkomende token op (api://... scope)
    http_request = ctx.request_context.request
    if http_request is None:
        raise RuntimeError("No HTTP request in context.")
    auth = http_request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise RuntimeError("Missing or invalid Authorization header.")
    assertion = auth[7:]

    # Wissel in voor een Graph token via OBO
    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "client_id": _CLIENT_ID,
        "client_secret": _azure_settings["clientSecret"],
        "assertion": assertion,
        "scope": " ".join(_GRAPH_SCOPES),
        "requested_token_use": "on_behalf_of",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{_AZURE_BASE}/token", data=data)
    if resp.status_code != 200:
        print(f"[OBO] FAILED: {resp.status_code} {resp.text[:500]}")
        raise RuntimeError(f"OBO failed: {resp.text[:200]}")

    print("[OBO] Success — got Graph token")
    return resp.json()["access_token"]


# register_graph_tools(mcp, _azure_settings, _extract_and_exchange_token)
register_graph_tools(mcp, _azure_settings, extract_session_token)



class RoutingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        path = scope["path"]
        print(f"[middleware] {request.method} {path}")

        handler = _ROUTES.get(path)
        if handler:
            response = await handler(request)
            await response(scope, receive, send)
            return

        if path == "/mcp":
            auth = request.headers.get("authorization", "")
            if not auth.lower().startswith("bearer "):
                response = Response(
                    status_code=401,
                    headers={
                        "WWW-Authenticate": (
                            f'Bearer realm="{_RESOURCE_URI}",'
                            f' resource_metadata="{_RESOURCE_URI}/.well-known/oauth-protected-resource"'
                        )
                    },
                )
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)


app = RoutingMiddleware(mcp.streamable_http_app())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)