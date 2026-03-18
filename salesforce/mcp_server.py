# mcp_server.py
import configparser
import logging
import os
import uuid

from dotenv import load_dotenv
load_dotenv()

from mcp.server.fastmcp import FastMCP, Context
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

from salesforce.auth import (
    SalesforceAuthError,
    SalesforceCredentials,
    build_authorization_url,
    exchange_code_for_tokens,
    refresh_access_token,
)
from salesforce.mcp_router import register_salesforce_tools
from salesforce.token_store import StoredTokens, build_token_store

log = logging.getLogger("salesforce.mcp_server")

mcp = FastMCP("salesforce", port=8001)

_config = configparser.ConfigParser()
_config.read(["config.cfg"])
_sf_settings = _config["salesforce"]

_RESOURCE_URI = os.environ.get("MCP_RESOURCE_URI", "http://localhost:8001")

# OAuth config — all readable from env; config.cfg provides fallbacks.
_SF_LOGIN_URL = "https://test.salesforce.com"
_SF_CLIENT_ID = os.environ.get("SF_CLIENT_ID", "")
_SF_CLIENT_SECRET = os.environ.get("SF_CLIENT_SECRET", "")
_SF_CALLBACK_URL = os.environ.get("SF_OAUTH_CALLBACK_URL", "http://localhost:8001/auth/salesforce/callback")
# _SF_LOGIN_URL = (
#     os.environ.get("SF_LOGIN_URL")
#     or _sf_settings.get("loginUrl", "https://test.salesforce.com")
# )
# _SF_CALLBACK_URL = (
#     os.environ.get("SF_OAUTH_CALLBACK_URL")
#     or _sf_settings.get("oauthCallbackUrl", "http://localhost:8001/auth/salesforce/callback")
# )

# Token store singleton (file-backed for dev, Key Vault for prod).
_token_store = build_token_store()

log.info(
    "SF OAuth config  client_id=%s  callback=%s  login_url=%s  store=%s",
    _SF_CLIENT_ID[:8] + "…" if _SF_CLIENT_ID else "MISSING",
    _SF_CALLBACK_URL,
    _SF_LOGIN_URL,
    type(_token_store).__name__,
)

# In-memory CSRF state map: state UUID → redirect_after URL.
_pending_states: dict[str, str] = {}


# ──────────────────────────────────────────────────────────────────────────────
# Well-known metadata
# ──────────────────────────────────────────────────────────────────────────────

@mcp.custom_route("/.well-known/oauth-protected-resource", methods=["GET"])
async def protected_resource_metadata(_request: Request) -> JSONResponse:
    return JSONResponse({
        "resource": _RESOURCE_URI,
        "bearer_methods_supported": ["header"],
        "login_endpoint": f"{_RESOURCE_URI}/auth/salesforce/login",
    })


# ──────────────────────────────────────────────────────────────────────────────
# OAuth 2.0 Authorization Code Flow routes
# ──────────────────────────────────────────────────────────────────────────────

@mcp.custom_route("/auth/salesforce/login", methods=["GET"])
async def salesforce_login(request: Request) -> RedirectResponse:
    """Redirect the browser to the Salesforce OAuth consent page."""
    redirect_after = request.query_params.get("redirect_after", "")
    state = str(uuid.uuid4())
    _pending_states[state] = redirect_after

    auth_url = build_authorization_url(
        client_id=_SF_CLIENT_ID,
        redirect_uri=_SF_CALLBACK_URL,
        login_url=_SF_LOGIN_URL,
        state=state,
    )
    return RedirectResponse(auth_url, status_code=302)


