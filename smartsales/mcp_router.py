# mcp_router.py
import inspect
import json
from typing import Any, Callable, Awaitable

import yaml
from mcp.server.fastmcp import Context

from smartsales.auth import SmartSalesCredentials
from smartsales.repository import SmartSalesRepository

_TYPE_MAP: dict[str, type] = {
    "str":              str,
    "str | None":       str | None,
    "str | dict | None": str | dict | None,
    "int":              int,
    "int | None":       int | None,
    "bool":             bool,
    "bool | None":      bool | None,
    "any":              Any,
}

# Cache keyed by session_token → (SmartSalesRepository, cached_access_token).
# A new repo is created automatically when the access token is refreshed.
_repo_cache: dict[str, tuple[SmartSalesRepository, str]] = {}


def _get_repo(session_token: str, access_token: str) -> SmartSalesRepository:
    cached = _repo_cache.get(session_token)
    if cached is None or cached[1] != access_token:
        repo = SmartSalesRepository(access_token=access_token)
        _repo_cache[session_token] = (repo, access_token)
    return _repo_cache[session_token][0]


def _load_tools(path: str = "smartsales/tools.yaml") -> list[dict]:
    with open(path) as f:
        return yaml.safe_load(f)


def register_smartsales_tools(
    mcp,
    extract_session_token: Callable[[Context], str],
    resolve_session: Callable[[str], Awaitable[SmartSalesCredentials]],
) -> None:
    for tool_def in _load_tools():
        _register_one(mcp, extract_session_token, resolve_session, tool_def)


def _register_one(mcp, extract_session_token, resolve_session, tool_def: dict) -> None:
    repo_method = tool_def["method"]
    params = tool_def.get("params", [])

    async def handler(ctx: Context, _m=repo_method, **kwargs):
        # LLM geeft q soms door als dict ipv JSON string — omzetten naar string
        kwargs = {k: json.dumps(v) if isinstance(v, dict) else v for k, v in kwargs.items()}

        session_token = extract_session_token(ctx)
        creds = await resolve_session(session_token)
        repo = _get_repo(session_token, creds.access_token)
        return await getattr(repo, _m)(**kwargs)

    sig_params = [
        inspect.Parameter("ctx", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Context),
    ]
    for p in params:
        py_type = _TYPE_MAP.get(p.get("type", "str"), str)

        if "default" in p:
            default = p["default"]
        elif "None" in p.get("type", ""):
            default = None
        else:
            default = inspect.Parameter.empty

        sig_params.append(
            inspect.Parameter(
                p["name"],
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=py_type,
                default=default,
            )
        )

    handler.__signature__ = inspect.Signature(sig_params)
    handler.__name__ = tool_def["name"]

    mcp.tool(name=tool_def["name"], description=tool_def.get("description", ""))(handler)
