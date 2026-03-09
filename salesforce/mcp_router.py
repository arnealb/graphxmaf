import inspect
import yaml

from mcp.server.fastmcp import Context

from salesforce.repository import SalesforceRepository
from salesforce.agent import SalesforceAgent

_TYPE_MAP: dict[str, type] = {
    "str":        str,
    "str | None": str | None,
    "int":        int,
    "int | None": int | None,
}

_agent_cache: dict[str, SalesforceAgent] = {}


def _get_agent(token: str, instance_url: str) -> SalesforceAgent:
    if token not in _agent_cache:
        repo = SalesforceRepository(access_token=token, instance_url=instance_url)
        _agent_cache[token] = SalesforceAgent(repo)
    return _agent_cache[token]


def _load_tools(path: str = "salesforce/tools.yaml") -> list[dict]:
    with open(path) as f:
        return yaml.safe_load(f)


def register_salesforce_tools(mcp, instance_url: str, extract_token) -> None:
    for tool_def in _load_tools():
        _register_one(mcp, instance_url, extract_token, tool_def)


def _register_one(mcp, instance_url: str, extract_token, tool_def: dict) -> None:
    agent_method = tool_def["method"]
    params = tool_def.get("params", [])

    async def handler(ctx: Context, _m=agent_method, **kwargs):
        token = extract_token(ctx)
        agent = _get_agent(token, instance_url)
        return await getattr(agent, _m)(**kwargs)

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
