import os
import sys
import socket
import time
import logging
import configparser
import subprocess
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import httpx
import msal

from agent_framework import MCPStreamableHTTPTool
from agent_framework.devui import serve
from agents.graph_agent import create_graph_agent
from agents.orchestrator_agent import create_orchestrator_agent
from agents.salesforce_agent import create_salesforce_agent
from agents.smartsales_agent import create_smartsales_agent

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("mcp").setLevel(logging.WARNING)

_TOKEN_CACHE_FILE = ".token_cache.bin"
_LOCAL_REDIRECT_URI = "http://localhost:5000"


# ── MSAL helpers ──────────────────────────────────────────────────────────────

def _build_msal_app(
    client_id: str, tenant_id: str, client_secret: str
) -> tuple[msal.ConfidentialClientApplication, msal.SerializableTokenCache]:
    cache = msal.SerializableTokenCache()
    if os.path.exists(_TOKEN_CACHE_FILE):
        with open(_TOKEN_CACHE_FILE, "r") as f:
            cache.deserialize(f.read())

    app = msal.ConfidentialClientApplication(
        client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        client_credential=client_secret,
        token_cache=cache,
    )
    return app, cache


def _persist_cache(cache: msal.SerializableTokenCache) -> None:
    if cache.has_state_changed:
        with open(_TOKEN_CACHE_FILE, "w") as f:
            f.write(cache.serialize())


def authenticate(client_id: str, tenant_id: str, scopes: list[str], client_secret: str) -> str:
    """Acquire a delegated access token via MSAL auth code flow (confidential client).

    Tries the token cache first; falls back to browser-based auth code flow.
    """
    app, cache = _build_msal_app(client_id, tenant_id, client_secret)

    # Try silent first (cached token).
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(scopes, account=accounts[0])
        if result and "access_token" in result:
            _persist_cache(cache)
            return result["access_token"]

    # Auth code flow — open browser, catch redirect on localhost.
    flow = app.initiate_auth_code_flow(scopes=scopes, redirect_uri=_LOCAL_REDIRECT_URI)
    if "auth_uri" not in flow:
        raise RuntimeError(f"Failed to create auth flow: {flow}")

    print(f"\nOpening browser for login...")
    webbrowser.open(flow["auth_uri"])

    # Mini HTTP server to catch the OAuth callback.
    auth_response = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            # Parse query params from the redirect URL
            parsed = urlparse(self.path)
            params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
            auth_response.update(params)
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h3>Authenticated! You can close this tab.</h3></body></html>")

        def log_message(self, *args):
            pass  # suppress console spam

    server = HTTPServer(("localhost", 5000), CallbackHandler)
    print("Waiting for authentication callback...")
    server.handle_request()
    server.server_close()

    # Exchange the auth code for tokens.
    result = app.acquire_token_by_auth_code_flow(flow, auth_response)
    if "access_token" not in result:
        raise RuntimeError(
            f"Authentication failed: {result.get('error_description', 'Unknown error')}"
        )

    _persist_cache(cache)
    return result["access_token"]


# ── Server helpers ────────────────────────────────────────────────────────────

def _is_local_url(url: str) -> bool:
    host = urlparse(url).hostname or ""
    return host in ("localhost", "127.0.0.1", "::1")





def _wait_for_port(host: str, port: int, timeout: float = 15.0) -> None:
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


