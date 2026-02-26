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

_agents: dict[str, GraphAgent] = {}


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


# def _make_agent(token: str) -> GraphAgent:
#     repo = GraphRepository(_azure_settings, credential=StaticTokenCredential(token))
#     return GraphAgent(repo)

def _make_agent(token: str) -> GraphAgent:
    if token not in _agents:
        repo = GraphRepository(_azure_settings, credential=StaticTokenCredential(token))
        _agents[token] = GraphAgent(repo)
    return _agents[token]

@mcp.tool()
async def whoami(ctx: Context) -> str:
    token = _extract_token(ctx)
    agent = _make_agent(token)
    return await agent.whoami()

@mcp.tool()
async def findpeople(ctx: Context, name: str) -> str:
    token = _extract_token(ctx)
    agent = _make_agent(token)
    return await agent.find_people(name)

@mcp.tool()
async def list_email(ctx: Context) -> str:
    token = _extract_token(ctx)
    agent = _make_agent(token)
    return await agent.list_email()

@mcp.tool()
async def search_email(
    ctx: Context,
    sender: str | None = None,
    subject: str | None = None,
    received_after: str | None = None,
    received_before: str | None = None,
) -> str:
    token = _extract_token(ctx)
    agent = _make_agent(token)

    print(f"search emails met: sender={sender!r}, subject={subject!r}, received_after={received_after!r}, received_before={received_before!r}")

    return await agent.search_emails(
        sender=sender,
        subject=subject,
        received_before=received_before,
        received_after=received_after,
    )

# --------------------------------------------------------------- 
@mcp.tool()
async def search_files(ctx: Context, query: str, drive_id: str | None = None, folder_id: str = "root") -> str:
    token = _extract_token(ctx)
    agent = _make_agent(token)
    return await agent.search_files(query=query, drive_id=drive_id, folder_id=folder_id)

# @mcp.tool()
# async def list_files(ctx: Context) -> str:
#     token = _extract_token(ctx)
#     agent = _make_agent(token)
#     return await agent.list_files()

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



if __name__ == "__main__":
    mcp.run(transport="streamable-http")