@mcp.custom_route("/auth/salesforce/callback", methods=["GET"])
async def salesforce_callback(request: Request) -> JSONResponse:
    """Receive the authorization code, exchange it, persist the tokens."""
    # Salesforce sends ?error=...&error_description=... when auth fails.
    sf_error = request.query_params.get("error")
    if sf_error:
        desc = request.query_params.get("error_description", sf_error)
        log.error("Salesforce returned error: %s — %s", sf_error, desc)
        return JSONResponse({"error": sf_error, "error_description": desc}, status_code=400)

    code = request.query_params.get("code")
    state = request.query_params.get("state")

    if not code:
        return JSONResponse({"error": "missing_code"}, status_code=400)
    if not state or state not in _pending_states:
        log.error("State mismatch: received=%s known=%s", state, list(_pending_states))
        return JSONResponse({"error": "invalid_state"}, status_code=400)

    _pending_states.pop(state)

    try:
        token_data = await exchange_code_for_tokens(
            code=code,
            client_id=_SF_CLIENT_ID,
            client_secret=_SF_CLIENT_SECRET,
            redirect_uri=_SF_CALLBACK_URL,
            login_url=_SF_LOGIN_URL,
        )
    except SalesforceAuthError as exc:
        log.error("Code exchange failed: %s", exc)
        return JSONResponse({"error": str(exc)}, status_code=400)

    tokens = StoredTokens.from_token_response(token_data)
    session_token = _token_store.generate_session_token()
    await _token_store.save(session_token, tokens)

    log.info("New session created user=%s session=%s", tokens.username, session_token)
    return JSONResponse({"session_token": session_token, "username": tokens.username})


@mcp.custom_route("/auth/salesforce/logout", methods=["POST"])
async def salesforce_logout(request: Request) -> JSONResponse:
    """Delete the session from the token store."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        session_token = auth[7:]
        await _token_store.delete(session_token)
        log.info("Session deleted session=%s", session_token)
        return JSONResponse({"status": "logged_out"})
    return JSONResponse({"error": "missing_bearer_token"}, status_code=400)


# ──────────────────────────────────────────────────────────────────────────────
# Session resolution (used by every MCP tool call)
# ──────────────────────────────────────────────────────────────────────────────

async def _resolve_session(session_token: str) -> SalesforceCredentials:
    """Resolve a session UUID to live Salesforce credentials.

    - Looks up the session in the token store.
    - Auto-refreshes the access token if it is about to expire.
    - Raises ``RuntimeError`` (with a re-auth hint) on any unrecoverable error.
    """
    tokens = await _token_store.get(session_token)
    if tokens is None:
        raise RuntimeError(
            f"Session not found. Re-authenticate at "
            f"{_RESOURCE_URI}/auth/salesforce/login"
        )

    if tokens.is_expired():
        if not tokens.refresh_token:
            await _token_store.delete(session_token)
            raise RuntimeError(
                "Session expired and no refresh token is available. "
                f"Re-authenticate at {_RESOURCE_URI}/auth/salesforce/login"
            )
        try:
            refreshed = await refresh_access_token(
                refresh_token=tokens.refresh_token,
                client_id=_SF_CLIENT_ID,
                client_secret=_SF_CLIENT_SECRET,
                login_url=_SF_LOGIN_URL,
            )
            new_tokens = StoredTokens.from_token_response(refreshed)
            # Salesforce does not rotate refresh tokens by default; preserve ours.
            if not new_tokens.refresh_token:
                new_tokens.refresh_token = tokens.refresh_token
            # Preserve identity fields that aren't in a refresh response.
            if not new_tokens.user_id:
                new_tokens.user_id = tokens.user_id
                new_tokens.username = tokens.username
            await _token_store.save(session_token, new_tokens)
            tokens = new_tokens
        except SalesforceAuthError as exc:
            await _token_store.delete(session_token)
            raise RuntimeError(
                f"Token refresh failed (session invalidated): {exc}. "
                f"Re-authenticate at {_RESOURCE_URI}/auth/salesforce/login"
            ) from exc

    return SalesforceCredentials(
        access_token=tokens.access_token,
        instance_url=tokens.instance_url,
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


register_salesforce_tools(mcp, _extract_session_token, _resolve_session)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