def _start_graph_mcp_server(env: dict, mcp_url: str) -> subprocess.Popen:
    proc = subprocess.Popen(
        [sys.executable, "-m", "graph.mcp_server"],
        env=env,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    parsed = urlparse(mcp_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 8000
    print(f"Waiting for MCP server on {host}:{port} …")
    _wait_for_port(host, port)
    print("MCP server ready.")
    return proc


def _start_salesforce_mcp_server(env: dict, mcp_url: str) -> subprocess.Popen:
    proc = subprocess.Popen(
        [sys.executable, "-m", "salesforce.mcp_server"],
        env=env,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    parsed = urlparse(mcp_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 8001
    print(f"Waiting for Salesforce MCP server on {host}:{port} …")
    _wait_for_port(host, port)
    print("Salesforce MCP server ready.")
    return proc


def _start_smartsales_mcp_server(env: dict, mcp_url: str) -> subprocess.Popen:
    proc = subprocess.Popen(
        [sys.executable, "-m", "smartsales.mcp_server"],
        env=env,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    parsed = urlparse(mcp_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 8002
    print(f"Waiting for SmartSales MCP server on {host}:{port} …")
    _wait_for_port(host, port)
    print("SmartSales MCP server ready.")
    return proc


# ── Session resolvers ─────────────────────────────────────────────────────────

def _resolve_ss_session(ss_mcp_url: str) -> str:
    parsed = urlparse(ss_mcp_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    session_url = f"{base}/auth/smartsales/session"

    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            resp = httpx.get(session_url, timeout=5)
            if resp.status_code == 200:
                print("SmartSales: session ready.")
                return resp.json()["session_token"]
        except httpx.RequestError:
            pass
        time.sleep(1)

    raise RuntimeError(f"SmartSales session not ready within 30s at {base}")


def _resolve_sf_session(sf_mcp_url: str) -> str:
    """Return a valid Salesforce session token, triggering browser auth if needed."""
    parsed = urlparse(sf_mcp_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    session_url = f"{base}/auth/salesforce/session"
    login_url = f"{base}/auth/salesforce/login"

    # 1. Check for existing session.
    # Use a longer timeout to accommodate Azure Container App cold-starts (30–60 s).
    try:
        resp = httpx.get(session_url, timeout=90)
        if resp.status_code == 200:
            data = resp.json()
            print(f"Salesforce: session restored ({data.get('username', '?')}).")
            return data["session_token"]
    except httpx.RequestError as exc:
        raise RuntimeError(f"Cannot reach Salesforce MCP server at {base}: {exc}") from exc

    # 2. No session — authenticate via browser.
    print(f"\nNo active Salesforce session found.")
    print(f"Opening browser for Salesforce login: {login_url}")
    webbrowser.open(login_url)
    print("Waiting for authentication (timeout: 120 s) …\n")

    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        time.sleep(2)
        try:
            resp = httpx.get(session_url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                print(f"Salesforce: authenticated as {data.get('username', '?')}.")
                return data["session_token"]
        except httpx.RequestError:
            pass

    raise TimeoutError(
        "Salesforce authentication timed out after 120 s. "
        f"Re-open {login_url} manually and restart."
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Starting application...")

    config = configparser.ConfigParser()
    config.read(["config.cfg"])
    azure_settings = config["azure"]
    sf_settings = config["salesforce"]
    ss_settings = config["smartsales"] if config.has_section("smartsales") else {}

    # ── Microsoft Graph ────────────────────────────────────────────────
    client_id = azure_settings["clientId"]
    tenant_id = azure_settings["tenantId"]
    client_secret = azure_settings.get("clientSecret", os.environ.get("CLIENT_SECRET", ""))
    scopes = azure_settings["graphUserScopes"].split(" ")
    mcp_url = azure_settings.get("mcpServerUrl", "http://localhost:8000/mcp")

    token = authenticate(client_id, tenant_id, scopes, client_secret)
    print("Authenticated with Microsoft.")

    server_env = os.environ.copy()
    parsed = urlparse(mcp_url)
    resource_base = f"{parsed.scheme}://{parsed.netloc}"
    server_env["MCP_RESOURCE_URI"] = resource_base

    graph_proc = None
    if _is_local_url(mcp_url):
        graph_proc = _start_graph_mcp_server(server_env, mcp_url)

    graph_http = httpx.AsyncClient(
        headers={"Authorization": f"Bearer {token}"},
    )
    graph_mcp = MCPStreamableHTTPTool(
        name="graph",
        url=mcp_url,
        http_client=graph_http,
    )

    # ── Salesforce ─────────────────────────────────────────────────────
    sf_mcp_url = sf_settings.get("mcpServerUrl", "http://localhost:8001/mcp")
    sf_server_env = os.environ.copy()
    sf_parsed = urlparse(sf_mcp_url)
    sf_resource_base = f"{sf_parsed.scheme}://{sf_parsed.netloc}"
    sf_server_env["MCP_RESOURCE_URI"] = sf_resource_base

    sf_proc = None
    if _is_local_url(sf_mcp_url):
        sf_proc = _start_salesforce_mcp_server(sf_server_env, sf_mcp_url)

    sf_session_token = _resolve_sf_session(sf_mcp_url)

    sf_http = httpx.AsyncClient(
        headers={"Authorization": f"Bearer {sf_session_token}"},
    )
    sf_mcp = MCPStreamableHTTPTool(
        name="salesforce",
        url=sf_mcp_url,
        http_client=sf_http,
    )

    # ── SmartSales ──────────────────────────────────────────────────────
    ss_mcp_url = ss_settings.get("mcpServerUrl", "http://localhost:8002/mcp")
    ss_server_env = os.environ.copy()
    ss_parsed = urlparse(ss_mcp_url)
    ss_resource_base = f"{ss_parsed.scheme}://{ss_parsed.netloc}"
    ss_server_env["MCP_RESOURCE_URI"] = ss_resource_base

    ss_proc = None
    if _is_local_url(ss_mcp_url):
        ss_proc = _start_smartsales_mcp_server(ss_server_env, ss_mcp_url)

    ss_session_token = _resolve_ss_session(ss_mcp_url)

    ss_http = httpx.AsyncClient(
        headers={"Authorization": f"Bearer {ss_session_token}"},
    )
    ss_mcp = MCPStreamableHTTPTool(
        name="smartsales",
        url=ss_mcp_url,
        http_client=ss_http,
    )

    # ── Serve agents ───────────────────────────────────────────────────
    try:
        graph_agent = create_graph_agent(graph_mcp=graph_mcp)
        sf_agent = create_salesforce_agent(salesforce_mcp=sf_mcp)
        ss_agent = create_smartsales_agent(smartsales_mcp=ss_mcp)
        orchestrator = create_orchestrator_agent(
            smartsales_agent=ss_agent,
            graph_agent=graph_agent,
            salesforce_agent=sf_agent,
        )
        serve(entities=[orchestrator, ss_agent, graph_agent, sf_agent], port=8080, auto_open=True)
    finally:
        if graph_proc is not None:
            graph_proc.terminate()
            graph_proc.wait()
        if sf_proc is not None:
            sf_proc.terminate()
            sf_proc.wait()
        if ss_proc is not None:
            ss_proc.terminate()
            ss_proc.wait()


if __name__ == "__main__":
    main()