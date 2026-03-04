# Document Reasoning Improvements

## Problem

The agent handled multi-turn document conversations poorly. Five concrete issues:

1. Vague follow-ups ("there should be another one") were not connected to the current topic
2. Conversation context (e.g. topic = Nutella) was not maintained across turns
3. Answers did not cite which file they came from
4. When asked about file content, the agent re-listed file names instead of reading them
5. When multiple files were relevant, the agent didn't synthesize them into one answer

Root cause: the system prompt had no rules for context continuity, source attribution, or read-vs-list decisions, and there was no efficient way to read multiple files in one call.

---

## Changes

### 1. `entities/graph_agent.py` — `read_multiple_files`

New method that accepts a comma-separated string of file IDs, calls `read_file` for each, and returns all content joined by `---` separators so the model can attribute content per file.

### 2. `graph/tools.yaml` — register `read_multiple_files`

Registered the new method as an MCP tool with a description that instructs the model to use it when a question spans multiple documents.

### 3. `entities/document_context.py` — `DocumentContextProvider` (new file)

A `BaseContextProvider` that maintains structured document state across conversation turns using `session.state`. Two hooks:

**`before_run`**
Reads `session.state["doc_context"]` and injects a compact system message before each turn:
```
[Session Context]
Current topic: nutella
Last search: "nutella origin"
Files found: nutella_recipe.docx (id1), nutella_history.docx (id2)
```
Nothing is injected on the first turn (no state yet).

**`after_run`**
Scans `context.response.messages` for `function_call`/`function_result` content pairs. When `search_files` was called, extracts the query and parses `ID:`/`Name:` lines from the result, then persists into `session.state["doc_context"]`. The DevUI manages sessions automatically, so this state survives across turns.

> **Implementation note:** `FunctionMiddleware` was considered but ruled out — `FunctionInvocationContext.metadata` is a separate dict from `SessionContext.metadata`, so the two cannot share state. `after_run` already has access to both the response messages and the session, making middleware unnecessary.
>
> MCP tools in this framework use `function_call`/`function_result` content types (not `mcp_server_tool_call`/`mcp_server_tool_result`), confirmed by reading `agent_framework/_mcp.py`.

### 4. `agent.py` — wired provider + updated instructions

- Added `context_providers=[DocumentContextProvider()]` to the `Agent` constructor (works transparently with `serve()` — no changes to `main.py` needed).
- Replaced hardcoded context-continuity examples in the instructions with a short description of the injected `[Session Context]` block. Instructions are now the behavioral contract; the provider supplies the actual live data.
- Added `read_multiple_files` to the tool list and DOCUMENT WORKFLOW rules.

### 5. `main.py` — logging setup

Added `logging.basicConfig` so log output from `DocumentContextProvider` is visible in the terminal. Noisy libraries (`httpx`, `httpcore`, `mcp`) silenced to `WARNING`.

---

## Log output

When running, you'll see lines like:

```
12:34:01  INFO   entities.document_context — [doc_ctx] before_run: no session context yet, skipping injection
12:34:05  INFO   entities.document_context — [doc_ctx] after_run: saw tool call — search_files({'query': 'nutella'})
12:34:05  INFO   entities.document_context — [doc_ctx] after_run: search_files(query='nutella') → found 2 file(s): ['nutella_recipe.docx', 'nutella_history.docx']
12:34:07  INFO   entities.document_context — [doc_ctx] before_run: injecting context:
[Session Context]
Current topic: nutella
Last search: "nutella"
Files found: nutella_recipe.docx (id1), nutella_history.docx (id2)
```

---

## Files changed

| File | Change |
|------|--------|
| `entities/graph_agent.py` | Added `read_multiple_files` method |
| `entities/document_context.py` | New file — `DocumentContextProvider` |
| `graph/tools.yaml` | Registered `read_multiple_files` tool |
| `agent.py` | Wired provider, updated instructions |
| `main.py` | Added `logging.basicConfig` |
