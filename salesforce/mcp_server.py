import configparser
import os

from mcp.server.fastmcp import FastMCP, Context
from starlette.requests import Request
from starlette.responses import JSONResponse

from salesforce.mcp_router import register_salesforce_tools


mcp = FastMCP("salesforce", port=8001)

_config = configparser.ConfigParser()
_config.read(["config.cfg"])
_sf_settings = _config["salesforce"]

_INSTANCE_URL = os.environ.get("SF_INSTANCE_URL") or _sf_settings.get("loginUrl", "https://login.salesforce.com")
_RESOURCE_URI = os.environ.get("MCP_RESOURCE_URI", "http://localhost:8001")


@mcp.custom_route("/.well-known/oauth-protected-resource", methods=["GET"])
async def protected_resource_metadata(_request: Request) -> JSONResponse:
    return JSONResponse({
        "resource": _RESOURCE_URI,
        "bearer_methods_supported": ["header"],
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
            "Missing or invalid Authorization header."
        )
    return auth[7:]


register_salesforce_tools(mcp, _INSTANCE_URL, _extract_token)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
