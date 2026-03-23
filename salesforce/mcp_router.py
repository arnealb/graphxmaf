# mcp_router.py
import inspect
from typing import Callable, Awaitable

import yaml

from mcp.server.fastmcp import Context

from salesforce.auth import SalesforceCredentials
from salesforce.repository import SalesforceRepository

_TYPE_MAP: dict[str, type] = {
    "str":                  str,
    "str | None":           str | None,
    "int":                  int,
    "int | None":           int | None,
    "list[str] | None":     list[str] | None,
    "dict[str, str] | None": dict[str, str] | None,
}

# tools.yaml uses "find_accounts" but the repo method is "get_accounts"
_SF_METHOD_ALIASES = {
    "find_accounts": "get_accounts",
}

# Cache keyed by session_token → (SalesforceRepository, cached_access_token).
# When the access token is refreshed the cached_access_token won't match and a
# fresh repo is created automatically.
_repo_cache: dict[str, tuple[SalesforceRepository, str]] = {}


def _get_repo(session_token: str, access_token: str, instance_url: str) -> SalesforceRepository:
    cached = _repo_cache.get(session_token)
    if cached is None or cached[1] != access_token:
        repo = SalesforceRepository(access_token=access_token, instance_url=instance_url)
        _repo_cache[session_token] = (repo, access_token)
    return _repo_cache[session_token][0]


def _load_tools(path: str = "salesforce/tools.yaml") -> list[dict]:
    with open(path) as f:
        return yaml.safe_load(f)


def register_salesforce_tools(
    mcp,
    extract_session_token: Callable[[Context], str],
    resolve_session: Callable[[str], Awaitable[SalesforceCredentials]],
) -> None:
    for tool_def in _load_tools():
        _register_one(mcp, extract_session_token, resolve_session, tool_def)


def _register_one(mcp, extract_session_token, resolve_session, tool_def: dict) -> None:
    repo_method = tool_def["method"]
    params = tool_def.get("params", [])

    async def handler(ctx: Context, _m=repo_method, **kwargs):
        session_token = extract_session_token(ctx)
        creds = await resolve_session(session_token)
        repo = _get_repo(session_token, creds.access_token, creds.instance_url)
        actual = _SF_METHOD_ALIASES.get(_m, _m)
        return await getattr(repo, actual)(**kwargs)

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
