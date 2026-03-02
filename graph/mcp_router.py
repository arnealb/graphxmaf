import inspect
import yaml
from mcp.server.fastmcp import Context
from graph.repository import GraphRepository
from auth.token_credential import StaticTokenCredential

_repo_cache: dict[str, GraphRepository] = {}


def get_repo(token, azure_settings):
    if token not in _repo_cache:
        _repo_cache[token] = GraphRepository(
            azure_settings,
            credential=StaticTokenCredential(token),
        )
    return _repo_cache[token]


def load_endpoints(path="graph/endpoints.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def register_graph_tools(mcp, azure_settings, extract_token):
    endpoints = load_endpoints()

    def make_handler(ep):
        path_params = ep.get("pathParams", [])
        query_params = ep.get("query", [])

        # The body uses **kwargs so individual named arguments land here
        # regardless of what __signature__ advertises (see below).
        async def handler(ctx: Context, **kwargs):
            token = extract_token(ctx)
            repo = get_repo(token, azure_settings)

            path = ep["path"]
            for p in path_params:
                if p in kwargs:
                    path = path.replace(f"{{{p}}}", str(kwargs[p]))

            query = {}
            for q in query_params:
                if kwargs.get(q) is not None:
                    query[f"${q}"] = kwargs[q]

            data = await repo.raw(
                path,
                ep.get("method", "GET"),
                query=query,
            )
            return str(data)


        sig_params = [
            inspect.Parameter("ctx", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Context),
        ]
        for p in path_params:
            sig_params.append(
                inspect.Parameter(p, inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=str)
            )
        for q in query_params:
            sig_params.append(
                inspect.Parameter(q, inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=str | None, default=None)
            )

        handler.__signature__ = inspect.Signature(sig_params)

        return handler

    for ep in endpoints:
        tool_name = f"graph-{ep['name']}"
        print("tool_name:", tool_name)
        mcp.tool(name=tool_name)(make_handler(ep))
