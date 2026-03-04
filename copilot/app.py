# app.py
# Run from the project root: python copilot/app.py
import os
import sys

# Make the project root importable (for agent.py, main.py, etc.)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import configparser
import logging
from urllib.parse import urlparse

import httpx
from agent_framework import MCPStreamableHTTPTool
from agent_framework._sessions import AgentSession
from agent_framework._types import Message
from microsoft_agents.hosting.core import (
    AgentApplication,
    AgentAuthConfiguration,
    TurnState,
    TurnContext,
    MemoryStorage,
)
from microsoft_agents.hosting.aiohttp import CloudAdapter
from start_server import start_server

from main import authenticate, _is_local_url, _start_local_mcp_server
from agent import create_graph_agent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

# ── startup: authenticate + MCP server + graph agent ──────────────────────────
_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
config = configparser.ConfigParser()
config.read(os.path.join(_root, "config.cfg"))
azure = config["azure"]

client_id = azure["clientId"]
tenant_id = azure["tenantId"]
scopes = azure["graphUserScopes"].split(" ")
mcp_url = azure.get("mcpServerUrl", "http://localhost:8000/mcp")

# Acquire a delegated token (uses cache if available, otherwise device-code flow).
# On first run: follow the printed instructions in the terminal.
token = authenticate(client_id, tenant_id, scopes)
print("Authenticated.")

server_env = os.environ.copy()
parsed = urlparse(mcp_url)
server_env["MCP_RESOURCE_URI"] = f"{parsed.scheme}://{parsed.netloc}"

# Start the local MCP server (mcp_api_tool.py) if the URL points to localhost.
# Must be run from the project root so the subprocess can find mcp_api_tool.py.
_server_proc = None
if _is_local_url(mcp_url):
    _server_proc = _start_local_mcp_server(server_env)

_http_client = httpx.AsyncClient(headers={"Authorization": f"Bearer {token}"})
graph_mcp = MCPStreamableHTTPTool(name="graph", url=mcp_url, http_client=_http_client)
_agent = create_graph_agent(graph_mcp=graph_mcp)

# One AgentSession per Teams/Copilot conversation — preserves history + doc context.
_sessions: dict[str, AgentSession] = {}

# ── Copilot / Teams bot ────────────────────────────────────────────────────────
AGENT_APP = AgentApplication[TurnState](
    storage=MemoryStorage(), adapter=CloudAdapter()
)


async def _welcome(context: TurnContext, _: TurnState):
    await context.send_activity(
        "Hallo! Ik ben de GraphAgent. "
        "Stel me een vraag over je Microsoft 365 data (mail, agenda, bestanden, contacten). "
        "Typ /help om dit bericht opnieuw te zien."
    )


AGENT_APP.conversation_update("membersAdded")(_welcome)
AGENT_APP.message("/help")(_welcome)


@AGENT_APP.activity("message")
async def on_message(context: TurnContext, _: TurnState):
    user_text = (context.activity.text or "").strip()
    if not user_text:
        return

    conv_id = context.activity.conversation.id
    if conv_id not in _sessions:
        _sessions[conv_id] = AgentSession(session_id=conv_id)

    response = await _agent.run(
        messages=[Message("user", [user_text])],
        session=_sessions[conv_id],
    )
    await context.send_activity(response.text or "(geen antwoord)")


if __name__ == "__main__":
    try:
        start_server(AGENT_APP, AgentAuthConfiguration(anonymous_allowed=True))
    finally:
        if _server_proc is not None:
            _server_proc.terminate()
            _server_proc.wait()
