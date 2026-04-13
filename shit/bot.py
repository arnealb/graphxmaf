# bot.py
import os
os.environ.setdefault("CONNECTIONS__SERVICE_CONNECTION__SETTINGS__ANONYMOUS_ALLOWED", "True")

import configparser
import httpx
from dotenv import load_dotenv
load_dotenv()

from microsoft_agents.hosting.core import (
    AgentApplication,
    TurnState,
    TurnContext,
    MemoryStorage,
    Authorization,
)
from microsoft_agents.hosting.aiohttp import CloudAdapter
from microsoft_agents.authentication.msal import MsalConnectionManager
from microsoft_agents.activity import load_configuration_from_env

from agent_framework import MCPStreamableHTTPTool
from agents.graph_agent import create_graph_agent
from agents.orchestrator_agent import create_orchestrator_agent
from agents.salesforce_agent import create_salesforce_agent
from start_server import start_server

# ── M365 Agents SDK setup ──
agents_sdk_config = load_configuration_from_env(os.environ)
STORAGE = MemoryStorage()
CONNECTION_MANAGER = MsalConnectionManager(**agents_sdk_config)
ADAPTER = CloudAdapter(connection_manager=CONNECTION_MANAGER)
AUTHORIZATION = Authorization(STORAGE, CONNECTION_MANAGER, **agents_sdk_config)

# ── MCP setup ──

from main import authenticate

config = configparser.ConfigParser()
config.read(["config.cfg"])
azure = config["azure"]
sf_cfg = config["salesforce"]

client_id = azure.get("clientId", "")
tenant_id = azure.get("tenantId", "")
graph_scopes = azure.get("graphUserScopes", "User.Read").split()

try:
    print("starting auth for graph")
    graph_token = authenticate(client_id, tenant_id, graph_scopes)
    print("Authenticated with Microsoft Graph.")
except Exception as e:
    print(f"Graph auth skipped: {e}")
    graph_token = "placeholder"

graph_mcp = MCPStreamableHTTPTool(
    name="graph",
    url=azure.get("mcpServerUrl_graph", "http://localhost:8000/mcp"),
    http_client=httpx.AsyncClient(headers={"Authorization": f"Bearer {graph_token}"}),
)






graph_mcp = MCPStreamableHTTPTool(
    name="graph",
    url=azure.get("mcpServerUrl_graph", "http://localhost:8000/mcp"),
    http_client=httpx.AsyncClient(headers={"Authorization": "Bearer placeholder"}),
)
sf_mcp = MCPStreamableHTTPTool(
    name="salesforce",
    url=sf_cfg.get("mcpServerUrl_sf", "http://localhost:8001/mcp"),
    http_client=httpx.AsyncClient(headers={"Authorization": "Bearer placeholder"}),
)

graph_agent = create_graph_agent(graph_mcp=graph_mcp)
sf_agent = create_salesforce_agent(salesforce_mcp=sf_mcp)
orchestrator = create_orchestrator_agent(graph_agent=graph_agent, salesforce_agent=sf_agent)

# ── M365 Agent wrapper ──
AGENT_APP = AgentApplication[TurnState](
    storage=STORAGE,
    adapter=ADAPTER,
    authorization=AUTHORIZATION,
    **agents_sdk_config,
)

@AGENT_APP.activity("message")
async def on_message(context: TurnContext, _state: TurnState):
    print(f"GOT MESSAGE: {context.activity.text}")
    user_text = context.activity.text
    response = await orchestrator.run(user_text)
    await context.send_activity(response.text)



if __name__ == "__main__":
    start_server(AGENT_APP, CONNECTION_MANAGER.get_default_connection_configuration())