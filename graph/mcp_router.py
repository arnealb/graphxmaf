import inspect
import yaml
from datetime import datetime

from mcp.server.fastmcp import Context

from graph.repository import GraphRepository
from graph.models import User
from auth.token_credential import StaticTokenCredential

_TYPE_MAP: dict[str, type] = {
    "str":       str,
    "str | None": str | None,
    "int":       int,
    "int | None": int | None,
}

_repo_cache: dict[str, GraphRepository] = {}

import logging
log = logging.getLogger("graph")
log.setLevel(logging.INFO)


def _get_repo(token: str, azure_settings) -> GraphRepository:
    if token not in _repo_cache:
        _repo_cache[token] = GraphRepository(azure_settings, credential=StaticTokenCredential(token))
    return _repo_cache[token]


# ---------------------------------------------------------------------------
# Per-tool dispatch functions
# ---------------------------------------------------------------------------

async def _whoami(repo: GraphRepository, **kwargs):
    user = await repo.get_user()
    return User(
        display_name=user.display_name,
        email=user.mail or user.user_principal_name,
    )


async def _find_people(repo: GraphRepository, name: str, **kwargs):
    log.info("[findpeople] tool called with name=%r", name)
    return await repo.find_people(name)


async def _list_email(repo: GraphRepository, **kwargs):
    emails = await repo.get_inbox()
    return [e.model_dump(mode="json") for e in emails]

async def _read_email(repo: GraphRepository, message_id: str, **kwargs):
    result = await repo.get_message_body(message_id)
    if not result:
        return {"error": "Email not found"}
    return result.model_dump(mode="json")


async def _search_documents(repo: GraphRepository, query: str, **kwargs):
    from graph.graphrag_searcher import search_documents
    return await search_documents(query)


async def _search_files(repo: GraphRepository, query: str, drive_id=None, folder_id="root", **kwargs):
    import re
    filetype_match = re.search(r'\bfiletype:(\w+)\b', query, re.IGNORECASE)
    if filetype_match:
        ext = "." + filetype_match.group(1).lower()
        base = re.sub(r'\bfiletype:\w+\b', "", query, flags=re.IGNORECASE).strip()
        results = await repo.search_drive_items_sdk(query=base or ext, top=25, drive_id=drive_id)
        return [f for f in results if f.name.lower().endswith(ext)]
    return await repo.search_drive_items_sdk(query=query, top=25, drive_id=drive_id)


async def _read_file(repo: GraphRepository, file_id: str, **kwargs):
    return await repo.get_file_text(file_id)


async def _read_multiple_files(repo: GraphRepository, file_ids: str, **kwargs):
    ids = [fid.strip() for fid in file_ids.split(",") if fid.strip()]
    return await repo.get_files_text_batch(ids)


async def _list_contacts(repo: GraphRepository, **kwargs):
    return await repo.get_contacts()


async def _list_calendar(repo: GraphRepository, **kwargs):
    upcoming = await repo.get_upcoming_events()
    past = await repo.get_past_events()
    return upcoming + past


def _parse_dt(s) -> datetime | None:
    if isinstance(s, str):
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            return None
    return s


async def _search_events(
    repo: GraphRepository,
    text=None, location=None, attendee=None,
    start_after=None, start_before=None,
    **kwargs,
):
    return await repo.search_events(
        text=text,
        location=location,
        attendee_query=attendee,
        start_after=_parse_dt(start_after),
        start_before=_parse_dt(start_before),
    )


_DISPATCH = {
    "whoami":              _whoami,
    "find_people":         _find_people,
    "list_email":          _list_email,
    "read_email":          _read_email,
    "search_documents":    _search_documents,
    "search_files":        _search_files,
    "read_file":           _read_file,
    "read_multiple_files": _read_multiple_files,
    "list_contacts":       _list_contacts,
    "list_calendar":       _list_calendar,
    "search_events":       _search_events,
}


# ---------------------------------------------------------------------------

def _load_tools(path: str = "graph/tools.yaml") -> list[dict]:
    with open(path) as f:
        return yaml.safe_load(f)


def register_graph_tools(mcp, azure_settings, extract_token) -> None:
    for tool_def in _load_tools():
        _register_one(mcp, azure_settings, extract_token, tool_def)


def _register_one(mcp, azure_settings, extract_token, tool_def: dict) -> None:
    method_name = tool_def["method"]
    params = tool_def.get("params", [])

    async def handler(ctx: Context, _m=method_name, **kwargs):
            token = extract_token(ctx)
            # Support async extract_token (voor OBO)
            if inspect.isawaitable(token):
                token = await token
            repo = _get_repo(token, azure_settings)
            fn = _DISPATCH.get(_m)
            if fn:
                return await fn(repo, **kwargs)
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
