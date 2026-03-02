import configparser
import os

from mcp.server.fastmcp import FastMCP, Context
from starlette.requests import Request
from starlette.responses import JSONResponse

from graph.mcp_router import register_graph_tools


mcp = FastMCP("graph", port=8000)

_config = configparser.ConfigParser()
_config.read(["config.cfg"])
_azure_settings = _config["azure"]

_TENANT_ID = _azure_settings["tenantId"]
_GRAPH_SCOPES = _azure_settings["graphUserScopes"].split(" ")
_RESOURCE_URI = os.environ.get("MCP_RESOURCE_URI", "http://localhost:8000")


@mcp.custom_route("/.well-known/oauth-protected-resource", methods=["GET"])
async def protected_resource_metadata(_request: Request) -> JSONResponse:
    return JSONResponse({
        "resource": _RESOURCE_URI,
        "authorization_servers": [
            f"https://login.microsoftonline.com/{_TENANT_ID}/v2.0"
        ],
        "bearer_methods_supported": ["header"],
        "scopes_supported": _GRAPH_SCOPES,
    })


def _extract_token(ctx: Context) -> str:
    http_request = ctx.request_context.request
    if http_request is None:
        raise RuntimeError(
            "No HTTP request in context. "
            "This tool requires streamable-http transport."
        )
    auth = http_request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise RuntimeError(
            "Missing or invalid Authorization header. "
            "Authenticate via the authorization server listed at "
            f"{_RESOURCE_URI}/.well-known/oauth-protected-resource"
        )
    return auth[7:]


register_graph_tools(mcp, _azure_settings, _extract_token)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
