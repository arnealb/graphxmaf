# agent_framework_agent.py
import os
import httpx
import msal
import configparser
from agent_framework import MCPStreamableHTTPTool
from agent import create_graph_agent
from dotenv import load_dotenv

load_dotenv()

_TOKEN_CACHE_FILE = ".token_cache.bin"

def _build_msal_app(client_id, tenant_id):
    cache = msal.SerializableTokenCache()
    if os.path.exists(_TOKEN_CACHE_FILE):
        with open(_TOKEN_CACHE_FILE, "r") as f:
            cache.deserialize(f.read())
    app = msal.PublicClientApplication(
        client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        token_cache=cache,
    )
    return app, cache

def get_cached_token() -> str:
    config = configparser.ConfigParser()
    config.read("config.cfg")
    client_id = config["azure"]["clientId"]
    tenant_id = config["azure"]["tenantId"]
    scopes = config["azure"]["graphUserScopes"].split(" ")

    app, cache = _build_msal_app(client_id, tenant_id)
    accounts = app.get_accounts()
    if not accounts:
        raise RuntimeError("Geen cached token gevonden. Run eerst je originele main.py om in te loggen.")
    
    result = app.acquire_token_silent(scopes, account=accounts[0])
    if not result or "access_token" not in result:
        raise RuntimeError("Token verlopen. Run eerst je originele main.py om opnieuw in te loggen.")
    
    if cache.has_state_changed:
        with open(_TOKEN_CACHE_FILE, "w") as f:
            f.write(cache.serialize())
    
    print(f"[GraphAgentWrapper] Cached token opgehaald voor: {accounts[0].get('username')}")
    return result["access_token"]


class GraphAgentWrapper:
    def __init__(self, token: str | None = None):
        mcp_url = os.environ.get("MCP_SERVER_URL", "http://localhost:8000/mcp")
        
        if token:
            print(f"[GraphAgentWrapper] OBO token ontvangen")
        else:
            token = get_cached_token()
            print(f"[GraphAgentWrapper] Cached token gebruikt")

        http_client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {token}"}
        )
        graph_mcp = MCPStreamableHTTPTool(
            name="graph",
            url=mcp_url,
            http_client=http_client,
        )
        self.agent = create_graph_agent(graph_mcp=graph_mcp)

    async def invoke(self, message: str) -> str:
        print(f"[invoke] Bericht naar agent: {message}")
        try:
            result = await self.agent.run(message)
            print(f"[invoke] Antwoord: {result.text[:100]}")
            return result.text
        except Exception as e:
            print(f"[invoke] FOUT: {e}")
            import traceback
            traceback.print_exc()
            raise