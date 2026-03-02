import configparser
import os

from mcp.server.fastmcp import FastMCP, Context
from mcp.shared.context import RequestContext
from starlette.requests import Request
from starlette.responses import JSONResponse

from graph.mcp_router import register_graph_tools


mcp = FastMCP("graph", port=8000)

_config = configparser.ConfigParser()
_config.read(["config.cfg"])
_azure_settings = _config["azure"]

_TENANT_ID = _azure_settings["tenantId"]
_GRAPH_SCOPES = _azure_settings["graphUserScopes"].split(" ")
_RESOURCE_URI = os.environ.get("MCP_RESOURCE_URI", "http://localhost:8000")


@mcp.custom_route("/.well-known/oauth-protected-resource", methods=["GET"])
async def protected_resource_metadata(_request: Request) -> JSONResponse:
    return JSONResponse({
        "resource": _RESOURCE_URI,
        "authorization_servers": [
            f"https://login.microsoftonline.com/{_TENANT_ID}/v2.0"
        ],
        "bearer_methods_supported": ["header"],
        "scopes_supported": _GRAPH_SCOPES,
    })


def _extract_token(ctx: Context) -> str:
    http_request = ctx.request_context.request
    if http_request is None:
        raise RuntimeError(
            "No HTTP request in context. "
            "This tool requires streamable-http transport."
        )
    auth = http_request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise RuntimeError(
            "Missing or invalid Authorization header. "
            "Authenticate via the authorization server listed at "
            f"{_RESOURCE_URI}/.well-known/oauth-protected-resource"
        )
    return auth[7:]


register_graph_tools(mcp, _azure_settings, _extract_token)


# ── /mcp-json REST bridge ─────────────────────────────────────────────────────
#
# POST { "tool": "graph.list-mail-messages", "params": { "$top": 5 } }
#
# Why the original bridge returned known_tools: []:
#   mcp.app.state has no "tools" key — FastMCP stores tools in
#   mcp._tool_manager (a ToolManager), not in the Starlette app state.
#
# Why the original Context construction silently failed:
#   request.scope.get("fastmcp_context") is always None — FastMCP never
#   writes into the ASGI scope under that key.  Passing None means
#   ctx.request_context raises ValueError("Context is not available outside
#   of a request"), which is exactly what _extract_token hits first.
#
# Fix: build a RequestContext whose .request field is the real Starlette
# Request arriving at this endpoint.  _extract_token only reads
# ctx.request_context.request.headers, so session/lifespan_context can be
# None — the Graph tool handlers never touch those fields.

@mcp.custom_route("/mcp-json", methods=["POST"])
async def mcp_json_bridge(request: Request) -> JSONResponse:
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid JSON body"}, status_code=400)

    tool_name: str | None = data.get("tool")
    params: dict = data.get("params", {})

    if not tool_name:
        return JSONResponse({"error": "missing 'tool' field"}, status_code=400)

    # ── locate the tool ───────────────────────────────────────────────────────
    # FastMCP tools live in mcp._tool_manager._tools.
    # Use the public API: get_tool() / list_tools().
    tool = mcp._tool_manager.get_tool(tool_name)
    if tool is None:
        known = [t.name for t in mcp._tool_manager.list_tools()]
        return JSONResponse(
            {"error": f"unknown tool {tool_name!r}", "known_tools": known},
            status_code=404,
        )

    # ── build a Context that carries the real HTTP request ────────────────────
    # RequestContext is a dataclass; Python does not enforce types at runtime.
    # session=None and lifespan_context=None are safe because our tool handlers
    # only call ctx.request_context.request (to read the Authorization header).
    rc = RequestContext(
        request_id="bridge",
        meta=None,
        session=None,        # type: ignore[arg-type]
        lifespan_context=None,
        request=request,     # ← gives _extract_token its Authorization header
    )
    ctx = Context(request_context=rc, fastmcp=mcp)

    # ── execute ───────────────────────────────────────────────────────────────
    # call_tool handles argument validation and injects ctx into context_kwarg.
    # Do NOT call the raw fn directly — that bypasses both.
    try:
        print("calling tool: ", tool_name)
        result = await mcp._tool_manager.call_tool(tool_name, params, context=ctx)
        return JSONResponse({"result": result})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
