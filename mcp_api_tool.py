import configparser
import os
import time

from mcp.server.fastmcp import FastMCP, Context
from starlette.requests import Request
from starlette.responses import JSONResponse
from azure.core.credentials import AccessToken

from graph_api import Graph
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
            f"ID: {message.id}\n"
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


@mcp.tool()
async def read_email(ctx: Context, message_id: str) -> str:
    """Read the full body of a specific email by its message ID."""
    token = _extract_token(ctx)
    g = _make_graph_client(token, _azure_settings)

    message = await g.get_message_body(message_id)

    if not message:
        return "Message not found."

    sender = (
        message.from_.email_address.name
        if message.from_ and message.from_.email_address
        else "Unknown"
    )
    body_content = message.body.content if message.body else "(no body)"

    return (
        f"Subject: {message.subject}\n"
        f"From: {sender}\n"
        f"Received: {message.received_date_time}\n"
        f"\n{body_content}"
    )


@mcp.tool()
async def unified_search(
    ctx: Context,
    query: str,
    entities: list[str] = ["message", "event", "driveItem", "person"],
) -> str:
    """Search across mail, calendar, files and contacts using the Microsoft Graph search API."""
    token = _extract_token(ctx)
    g = _make_graph_client(token, _azure_settings)

    result = await g.search(query=query, entity_types=entities)

    if not result or not result.value:
        return "No results found."

    output = []

    for response in result.value:
        if not response.hits_containers:
            continue
        for container in response.hits_containers:
            if not container.hits:
                continue
            for hit in container.hits:
                resource = hit.resource
                if resource is None:
                    continue

                odata_type = (resource.odata_type or "").lower()

                if "message" in odata_type:
                    output.append(
                        f"[MAIL]\n"
                        f"ID: {resource.id}\n"
                        f"Subject: {getattr(resource, 'subject', 'N/A')}\n"
                    )
                elif "event" in odata_type:
                    output.append(
                        f"[EVENT]\n"
                        f"Subject: {getattr(resource, 'subject', 'N/A')}\n"
                        f"Start: {getattr(resource.start, 'date_time', 'N/A') if resource.start else 'N/A'}\n"
                    )
                elif "driveitem" in odata_type:
                    output.append(
                        f"[FILE]\n"
                        f"Name: {getattr(resource, 'name', 'N/A')}\n"
                        f"WebUrl: {getattr(resource, 'web_url', 'N/A')}\n"
                    )
                elif "person" in odata_type or "contact" in odata_type:
                    output.append(
                        f"[CONTACT]\n"
                        f"Name: {getattr(resource, 'display_name', 'N/A')}\n"
                    )
                else:
                    output.append(f"[{odata_type}] ID: {resource.id}\n")

    return "\n".join(output) if output else "No results found."


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
