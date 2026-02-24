import configparser
import os
import time

from mcp.server.fastmcp import FastMCP, Context
from starlette.requests import Request
from starlette.responses import JSONResponse
from azure.core.credentials import AccessToken

from graph.repository import GraphRepository
from auth.token_credential import StaticTokenCredential, _make_graph_client

from graph.repository import GraphRepository
from auth.token_credential import StaticTokenCredential
from entities.graph_agent import GraphAgent


mcp = FastMCP("graph", port=8000)

_config = configparser.ConfigParser()
_config.read(["config.cfg"])
_azure_settings = _config["azure"]

_TENANT_ID = _azure_settings["tenantId"]
_GRAPH_SCOPES = _azure_settings["graphUserScopes"].split(" ")
_RESOURCE_URI = os.environ.get("MCP_RESOURCE_URI", "http://localhost:8000")


# prm shit -> hoe moeten user authenticeren
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


# gewoon fancy way om bearer token uit http req te halen -> me foutmeldingen
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


def _make_agent(token: str) -> GraphAgent:
    repo = GraphRepository(_azure_settings, credential=StaticTokenCredential(token))
    return GraphAgent(repo)

@mcp.tool()
async def whoami(ctx: Context) -> str:
    token = _extract_token(ctx)
    agent = _make_agent(token)
    return await agent.whoami()

@mcp.tool()
async def list_files(ctx: Context) -> str:
    token = _extract_token(ctx)
    agent = _make_agent(token)
    return await agent.list_files()

@mcp.tool()
async def list_contacts(ctx: Context) -> str:
    token = _extract_token(ctx)
    agent = _make_agent(token)
    return await agent.list_contacts()

@mcp.tool()
async def list_calendar(ctx: Context) -> str:
    token = _extract_token(ctx)
    agent = _make_agent(token)
    return await agent.list_calendar()

@mcp.tool()
async def read_email(ctx: Context, message_id: str) -> str:
    token = _extract_token(ctx)
    agent = _make_agent(token)
    return await agent.read_email(message_id)

@mcp.tool()
async def list_email(ctx: Context) -> str:
    token = _extract_token(ctx)
    agent = _make_agent(token)
    return await agent.list_email()

@mcp.tool()
async def unified_search(
    ctx: Context,
    query: str,
    entities: list[str] = ["message", "event", "driveItem", "person"],
) -> str:
    token = _extract_token(ctx)
    agent = _make_agent(token)
    return await agent.unified_search(query=query, entities=entities)

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
