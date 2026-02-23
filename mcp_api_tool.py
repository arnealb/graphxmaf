import configparser
import os
import time

from mcp.server.fastmcp import FastMCP, Context
from starlette.requests import Request
from starlette.responses import JSONResponse
from azure.core.credentials import AccessToken

from graph_tutorial import Graph
from tokencred import StaticTokenCredential, _make_graph_client, search

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

@mcp.tool()
async def list_files(ctx: Context) -> str:
    """List the first 20 files in OneDrive root."""

    token = _extract_token(ctx)
    g = _make_graph_client(token, _azure_settings)

    files = await g.get_drive_items()

    if not files or not files.value:
        return "No files found."

    output = []
    for item in files.value:
        output.append(
            f"Name: {item.name}\n"
            f"Type: {'Folder' if item.folder else 'File'}\n"
            f"WebUrl: {item.web_url}\n"
        )

    return "\n".join(output)

@mcp.tool()
async def list_contacts(ctx: Context) -> str:
    """List the first 15 contacts."""

    token = _extract_token(ctx)
    g = _make_graph_client(token, _azure_settings)

    contacts = await g.get_contacts()

    if not contacts or not contacts.value:
        return "No contacts found."

    output = []
    for c in contacts.value:
        email = c.email_addresses[0].address if c.email_addresses else "N/A"

        output.append(
            f"Name: {c.display_name}\n"
            f"Email: {email}\n"
        )

    return "\n".join(output)

@mcp.tool()
async def list_calendar(ctx: Context) -> str:
    """List the next 10 upcoming calendar events."""

    token = _extract_token(ctx)
    g = _make_graph_client(token, _azure_settings)

    events = await g.get_upcoming_events()

    if not events or not events.value:
        return "No upcoming events found."

    output = []
    for event in events.value:
        output.append(
            f"Subject: {event.subject}\n"
            f"Start: {event.start.date_time if event.start else 'N/A'}\n"
            f"End: {event.end.date_time if event.end else 'N/A'}\n"
        )

    return "\n".join(output)


# @mcp.tool()
# async def unified_search(
#     ctx: Context,
#     query: str,
#     entities: list[str] = ["message", "event", "driveItem", "person"]
# ) -> str:
#     """
#     Search across mail, calendar, contacts and files using Microsoft Graph search API.
#     """

#     token = _extract_token(ctx)
#     g = _make_graph_client(token, _azure_settings)

#     result = await g.search(query=query, entity_types=entities)

#     if not result or "value" not in result or not result["value"]:
#         return "No results found."

#     hits = result["value"][0].get("hitsContainers", [])
#     if not hits:
#         return "No results found."

#     output = []

#     for container in hits:
#         for hit in container.get("hits", []):
#             resource = hit.get("resource", {})
#             entity_type = container.get("entityType", "unknown")

#             if entity_type == "message":
#                 output.append(
#                     f"[MAIL]\n"
#                     f"Subject: {resource.get('subject')}\n"
#                     f"From: {resource.get('from', {}).get('emailAddress', {}).get('name')}\n"
#                 )

#             elif entity_type == "event":
#                 output.append(
#                     f"[EVENT]\n"
#                     f"Subject: {resource.get('subject')}\n"
#                     f"Start: {resource.get('start', {}).get('dateTime')}\n"
#                 )

#             elif entity_type == "driveItem":
#                 output.append(
#                     f"[FILE]\n"
#                     f"Name: {resource.get('name')}\n"
#                     f"WebUrl: {resource.get('webUrl')}\n"
#                 )

#             elif entity_type == "person":
#                 output.append(
#                     f"[CONTACT]\n"
#                     f"Name: {resource.get('displayName')}\n"
#                     f"Email: {resource.get('emailAddresses', [{}])[0].get('address')}\n"
#                 )

#     return "\n".join(output) if output else "No results found."


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
