import configparser
import os
import time

from mcp.server.fastmcp import FastMCP, Context
from starlette.requests import Request
from starlette.responses import JSONResponse
from azure.core.credentials import AccessToken

from graph_tutorial import Graph
from tokencred import StaticTokenCredential, _make_graph_client

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



@mcp.tool()
async def whoami(ctx: Context) -> str:
    """Return the display name and email of the authenticated user."""
    token = _extract_token(ctx)
    g = _make_graph_client(token, _azure_settings)
    user = await g.get_user()
    return f"Name: {user.display_name}\nEmail: {user.mail or user.user_principal_name}"


@mcp.tool()
async def list_inbox(ctx: Context) -> str:
    """List the 25 most recent messages in the authenticated user's inbox."""
    token = _extract_token(ctx)
    g = _make_graph_client(token, _azure_settings)
    message_page = await g.get_inbox()

    if not message_page or not message_page.value:
        return "Inbox is empty."

    output = []
    for message in message_page.value:
        sender = (
            message.from_.email_address.name
            if message.from_ and message.from_.email_address
            else "NONE"
        )
        output.append(
            f"Subject: {message.subject}\n"
            f"From: {sender}\n"
            f"Status: {'Read' if message.is_read else 'Unread'}\n"
            f"Received: {message.received_date_time}\n"
        )

    more_available = message_page.odata_next_link is not None
    output.append(f"More messages available: {more_available}")

    return "\n".join(output)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
