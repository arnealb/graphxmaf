import os
import sys
import socket
import time
import logging
import configparser
import subprocess
from urllib.parse import urlparse

import httpx
import msal

from agent_framework import MCPStreamableHTTPTool
from agent_framework.devui import serve
from agent import create_graph_agent

logging.getLogger("asyncio").setLevel(logging.CRITICAL)

_TOKEN_CACHE_FILE = ".token_cache.bin"


# https://bonanipaulchaudhury.medium.com/integrating-oauth-2-0-delegation-via-azure-api-management-with-mcp-and-prm-why-it-matters-f6c993ef591f



def _build_msal_app(
    client_id: str, tenant_id: str
) -> tuple[msal.PublicClientApplication, msal.SerializableTokenCache]:
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


def _persist_cache(cache: msal.SerializableTokenCache) -> None:
    if cache.has_state_changed:
        with open(_TOKEN_CACHE_FILE, "w") as f:
            f.write(cache.serialize())


def authenticate(client_id: str, tenant_id: str, scopes: list[str]) -> str:
    """Acquire a delegated access token via MSAL.

    Tries the token cache first; falls back to the device code flow.
    In production (or with VS Code / Claude Desktop) the MCP client reads
    /.well-known/oauth-protected-resource and drives an auth-code + PKCE
    flow automatically — no manual token acquisition is needed.
    """
    app, cache = _build_msal_app(client_id, tenant_id)

# uncomment this to use cached tokens
    # Silent path: use a cached token when available.
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(scopes, account=accounts[0])
        if result and "access_token" in result:
            _persist_cache(cache)
            return result["access_token"]

    # Interactive path: device code flow.

    print("starting auth")

    flow = app.initiate_device_flow(scopes=scopes)

    print(f"\nAuthenticate at: {flow['verification_uri']}")
    print(f"Enter code:      {flow['user_code']}\n")
    
    result = app.acquire_token_by_device_flow(flow)

    if "access_token" not in result:
        raise RuntimeError(
            f"Authentication failed: {result.get('error_description', 'Unknown error')}"
        )

    _persist_cache(cache)
    return result["access_token"]



def _is_local_url(url: str) -> bool:
    # gewoon ofda local of cloud
    host = urlparse(url).hostname or ""
    return host in ("localhost", "127.0.0.1", "::1")


def _wait_for_port(host: str, port: int, timeout: float = 15.0) -> None:
    # idk waarom dis shit echt nodig is 
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return
        except OSError:
            time.sleep(0.25)
    raise TimeoutError(
        f"MCP server at {host}:{port} did not become ready within {timeout}s"
    )


def _start_local_mcp_server(env: dict) -> subprocess.Popen:
    # mcp_api_tool.py als achtergrond http server launchen

    proc = subprocess.Popen(
        [sys.executable, "mcp_api_tool.py"],
        env=env,
        # fouten / output naar zelfde terminal sturen 
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    parsed = urlparse(env.get("MCP_SERVER_URL", "http://localhost:8000"))
    host = parsed.hostname or "localhost"
    port = parsed.port or 8000
    print(f"Waiting for MCP server on {host}:{port} …")
    _wait_for_port(host, port)
    print("MCP server ready.")
    return proc

    

def main() -> None:
    print("Starting application...")

    config = configparser.ConfigParser()
    config.read(["config.cfg"])
    azure_settings = config["azure"]

    client_id = azure_settings["clientId"]
    tenant_id = azure_settings["tenantId"]
    scopes = azure_settings["graphUserScopes"].split(" ")
    mcp_url = azure_settings.get("mcpServerUrl", "http://localhost:8000/mcp")

    # 1. client logt in + scopes
    token = authenticate(client_id, tenant_id, scopes)
    print("Authenticated.")

                            # Build the environment that will be passed to the server subprocess so
                            # it can construct the correct PRM response.

    # 1.2 environment maken dat naar de server gestuurd wordt (wat is een prm resp)
    server_env = os.environ.copy()
    parsed = urlparse(mcp_url)
    resource_base = f"{parsed.scheme}://{parsed.netloc}"
    server_env["MCP_RESOURCE_URI"] = resource_base

    # dit is gwn een test om te zien of het een local mcp server / al in de cloud draait
    # als local -> spin up
    server_proc = None
    if _is_local_url(mcp_url):
        server_proc = _start_local_mcp_server(server_env)

    # Pass the bearer token on every HTTP request to the MCP server.
    # APIM (or the MCP server itself in local dev) validates this token.
    # token met ieder request doorsturen naar de MCP server
    # dafaq is APIM
    http_client = httpx.AsyncClient(
        headers={"Authorization": f"Bearer {token}"},
    )

    graph_mcp = MCPStreamableHTTPTool(
        name="graph",
        url=mcp_url,
        http_client=http_client,
    )





    try:
        agent = create_graph_agent(graph_mcp=graph_mcp)
        serve(entities=[agent], port=8080, auto_open=True)
    finally:
        if server_proc is not None:
            server_proc.terminate()
            server_proc.wait()


if __name__ == "__main__":
    main()
