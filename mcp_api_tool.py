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
        # Expiry is unknown; report 1 h from now so the SDK accepts it.
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


if __name__ == "__main__":
    mcp.run(transport="stdio")
