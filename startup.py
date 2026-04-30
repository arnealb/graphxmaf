"""startup.py — Auth + MCP server startup helpers shared by main_ui.py and eval scripts."""
import os
import sys
import socket
import time
import logging
import subprocess
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import httpx
import msal

_TOKEN_CACHE_FILE = ".token_cache.bin"
_LOCAL_REDIRECT_URI = "http://localhost:5001"


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

    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(scopes, account=accounts[0])
        if result and "access_token" in result:
            _persist_cache(cache)
            return result["access_token"]

    flow = app.initiate_auth_code_flow(scopes=scopes, redirect_uri=_LOCAL_REDIRECT_URI)
    if "auth_uri" not in flow:
        raise RuntimeError(f"Failed to create auth flow: {flow}")

    print(f"\nOpening browser for login...")
    webbrowser.open(flow["auth_uri"])

    auth_response = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
            auth_response.update(params)
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h3>Authenticated! You can close this tab.</h3></body></html>")

        def log_message(self, *args):
            pass

    server = HTTPServer(("localhost", 5001), CallbackHandler)
    print("Waiting for authentication callback...")
    server.handle_request()
    server.server_close()

    result = app.acquire_token_by_auth_code_flow(flow, auth_response)
    if "access_token" not in result:
        raise RuntimeError(
            f"Authentication failed: {result.get('error_description', 'Unknown error')}"
        )

    _persist_cache(cache)
    return result["access_token"]


def auto_index_if_stale(graphrag_root: Path) -> None:
    """Re-index GraphRAG if source documents are newer than the existing index.

    Checks modification times: if any file in data_untouched/ is newer than
    output/documents.parquet, wipes input/ and re-runs the full indexer.
    Safe to call on every startup — skips immediately when the index is current.
    """
    output = graphrag_root / "output" / "documents.parquet"
    data_dir = graphrag_root / "data_untouched"

    if not data_dir.exists():
        log.info("[graphrag] data_untouched/ not found — skipping auto-index.")
        return

    sources = list(data_dir.rglob("*.docx")) + list(data_dir.rglob("*.txt"))
    if not sources:
        log.info("[graphrag] No source documents found — skipping auto-index.")
        return

    newest_source = max(f.stat().st_mtime for f in sources)
    if output.exists() and output.stat().st_mtime >= newest_source:
        log.info("[graphrag] Index is up-to-date, skipping re-index.")
        return

    log.info("[graphrag] Index is stale or missing — re-indexing (%d source files)...", len(sources))
    from graph.graphrag_indexer import convert_all, run_index
    n = convert_all()
    if n > 0:
        run_index()
    log.info("[graphrag] Re-indexing complete.")


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
    raise TimeoutError(f"MCP server at {host}:{port} did not become ready within {timeout}s")


def _start_mcp_server(module: str, env: dict, mcp_url: str, label: str) -> subprocess.Popen:
    proc = subprocess.Popen(
        [sys.executable, "-m", module],
        env=env,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    parsed = urlparse(mcp_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 8000
    print(f"Waiting for {label} MCP server on {host}:{port} …")
    _wait_for_port(host, port)
    print(f"{label} MCP server ready.")
    return proc


def _start_graph_mcp_server(env: dict, mcp_url: str) -> subprocess.Popen:
    return _start_mcp_server("graph.mcp_server", env, mcp_url, "Graph")


def _start_salesforce_mcp_server(env: dict, mcp_url: str) -> subprocess.Popen:
    return _start_mcp_server("salesforce.mcp_server", env, mcp_url, "Salesforce")


def _start_smartsales_mcp_server(env: dict, mcp_url: str) -> subprocess.Popen:
    return _start_mcp_server("smartsales.mcp_server", env, mcp_url, "SmartSales")


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
    parsed = urlparse(sf_mcp_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    session_url = f"{base}/auth/salesforce/session"
    login_url = f"{base}/auth/salesforce/login"

    try:
        resp = httpx.get(session_url, timeout=90)
        if resp.status_code == 200:
            data = resp.json()
            print(f"Salesforce: session restored ({data.get('username', '?')}).")
            return data["session_token"]
    except httpx.RequestError as exc:
        raise RuntimeError(f"Cannot reach Salesforce MCP server at {base}: {exc}") from exc

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
