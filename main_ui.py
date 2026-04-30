"""main_ui.py — Multi-turn chat UI server.

Drop-in replacement for the Dev UI serve() call. Exposes a FastAPI server on
port 8090 with session-based agent.run() for true multi-turn conversations and
SSE streaming so tool calls are visible in the browser.

Usage:
    python main_ui.py

Opens the chat UI at http://localhost:8090
"""
import configparser
import json
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from urllib.parse import urlparse

import httpx
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from agent_framework import AgentSession, MCPStreamableHTTPTool
from agents.graph_agent import create_graph_agent
from agents.planning_orchestrator import create_planning_orchestrator
from agents.routing_trace import start_trace
from agents.salesforce_agent import create_salesforce_agent
from agents.smartsales_agent import create_smartsales_agent
from startup import (
    _is_local_url,
    _resolve_sf_session,
    _resolve_ss_session,
    _start_graph_mcp_server,
    _start_salesforce_mcp_server,
    _start_smartsales_mcp_server,
    authenticate,
    auto_index_if_stale,
)

load_dotenv()
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")

# ── Global state ──────────────────────────────────────────────────────────────

_orchestrator = None
_sessions: dict[str, AgentSession] = {}
_procs: list = []
_setup_result: dict = {}  # tokens/urls from sync setup, read by lifespan

# ── Lifespan ──────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _orchestrator

    d = _setup_result
    graph_http = httpx.AsyncClient(headers={"Authorization": f"Bearer {d['graph_token']}"})
    sf_http = httpx.AsyncClient(headers={"Authorization": f"Bearer {d['sf_token']}"})
    ss_http = httpx.AsyncClient(headers={"Authorization": f"Bearer {d['ss_token']}"})

    graph_mcp = MCPStreamableHTTPTool(name="graph", url=d["graph_url"], http_client=graph_http)
    sf_mcp = MCPStreamableHTTPTool(name="salesforce", url=d["sf_url"], http_client=sf_http)
    ss_mcp = MCPStreamableHTTPTool(name="smartsales", url=d["ss_url"], http_client=ss_http)

    graph_agent = create_graph_agent(graph_mcp=graph_mcp)
    sf_agent = create_salesforce_agent(salesforce_mcp=sf_mcp)
    ss_agent = create_smartsales_agent(smartsales_mcp=ss_mcp)
    _orchestrator = create_planning_orchestrator(
        graph_agent=graph_agent,
        sf_agent=sf_agent,
        ss_agent=ss_agent,
    )
    print("Agents ready — http://localhost:8090")

    yield

    await graph_http.aclose()
    await sf_http.aclose()
    await ss_http.aclose()
    for proc in _procs:
        proc.terminate()
        proc.wait()


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="Multi-Turn Chat UI", lifespan=lifespan)


# ── Routes ────────────────────────────────────────────────────────────────────


@app.get("/")
def index():
    return FileResponse("ui/index.html")


@app.get("/api/sessions")
def list_sessions():
    return {"sessions": list(_sessions.keys())}


@app.post("/api/sessions", status_code=201)
def create_session():
    session = AgentSession()
    _sessions[session.session_id] = session
    return {"session_id": session.session_id}


@app.delete("/api/sessions/{session_id}", status_code=204)
def delete_session(session_id: str):
    _sessions.pop(session_id, None)


class ChatRequest(BaseModel):
    session_id: str
    message: str


@app.post("/api/chat")
async def chat(body: ChatRequest):
    if _orchestrator is None:
        raise HTTPException(503, detail="Agent not ready")
    session = _sessions.get(body.session_id)
    if session is None:
        raise HTTPException(404, detail="Session not found — create one first via POST /api/sessions")

    async def generate():
        try:
            start_trace(body.message)
            async for event in _orchestrator.run_sse(body.message, session=session):
                yield _sse(event)
        except Exception as exc:
            logging.getLogger("ui").error("Chat error: %s", exc, exc_info=True)
            yield _sse({"type": "error", "message": str(exc)})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, default=str)}\n\n"


# ── Sync setup ────────────────────────────────────────────────────────────────


def _setup_sync() -> dict:
    """Auth + subprocess startup (blocking). Must run before uvicorn starts."""
    import pathlib
    config = configparser.ConfigParser()
    config.read(["config.cfg"])
    azure = config["azure"]
    sf = config["salesforce"]
    ss = config["smartsales"] if config.has_section("smartsales") else {}
    graphrag_cfg = config["graphrag"] if config.has_section("graphrag") else {}

    if graphrag_cfg.get("auto_index", "false").lower() == "true":
        auto_index_if_stale(pathlib.Path("graph/graphrag"))

    mcp_url = azure.get("mcpServerUrl", "http://localhost:8000/mcp")
    log.info(f"[mcp_url_graph] {mcp_url}")
    log.info("[auth] building MSAL app...")
    token = authenticate(
        azure["clientId"],
        azure["tenantId"],
        azure["graphUserScopes"].split(" "),
        azure.get("clientSecret", os.environ.get("CLIENT_SECRET", "")),
    )
    print("Authenticated with Microsoft.")

    parsed = urlparse(mcp_url)
    server_env = {**os.environ, "MCP_RESOURCE_URI": f"{parsed.scheme}://{parsed.netloc}"}
    if _is_local_url(mcp_url):
        _procs.append(_start_graph_mcp_server(server_env, mcp_url))

    sf_url = sf.get("mcpServerUrl", "http://localhost:8001/mcp")
    log.info(f"[mcp_url_salesforce] {sf_url}")

    sf_parsed = urlparse(sf_url)
    sf_env = {**os.environ, "MCP_RESOURCE_URI": f"{sf_parsed.scheme}://{sf_parsed.netloc}"}
    if _is_local_url(sf_url):
        _procs.append(_start_salesforce_mcp_server(sf_env, sf_url))
    sf_token = _resolve_sf_session(sf_url)

    ss_url = ss.get("mcpServerUrl", "http://localhost:8002/mcp")
    log.info(f"[mcp_url_smartsales] {ss_url}")

    ss_parsed = urlparse(ss_url)
    ss_env = {**os.environ, "MCP_RESOURCE_URI": f"{ss_parsed.scheme}://{ss_parsed.netloc}"}
    if _is_local_url(ss_url):
        _procs.append(_start_smartsales_mcp_server(ss_env, ss_url))
    ss_token = _resolve_ss_session(ss_url)

    return {
        "graph_token": token, "graph_url": mcp_url,
        "sf_token": sf_token, "sf_url": sf_url,
        "ss_token": ss_token, "ss_url": ss_url,
    }


# ── Entry point ───────────────────────────────────────────────────────────────


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )
    for noisy in ("asyncio", "httpx", "httpcore", "mcp"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    try:
        _setup_result.update(_setup_sync())
    except Exception as exc:
        print(f"Setup failed: {exc}", file=sys.stderr)
        sys.exit(1)

    uvicorn.run(app, host="0.0.0.0", port=8090, log_level="warning")


if __name__ == "__main__":
    main()
