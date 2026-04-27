import json
import logging
from pathlib import Path

from mcp.server.fastmcp import Context


def extract_session_token(ctx: Context) -> str:
    http_request = ctx.request_context.request
    if http_request is None:
        raise RuntimeError(
            "No HTTP request in context. "
            "This tool requires streamable-http transport."
        )
    auth = http_request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise RuntimeError("Missing or invalid Authorization header.")
    return auth[7:]


def write_session_ref(path: Path, session_token: str, log: logging.Logger | None = None) -> None:
    path.write_text(json.dumps({"session_token": session_token}), encoding="utf-8")
    if log:
        log.info("Session ref written to %s  session=%s", path, session_token)


def read_session_ref(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("session_token")
    except Exception:
        return None
