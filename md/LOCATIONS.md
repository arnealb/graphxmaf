# SmartSales — Locations Module

> Implemented: 2026-03-25

## Overview

Read-only access to SmartSales location data via 5 MCP tools. All tools are registered dynamically from `tools.yaml` via `mcp_router.py` and execute against the SmartSales REST API through `repository.py`.

## Tools

| Tool | Method | Endpoint |
|---|---|---|
| `get_location` | GET | `/api/v3/location/{uid}` |
| `list_locations` | GET | `/api/v3/location/list` |
| `list_queryable_fields` | GET | `/api/v3/location/list/queryableFields` |
| `list_sortable_fields` | GET | `/api/v3/location/list/sortableFields` |
| `list_displayable_fields` | GET | `/api/v3/location/list/displayableFields` |

### `get_location`
Fetches a single location by its uid. Returns the full raw LocationDTO from the API.

### `list_locations`
Queries locations using SmartSales-native parameters:
- `q` — JSON filter string, e.g. `{"city":"contains:knokke","country":"eq:Belgium"}`
- `s` — sort expression, e.g. `"name:asc"`
- `p` — projection level: `"minimal"`, `"simple"`, `"fullWithColor"`, `"full"` (default: `"fullWithColor"`)
- `d` — comma-separated field list to include in the response
- `nextPageToken` — pagination token from a previous response
- `skipResultSize` — skip total count calculation (default: `false`)

Returns `{ locations: [...], nextPageToken, resultSizeEstimate }`.

### `list_queryable_fields` / `list_sortable_fields` / `list_displayable_fields`
Return field metadata from the API. Used by the agent when a user asks which fields are available to filter, sort, or display on. All three are served from the in-memory cache (see below).

## Field Cache

On server startup, `mcp_server.py` calls `repo.warm_field_cache()` which pre-fetches all three field lists and stores them in the module-level `_field_cache` dict in `repository.py`. The cache lives for the lifetime of the MCP server process (no TTL — field definitions are static schema data).

```
_field_cache = {
    "queryable":   [...],   # fields valid in q
    "sortable":    [...],   # fields valid in s
    "displayable": [...],   # fields valid for display
}
```

## Server-side Field Validation

`list_locations` validates `q` and `s` against the cache before making any API call:
- Parses field names out of the `q` JSON and checks them against `_field_cache["queryable"]`
- Parses the field name out of `s` and checks it against `_field_cache["sortable"]`
- Returns `{"error": "Unknown filter field(s): ..."}` immediately if any field is invalid — no API call is made

This means the agent never needs to call the field list tools for validation; they exist solely for answering user questions about available fields.

## LLM → API Parameter Handling

The LLM sometimes passes `q` as a dict `{"city": "eq:Leuven"}` instead of a JSON string. The handler in `mcp_router.py` coerces any dict kwarg to a JSON string before passing it to the repository:

```python
kwargs = {k: json.dumps(v) if isinstance(v, dict) else v for k, v in kwargs.items()}
```

## Files

| File | Role |
|---|---|
| `tools.yaml` | Tool definitions (name, description, method, params) |
| `mcp_router.py` | Dynamically builds FastMCP tool handlers from tools.yaml |
| `repository.py` | Async HTTP client for the SmartSales REST API + field cache |
| `mcp_server.py` | FastMCP server, auth/session management, cache warm-up on startup |
| `auth.py` | Env-based authentication (no browser OAuth) |
| `token_store.py` | File-backed token persistence |
