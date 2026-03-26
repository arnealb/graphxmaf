# mcp_server.py
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from mcp.server.fastmcp import FastMCP, Context
from starlette.requests import Request
from starlette.responses import JSONResponse

from smartsales.auth import (
    SmartSalesAuthError,
    SmartSalesCredentials,
    authenticate_from_env,
)
from smartsales.mcp_router import register_smartsales_tools, _get_repo
from smartsales.token_store import StoredTokens, build_token_store

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("smartsales.mcp_server")

mcp = FastMCP("smartsales", port=8002)

_token_store = build_token_store()

# Session ref file — stores the UUID of the most recently authenticated session.
# main.py reads this via /auth/smartsales/session so it never needs to manage tokens directly.
_SESSION_REF_FILE = Path(os.environ.get("SS_SESSION_REF_FILE", ".ss_session.json"))


def _write_session_ref(session_token: str) -> None:
    _SESSION_REF_FILE.write_text(json.dumps({"session_token": session_token}), encoding="utf-8")
    log.info("Session ref written  session=%s", session_token)


def _read_session_ref() -> str | None:
    if not _SESSION_REF_FILE.exists():
        return None
    try:
        return json.loads(_SESSION_REF_FILE.read_text(encoding="utf-8")).get("session_token")
    except Exception:
        return None


async def _ensure_session() -> str:
    """Return an active session token, creating one via env-based auth if needed."""
    session_token = _read_session_ref()
    if session_token:
        tokens = await _token_store.get(session_token)
        if tokens and not tokens.is_expired():
            log.info("Existing SmartSales session valid  session=%s", session_token)
            return session_token

    # Authenticate fresh using env credentials — no browser required.
    log.info("Authenticating SmartSales via env credentials …")
    creds = authenticate_from_env()
    tokens = StoredTokens(
        access_token=creds.access_token,
        refresh_token=creds.refresh_token,
        expires_at=creds.expires_at,
    )
    session_token = _token_store.generate_session_token()
    await _token_store.save(session_token, tokens)
    _write_session_ref(session_token)
    log.info("SmartSales session created  session=%s", session_token)
    return session_token


# ──────────────────────────────────────────────────────────────────────────────
# Session discovery (used by main.py on startup)
# ──────────────────────────────────────────────────────────────────────────────

@mcp.custom_route("/auth/smartsales/session", methods=["GET"])
async def smartsales_current_session(_request: Request) -> JSONResponse:
    """Return the active session token, auto-creating one if needed.

    main.py calls this on startup to retrieve the session token without
    managing tokens directly.
    """
    try:
        session_token = await _ensure_session()
        creds = await _resolve_session(session_token)
        repo = _get_repo(session_token, creds.access_token)
        await repo.warm_field_cache()
        return JSONResponse({"session_token": session_token})
    except SmartSalesAuthError as exc:
        log.error("SmartSales auth failed: %s", exc)
        return JSONResponse({"error": str(exc)}, status_code=401)


# ──────────────────────────────────────────────────────────────────────────────
# Session resolution (used by every MCP tool call)
# ──────────────────────────────────────────────────────────────────────────────

async def _resolve_session(session_token: str) -> SmartSalesCredentials:
    """Resolve a session UUID to live SmartSales credentials.

    Auto-refreshes via env credentials if the token is expired.
    """
    tokens = await _token_store.get(session_token)
    if tokens is None:
        raise RuntimeError("Session not found — restart the server to re-authenticate.")

    if tokens.is_expired():
        log.info("SmartSales token expired — re-authenticating …")
        try:
            creds = authenticate_from_env()
            new_tokens = StoredTokens(
                access_token=creds.access_token,
                refresh_token=creds.refresh_token,
                expires_at=creds.expires_at,
            )
            await _token_store.save(session_token, new_tokens)
            tokens = new_tokens
        except SmartSalesAuthError as exc:
            await _token_store.delete(session_token)
            raise RuntimeError(f"Token re-authentication failed (session invalidated): {exc}") from exc

    return SmartSalesCredentials(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_at=tokens.expires_at,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Token extraction helper (reads Bearer UUID from the Authorization header)
# ──────────────────────────────────────────────────────────────────────────────

def _extract_session_token(ctx: Context) -> str:
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


register_smartsales_tools(mcp, _extract_session_token, _resolve_session)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
