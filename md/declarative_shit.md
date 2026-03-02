  The Plan

  The core idea: move tool definitions to YAML, and write a router that reads them and registers tools
   dynamically against GraphAgent methods. mcp_api_tool.py becomes just a thin entry point.

  What changes

  1. graph/tools.yaml — declare every tool:
  - name: whoami
    description: Identify the authenticated user
    method: whoami

  - name: findpeople
    description: Resolve a person name to email addresses
    method: find_people
    params:
      - name: name
        type: str

  - name: search_email
    description: Search emails by sender, subject, or date
    method: search_emails
    params:
      - name: sender
        type: "str | None"
      - name: subject
        type: "str | None"
      - name: received_after
        type: "str | None"
      - name: received_before
        type: "str | None"
  # ... etc

  2. graph/mcp_router.py — reads the YAML, creates handler closures, registers with FastMCP:
  async def handler(ctx: Context, _method=entry["method"], **kwargs):
      token = extract_token(ctx)
      agent = get_agent(token, azure_settings)
      return await getattr(agent, _method)(**kwargs)

  handler.__signature__ = inspect.Signature(sig_params)  # FastMCP needs this
  mcp.tool(name=tool_def["name"])(handler)

  The inspect.Signature is unavoidable — FastMCP introspects it to generate the JSON schema for the
  LLM. But here it's cleaner because the types come from a controlled YAML type map, not arbitrary
  manipulation.

  3. mcp_api_tool.py — drops all @mcp.tool() decorators, just calls register_graph_tools(mcp, ...).
  ~60 lines become ~20.

  ---
  What stays the same

  - GraphAgent — all business logic untouched
  - GraphRepository — untouched
  - main.py / agent.py — untouched
  - Token caching (moved into mcp_router.py)

  ---
  What you gain

  - Adding a new Graph endpoint = add a YAML entry, zero Python
  - mcp_api_tool.py is readable at a glance
  - Tool descriptions live next to their definitions, not scattered in decorators

Want me to implement it?