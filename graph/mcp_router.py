import inspect
import os
import yaml

from mcp.server.fastmcp import Context

from graph.repository import GraphRepository
from auth.token_credential import StaticTokenCredential
from entities.graph_agent import GraphAgent

_TYPE_MAP: dict[str, type] = {
    "str":       str,
    "str | None": str | None,
    "int":       int,
    "int | None": int | None,
}

_agent_cache: dict[str, GraphAgent] = {}


def _get_agent(token: str, azure_settings) -> GraphAgent:
    if token not in _agent_cache:
        repo = GraphRepository(azure_settings, credential=StaticTokenCredential(token))
        _agent_cache[token] = GraphAgent(repo)
    return _agent_cache[token]


def _load_tools(path: str = "graph/tools.yaml") -> list[dict]:
    with open(path) as f:
        return yaml.safe_load(f)


def register_graph_tools(mcp, azure_settings, extract_token) -> None:
    for tool_def in _load_tools():
        _register_one(mcp, azure_settings, extract_token, tool_def)


def _register_one(mcp, azure_settings, extract_token, tool_def: dict) -> None:
    agent_method = tool_def["method"]
    params = tool_def.get("params", [])

    # _m=agent_method captures the loop variable by value
    async def handler(ctx: Context, _m=agent_method, **kwargs):
        token = extract_token(ctx)
        agent = _get_agent(token, azure_settings)
        return await getattr(agent, _m)(**kwargs)

    # FastMCP introspects __signature__ to build the JSON schema for the LLM.
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
