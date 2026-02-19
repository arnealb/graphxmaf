import sys
import os
import time
import configparser
from mcp.server.fastmcp import FastMCP
from azure.core.credentials import AccessToken
from graph_tutorial import Graph

mcp = FastMCP("graph")
graph = None


class StaticTokenCredential:
    """Wraps a pre-obtained access token so the MCP subprocess never needs
    to show an interactive authentication prompt."""

    def __init__(self, token: str):
        self._token = token

    def get_token(self, *scopes, **kwargs) -> AccessToken:
        return AccessToken(self._token, int(time.time()) + 3600)


def ensure_graph():
    global graph
    if graph is None:
        config = configparser.ConfigParser()
        config.read(["config.cfg"])
        azure_settings = config["azure"]

        token = os.environ.get("GRAPH_ACCESS_TOKEN")
        if not token:
            raise RuntimeError(
                "GRAPH_ACCESS_TOKEN env var is not set. "
                "Authenticate in the main process first."
            )

        credential = StaticTokenCredential(token)
        graph = Graph(azure_settings, credential=credential)

    return graph


@mcp.tool()
async def whoami() -> str:
    g = ensure_graph()
    user = await g.get_user()
    return f"Name: {user.display_name}\nEmail: {user.mail or user.user_principal_name}"

@mcp.tool()
async def list_inbox() -> str:
    g = ensure_graph()
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
    mcp.run(transport="stdio")
