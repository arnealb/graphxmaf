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
from agents.orchestrator_agent import create_orchestrator_agent
from agents.salesforce_agent import create_salesforce_agent
from agents.smartsales_agent import create_smartsales_agent
from main import (
    _is_local_url,
    _resolve_sf_session,
    _resolve_ss_session,
    _start_graph_mcp_server,
    _start_salesforce_mcp_server,
    _start_smartsales_mcp_server,
    authenticate,
)

load_dotenv()

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
    _orchestrator = create_orchestrator_agent(
        smartsales_agent=ss_agent,
        graph_agent=graph_agent,
        salesforce_agent=sf_agent,
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
        # function_call content arrives as streaming chunks (one per token).
        # Accumulate all chunks for the same call_id, then emit a single
        # tool_call event once the matching function_result arrives.
        pending: dict[str, dict] = {}  # call_id → {name, args_buf, emitted}

        def flush_call(cid: str) -> str | None:
            data = pending.get(cid)
            if not data or data["emitted"]:
                return None
            data["emitted"] = True
            args_str = data["args_buf"]
            try:
                args = json.loads(args_str) if args_str else {}
            except json.JSONDecodeError:
                args = args_str
            return _sse({"type": "tool_call", "call_id": cid, "name": data["name"], "arguments": args})

        try:
            stream = _orchestrator.run(body.message, session=session, stream=True)
            async for update in stream:
                for content in update.contents:
                    ctype = getattr(content, "type", None)

                    if ctype == "text" and content.text:
                        yield _sse({"type": "text", "chunk": content.text})

                    elif ctype == "function_call":
                        cid = content.call_id or ""
                        if cid not in pending:
                            pending[cid] = {"name": content.name or "", "args_buf": "", "emitted": False}
                        data = pending[cid]
                        if content.name and not data["name"]:
                            data["name"] = content.name
                        # Arguments arrive either as incremental string chunks or as a
                        # complete dict in one shot. Guard against two overwrite traps:
                        # (a) an empty-dict terminator chunk wiping accumulated strings,
                        # (b) a later chunk overwriting an already-populated buffer.
                        args = content.arguments
                        if isinstance(args, str) and args:
                            # String token — always append (this is the streaming case)
                            data["args_buf"] += args
                        elif args and not isinstance(args, str):
                            # Complete dict/mapping — only store if buffer still empty
                            if not data["args_buf"]:
                                try:
                                    data["args_buf"] = json.dumps(dict(args))
                                except Exception:
                                    data["args_buf"] = str(args)
                        # None, empty string, or empty dict {} → skip (terminator chunk)

                    elif ctype == "function_result":
                        cid = content.call_id or ""
                        event = flush_call(cid)
                        if event:
                            yield event
                        result = content.result
                        if isinstance(result, bytes):
                            result = result.decode()
                        yield _sse({"type": "tool_result", "call_id": cid, "result": result if result is not None else ""})

            # Flush any calls that never received a result
            for cid in pending:
                event = flush_call(cid)
                if event:
                    yield event

            final = await stream.get_final_response()
            usage = getattr(final, "usage_details", None)
            tokens = getattr(usage, "total_token_count", None) if usage else None
            yield _sse({"type": "done", "tokens": tokens})

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
    config = configparser.ConfigParser()
    config.read(["config.cfg"])
    azure = config["azure"]
    sf = config["salesforce"]
    ss = config["smartsales"] if config.has_section("smartsales") else {}

    mcp_url = azure.get("mcpServerUrl", "http://localhost:8000/mcp")
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
    sf_parsed = urlparse(sf_url)
    sf_env = {**os.environ, "MCP_RESOURCE_URI": f"{sf_parsed.scheme}://{sf_parsed.netloc}"}
    if _is_local_url(sf_url):
        _procs.append(_start_salesforce_mcp_server(sf_env, sf_url))
    sf_token = _resolve_sf_session(sf_url)

    ss_url = ss.get("mcpServerUrl", "http://localhost:8002/mcp")
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
