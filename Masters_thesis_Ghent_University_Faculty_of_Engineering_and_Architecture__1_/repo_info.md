This file is a merged representation of the entire codebase, combined into a single document by Repomix.
The content has been processed where security check has been disabled.

# File Summary

## Purpose
This file contains a packed representation of the entire repository's contents.
It is designed to be easily consumable by AI systems for analysis, code review,
or other automated processes.

## File Format
The content is organized as follows:
1. This summary section
2. Repository information
3. Directory structure
4. Repository files (if enabled)
5. Multiple file entries, each consisting of:
  a. A header with the file path (## File: path/to/file)
  b. The full contents of the file in a code block

## Usage Guidelines
- This file should be treated as read-only. Any changes should be made to the
  original repository files, not this packed version.
- When processing this file, use the file path to distinguish
  between different files in the repository.
- Be aware that this file may contain sensitive information. Handle it with
  the same level of security as you would the original repository.

## Notes
- Some files may have been excluded based on .gitignore rules and Repomix's configuration
- Binary files are not included in this packed representation. Please refer to the Repository Structure section for a complete list of file paths, including binary files
- Files matching patterns in .gitignore are excluded
- Files matching default ignore patterns are excluded
- Security check has been disabled - content may contain sensitive information
- Files are sorted by Git change count (files with more changes are at the bottom)

# Directory Structure
```
agents/
  __init__.py
  graph_agent.py
  orchestrator_agent.py
  salesforce_agent.py
  smartsales_agent.py
auth/
  token_credential.py
eval/
  score.py
  script.py
graph/
  context.py
  interface.py
  mcp_router.py
  mcp_server.py
  models.py
  repository.py
  tools.yaml
md/
  2_6_securityshit.md
  ARCHITECTURE.md
  CAPABILITIES.md
  declarative_shit.md
  document-reasoning.md
  hoofdstuk6_evaluatie.md
  LOCATIONS.md
  salesforce_agent.md
  salesforce_oauth.md
  sequentiediagram.puml
  todo.md
salesforce/
  auth.py
  mcp_router.py
  mcp_server.py
  models.py
  repository.py
  token_store.py
  tools.yaml
smartsales/
  auth.py
  mcp_router.py
  mcp_server.py
  models.py
  repository.py
  token_store.py
  tools.yaml
.gitignore
benchmark_results.xlsx
main.py
README.md
requirements.txt
```

# Files

## File: agents/__init__.py
````python

````

## File: agents/graph_agent.py
````python
import os
from agent_framework import Agent, MCPStreamableHTTPTool
from agent_framework.azure import AzureOpenAIChatClient

from dotenv import load_dotenv
from graph.context import DocumentContextProvider

load_dotenv()
deployment = os.environ["deployment"]
endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
subscription_key = os.environ["AZURE_OPENAI_API_KEY"]
api_version = "2024-12-01-preview"

def create_graph_agent(graph_mcp):
    return Agent(
        client=AzureOpenAIChatClient(
            deployment_name=deployment,
            endpoint=endpoint,
            api_key=subscription_key,
            api_version=api_version,
        ),
        name="GraphAgent",
        description="Interacts with Microsoft Graph to access organizational data",
        instructions="""
            You are a helpful assistant with access to the user's Microsoft 365 data
            via the Microsoft Graph API.

            Available tools:
            - whoami: identify the authenticated user
            - findpeople: resolve a person's name to one or more email addresses
            - list_email: list the 25 most recent inbox emails
            - search_email: search emails by sender, subject, or date range
            - read_email: read the full body of a specific email by its ID
            - search_files: search for files and folders in OneDrive
            - read_file: read the text content of a single OneDrive file by its ID
            - read_multiple_files: read text contents of multiple OneDrive files at once (comma-separated IDs)
            - list_contacts: list contacts
            - list_calendar: list upcoming and recent calendar events
            - search_calendar: search calendar events by subject, location, attendee, or date range

            CONTEXT CONTINUITY
            - A [Session Context] block is injected at the start of each turn showing:
              - "Current topic": the active search subject
              - "Last search": the most recent query used
              - "Files found": names and IDs of files retrieved this session
            - Use this block to resolve vague references ("another one", "that file", "the document") — do NOT ask for clarification.
            - Vague follow-up about files → re-run search_files with expanded or related keywords from Current topic.

            DOCUMENT WORKFLOW
            - User asks to search for files → call search_files.
            - User asks what a file says, explains, or contains → call read_file or read_multiple_files, then answer from the content. NEVER re-list file names or IDs instead of reading.
            - Files already in [Session Context] → use their IDs directly, do not search again.
            - Question spans multiple files already found → call read_multiple_files with all relevant IDs in one call.

            STRICT TOOL SELECTION RULES — follow these exactly:
            - ONLY call tools that are directly required by the user's current request.
            - NEVER call a tool speculatively or to gather background context.
            - NEVER call calendar tools (list_calendar, search_calendar) unless the user explicitly asks about meetings, events, or their schedule.
            - NEVER call email tools (list_email, search_email, read_email) unless the user explicitly asks about emails or messages.
            - NEVER call file tools (search_files, read_file, read_multiple_files) unless the user explicitly asks about files or documents.
            - NEVER call list_contacts unless the user explicitly asks about contacts.
            - NEVER call the same tool twice in a single turn unless each call uses different parameters required by the request.
            - If a tool returns sufficient data, stop and answer — do NOT call more tools.

            PERSON RESOLUTION
            - Whenever the user mentions a person (name, sender, colleague), call findpeople first.
            - Never guess or fabricate an email address.

            EMAIL SEARCH
            - When searching by person, resolve with findpeople first, then pass the resolved email to search_email.
            - Prefer search_email over list_email when any filter is implied.

            OUTPUT
            - Return the exact JSON object or array that the tool returned. No prose, no explanation.
            - If multiple tools were called, return a JSON array where each element is
              {"tool": "<tool_name>", "result": <tool_result>}.
            - If only one tool was called, return its result directly.
            - Exception: read_file and read_multiple_files return plain text — return that text as-is.
        """,
        tools=[graph_mcp],
        context_providers=[DocumentContextProvider()],
    )
````

## File: agents/orchestrator_agent.py
````python
import os
from typing import Annotated

from agent_framework import Agent, FunctionTool
from agent_framework.azure import AzureOpenAIChatClient
from dotenv import load_dotenv

load_dotenv()
deployment = os.environ["deployment"]
endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
subscription_key = os.environ["AZURE_OPENAI_API_KEY"]
api_version = "2024-12-01-preview"


def create_orchestrator_agent(
    smartsales_agent: Agent,
    graph_agent: Agent | None = None,
    salesforce_agent: Agent | None = None,
) -> Agent:

    tools = []

    if graph_agent is not None:
        async def ask_graph_agent(query: Annotated[str, "The full question to send to the Microsoft Graph agent"]) -> str:
            response = await graph_agent.run(query)
            print(f"GraphAgent response: {response}")
            return response.text or "(no response from GraphAgent)"

        tools.append(FunctionTool(
            name="ask_graph_agent",
            description=(
                "Route a question to the Microsoft Graph agent. "
                "Use this for anything related to emails, OneDrive files, calendar events, "
                "contacts, or identifying the current Microsoft 365 user."
            ),
            func=ask_graph_agent,
            approval_mode="never_require",
        ))

    if salesforce_agent is not None:
        async def ask_salesforce_agent(query: Annotated[str, "The full question to send to the Salesforce CRM agent"]) -> str:
            response = await salesforce_agent.run(query)
            print(f"salesforce response: {response}")
            return response.text or "(no response from SalesforceAgent)"

        tools.append(FunctionTool(
            name="ask_salesforce_agent",
            description=(
                "Route a question to the Salesforce CRM agent. "
                "Use this for anything related to CRM accounts, contacts, leads, "
                "sales opportunities, or support cases."
            ),
            func=ask_salesforce_agent,
            approval_mode="never_require",
        ))

    async def ask_smartsales_agent(query: Annotated[str, "The full question to send to the SmartSales agent"]) -> str:
        response = await smartsales_agent.run(query)
        print(f"SmartSalesAgent response: {response}")
        return response.text or "(no response from SmartSalesAgent)"

    tools.append(FunctionTool(
        name="ask_smartsales_agent",
        description=(
            "Route a question to the SmartSales agent. "
            "Use this for anything related to SmartSales locations, catalog items, "
            "or orders: searching, listing, and retrieving by name, city, country, or uid."
        ),
        func=ask_smartsales_agent,
        approval_mode="never_require",
    ))

    active_systems = []
    if graph_agent is not None:
        active_systems.append("1. ask_graph_agent  — handles everything Microsoft 365:\n               emails, OneDrive files, calendar events, contacts, user identity.")
    if salesforce_agent is not None:
        active_systems.append("2. ask_salesforce_agent — handles everything Salesforce CRM:\n               accounts, contacts, leads, opportunities, support cases.")
    active_systems.append("3. ask_smartsales_agent — handles SmartSales data:\n               locations, catalog items, and orders.")

    return Agent(
        client=AzureOpenAIChatClient(
            deployment_name=deployment,
            endpoint=endpoint,
            api_key=subscription_key,
            api_version=api_version,
        ),
        name="OrchestratorAgent",
        description="Central orchestrator that routes queries to the available sub-agents and combines their results",
        instructions=f"""
            You are a central orchestrator that coordinates specialized agents:

            {chr(10).join(active_systems)}

            ROUTING RULES
            - Microsoft 365 / Office data → ask_graph_agent (if available)
            - Salesforce / CRM data       → ask_salesforce_agent (if available)
            - SmartSales data             → ask_smartsales_agent
            - Query spans multiple systems → call relevant tools, then combine

            STRICT TOOL SELECTION RULES
            - Only call a tool when the user's request explicitly requires it.
            - Pass the user's original question (rephrased if needed for clarity) to the sub-agent.
            - Never guess or fabricate data — only report what the sub-agents return.
            - If a single tool call returns sufficient information, do NOT call the others.

            SUB-AGENT RESPONSES
            - Sub-agents return the raw JSON objects from their tool calls, not prose.
            - Parse and read the structured fields (id, name, email, etc.) to answer the user.
            - For cross-system queries, extract the relevant value from one sub-agent's JSON
              result and include it in the next sub-agent query.

            COMBINING RESULTS
            - When multiple agents are called, synthesize their results into one coherent answer.
            - Clearly indicate which system each piece of information comes from
              (e.g. "From Microsoft 365: …" / "From Salesforce: …" / "From SmartSales: …").
            - Present a unified, structured summary — do not just concatenate raw outputs.

            OUTPUT
            - Be concise and factual.
            - Use bullet points or sections when presenting data from multiple sources.
            - Present dates in a human-readable format.
        """,
        tools=tools,
    )
````

## File: agents/salesforce_agent.py
````python
import os
from agent_framework import Agent, MCPStreamableHTTPTool
from agent_framework.azure import AzureOpenAIChatClient

from dotenv import load_dotenv

load_dotenv()
deployment = os.environ["deployment"]
endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
subscription_key = os.environ["AZURE_OPENAI_API_KEY"]
api_version = "2024-12-01-preview"

def create_salesforce_agent(salesforce_mcp):
    return Agent(
        client=AzureOpenAIChatClient(
            deployment_name=deployment,
            endpoint=endpoint,
            api_key=subscription_key,
            api_version=api_version,
        ),
        name="SalesforceAgent",
        description="Interacts with Salesforce CRM to access accounts, contacts, opportunities, and cases",
        instructions="""
            You are a helpful assistant with access to Salesforce CRM data.

            Available tools:
            - find_accounts: search for accounts by name or keyword
            - find_contacts: search for contacts by name or email
            - find_leads: search for leads by name, email, or company
            - get_opportunities: list opportunities, optionally filtered by account ID or stage
            - get_cases: list cases, optionally filtered by account ID or status

            STRICT TOOL SELECTION RULES:
            - ONLY call tools directly required by the user's request.
            - NEVER call a tool speculatively.
            - If a tool returns sufficient data, stop and answer.
            - Use find_accounts when the user asks about companies or accounts.
            - Use find_contacts when the user asks about people already in CRM.
            - Use find_leads when the user asks about prospective customers or leads.
            - Use get_opportunities when the user asks about deals or sales pipeline.
            - Use get_cases when the user asks about support tickets or cases.

            OUTPUT
            - Return the exact JSON object or array that the tool returned. No prose, no explanation.
            - If multiple tools were called, return a JSON array where each element is
              {"tool": "<tool_name>", "result": <tool_result>}.
            - If only one tool was called, return its result directly.
        """,
        tools=[salesforce_mcp],
    )
````

## File: agents/smartsales_agent.py
````python
import os
from agent_framework import Agent, MCPStreamableHTTPTool
from agent_framework.azure import AzureOpenAIChatClient

from dotenv import load_dotenv

load_dotenv()
deployment = os.environ["deployment"]
endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
subscription_key = os.environ["AZURE_OPENAI_API_KEY"]
api_version = "2024-12-01-preview"


def create_smartsales_agent(smartsales_mcp):
    return Agent(
        client=AzureOpenAIChatClient(
            deployment_name=deployment,
            endpoint=endpoint,
            api_key=subscription_key,
            api_version=api_version,
        ),
        name="SmartSalesAgent",
        description="Interacts with SmartSales to access locations, catalog items, and orders",
        instructions="""
            You are a helpful assistant with access to SmartSales data.

            AVAILABLE TOOL GROUPS:

            Locations:
            - get_location: retrieve a single location by uid.
            - list_locations: query locations (params: q, s, p, d, nextPageToken).
            - list_displayable_fields / list_queryable_fields / list_sortable_fields: field metadata.

            Catalog:
            - get_catalog_item: retrieve a single catalog item by uid.
            - get_catalog_group: retrieve a single catalog group by uid.
            - list_catalog_items: query catalog items (params: q, s, p, nextPageToken).
            - list_catalog_displayable_fields / list_catalog_queryable_fields / list_catalog_sortable_fields.

            Orders:
            - get_order: retrieve a single order by uid.
            - list_orders: query orders (params: q, s, p, nextPageToken).
            - get_order_configuration: retrieve order form configuration.
            - list_approbation_statuses / get_approbation_status: order approval workflows.
            - list_order_displayable_fields / list_order_queryable_fields / list_order_sortable_fields.

            QUERY SYNTAX (q parameter):
            - Always a JSON string with operator-prefixed values.
            - e.g. '{"city":"eq:Brussels"}' or '{"country":"eq:Belgium","name":"contains:acme"}'
            - Supported operators: eq, neq, contains, ncontains, startswith, range:start,end,
              gt, gte, lt, lte, empty, nempty.

            STRICT TOOL SELECTION RULES:
            - ONLY call tools directly required by the user's request.
            - Call list_* tools EXACTLY ONCE per request. Do NOT paginate automatically —
              only fetch the next page when the user explicitly asks for it.
            - The response includes resultSizeEstimate — use it to report the total count.
            - If a tool returns sufficient data, stop and answer immediately.
            - To find orders by customer/supplier name: first call list_locations to resolve
              the name to a uid, then use that uid in list_orders.

            OUTPUT
            - Return the exact JSON object or array that the tool returned. No prose, no explanation.
            - Do NOT omit, summarize, or filter any fields.
            - If multiple tools were called, return a JSON array where each element is
              {"tool": "<tool_name>", "result": <tool_result>}.
            - If only one tool was called, return its result directly.
        """,
        tools=[smartsales_mcp],
    )
````

## File: auth/token_credential.py
````python
import time

from azure.core.credentials import AccessToken

from graph.repository import GraphRepository



class StaticTokenCredential:
    def __init__(self, token: str):
        self.token = token

    def get_token(self, *_scopes, **_kwargs) -> AccessToken:
        return AccessToken(self.token, int(time.time()) + 3600)


def _make_graph_client(token: str, _azure_settings) -> GraphRepository:
    return GraphRepository(_azure_settings, credential=StaticTokenCredential(token))
````

## File: eval/score.py
````python
"""eval/score.py — Standalone LLM evaluator for benchmark_results.xlsx.

Reads agent responses that were collected by eval/script.py and fills in
llm_score (1-5) and llm_rationale for any row that has not been scored yet.

Usage (from project root):
    python eval/score.py                     # score only unscored rows
    python eval/score.py --force             # re-score every row
    python eval/score.py --run-id abc12345   # only score a specific run
    python eval/score.py --sheet SmartSales  # only score one agent sheet
"""

import argparse
import asyncio
import json
import os

import openpyxl
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────

EXCEL_FILE = "benchmark_results.xlsx"

AGENT_SHEETS = ["Graph", "Salesforce", "SmartSales", "Orchestrator"]

# Column positions are read dynamically from the header row — no hardcoding needed.

# ── Evaluator prompt ──────────────────────────────────────────────────────────

_SYSTEM = (
    "You are a benchmark evaluator for an AI agent system. "
    "Your job is to score how well an agent's actual response matches an expected answer."
)

_USER_TMPL = """\
Question asked to the agent:
{question}

Expected answer (description of what a correct response should contain):
{expected_answer}

Actual agent response:
{actual_response}

Rate the actual response on a scale of 1 to 5:
  1 – Completely wrong, irrelevant, or no meaningful response
  2 – Partially correct but with major gaps or errors
  3 – Mostly correct with some notable gaps or inaccuracies
  4 – Correct with only minor gaps or formatting differences
  5 – Fully correct and complete

Respond ONLY with valid JSON in this exact format:
{{"score": <integer 1-5>, "rationale": "<one or two sentence justification of the score>", "comments": "<optional broader observations: what was done well, what was missing, or how the response could be improved>"}}
"""


async def evaluate(
    client: AsyncAzureOpenAI,
    deployment: str,
    question: str,
    expected_answer: str,
    actual_response: str,
    success: bool,
) -> tuple[int | None, str, str]:
    """Return (score 1-5, rationale, comments)."""
    if not success or not (actual_response or "").strip():
        return 1, "Agent call failed or returned an empty response.", ""

    try:
        resp = await client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user",   "content": _USER_TMPL.format(
                    question=question,
                    expected_answer=expected_answer,
                    actual_response=actual_response[:4000],
                )},
            ],
            temperature=0,
            max_tokens=300,
        )
        raw  = resp.choices[0].message.content or ""
        data = json.loads(raw)
        return int(data["score"]), str(data.get("rationale", "")), str(data.get("comments", ""))
    except Exception as exc:
        return None, f"Evaluator error: {exc}", ""


# ── Sheet processing ──────────────────────────────────────────────────────────

def _build_col_map(ws) -> dict[str, int]:
    """Read column positions from the header row (row 1). Returns {name: 0-based index}."""
    return {
        cell.value: cell.column - 1
        for cell in ws[1]
        if cell.value is not None
    }


def _cell(row, col_name: str, col_map: dict) -> object:
    """Read a cell value by column name using the dynamic column map."""
    idx = col_map.get(col_name)
    return row[idx].value if idx is not None and idx < len(row) else None


def _is_scored(row, col_map: dict) -> bool:
    score = _cell(row, "llm_score", col_map)
    return score is not None and str(score).strip() != ""


async def score_sheet(
    ws,
    client: AsyncAzureOpenAI,
    deployment: str,
    force: bool,
    run_id_filter: str | None,
) -> tuple[int, int]:
    """Score all eligible rows in a worksheet. Returns (scored, skipped)."""
    col_map = _build_col_map(ws)
    scored  = 0
    skipped = 0

    # Collect rows to score (skip header row 1)
    rows_to_score = []
    for row in ws.iter_rows(min_row=2):
        run_id = _cell(row, "run_id", col_map)

        if run_id_filter and str(run_id) != run_id_filter:
            skipped += 1
            continue

        if not force and _is_scored(row, col_map):
            skipped += 1
            continue

        rows_to_score.append(row)

    total = len(rows_to_score)
    for i, row in enumerate(rows_to_score, 1):
        question        = str(_cell(row, "prompt",          col_map) or "")
        expected_answer = str(_cell(row, "expected_answer", col_map) or "")
        actual_response = str(_cell(row, "actual_response", col_map) or "")
        success_val     = _cell(row, "success", col_map)
        success         = bool(success_val) if success_val is not None else False
        run_id          = _cell(row, "run_id",    col_map)
        difficulty      = _cell(row, "difficulty", col_map)

        print(f"  [{i:02d}/{total:02d}] run={run_id}  [{difficulty}]  {question[:60]!r}")

        score, rationale, comments = await evaluate(
            client, deployment,
            question, expected_answer, actual_response, success,
        )

        # Write scores back — look up column numbers from the header map.
        # If llm_comments column doesn't exist yet (old file), append it to the header first.
        excel_row = row[0].row
        for col_name, value in [
            ("llm_score",     score),
            ("llm_rationale", rationale),
            ("llm_comments",  comments),
        ]:
            if col_name not in col_map:
                # Column missing from this sheet (old file) — add it after the last column
                new_col = ws.max_column + 1
                ws.cell(row=1, column=new_col).value = col_name
                col_map[col_name] = new_col - 1  # update map (0-based)
            ws.cell(row=excel_row, column=col_map[col_name] + 1).value = value

        label = f"{score}/5" if score is not None else "ERR"
        print(f"           → {label}  {rationale[:80]}")
        scored += 1

    return scored, skipped


# ── Entry point ───────────────────────────────────────────────────────────────

async def main(args: argparse.Namespace) -> None:
    if not os.path.exists(EXCEL_FILE):
        print(f"ERROR: {EXCEL_FILE} not found. Run eval/script.py first.")
        return

    deployment = os.environ["deployment"]
    endpoint   = os.environ["AZURE_OPENAI_ENDPOINT"]
    api_key    = os.environ["AZURE_OPENAI_API_KEY"]

    client = AsyncAzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version="2024-12-01-preview",
    )

    wb     = openpyxl.load_workbook(EXCEL_FILE)
    sheets = [args.sheet] if args.sheet else AGENT_SHEETS

    total_scored  = 0
    total_skipped = 0

    for sheet_name in sheets:
        if sheet_name not in wb.sheetnames:
            print(f"Sheet '{sheet_name}' not found — skipping.")
            continue

        ws = wb[sheet_name]
        col_map = _build_col_map(ws)
        unscored = sum(
            1 for row in ws.iter_rows(min_row=2)
            if not _is_scored(row, col_map)
            and (not args.run_id or str(_cell(row, "run_id", col_map)) == args.run_id)
        )

        if not args.force and unscored == 0:
            print(f"\n[{sheet_name}] — all rows already scored, skipping. (use --force to re-score)")
            continue

        mode = "re-scoring all" if args.force else f"{unscored} unscored"
        print(f"\n{'─' * 60}")
        print(f"  Sheet: {sheet_name}  ({mode} rows)")
        print(f"{'─' * 60}")

        scored, skipped = await score_sheet(
            ws, client, deployment,
            force=args.force,
            run_id_filter=args.run_id,
        )
        total_scored  += scored
        total_skipped += skipped

    # Save
    try:
        wb.save(EXCEL_FILE)
    except PermissionError:
        from datetime import datetime
        fallback = EXCEL_FILE.replace(".xlsx", f"_scored_{datetime.now():%Y%m%d_%H%M%S}.xlsx")
        wb.save(fallback)
        print(f"\nWARNING: {EXCEL_FILE} is locked. Saved to {fallback}")
        return

    print(f"\nDone — scored {total_scored} rows, skipped {total_skipped}.")
    print(f"Results saved → {EXCEL_FILE}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Score benchmark_results.xlsx with LLM evaluator.")
    parser.add_argument(
        "--force", action="store_true",
        help="Re-score rows that already have a score.",
    )
    parser.add_argument(
        "--run-id", metavar="ID",
        help="Only score rows matching this run_id (e.g. abc12345).",
    )
    parser.add_argument(
        "--sheet", choices=["Graph", "Salesforce", "SmartSales", "Orchestrator"],
        help="Only score rows in this agent sheet.",
    )
    args = parser.parse_args()
    asyncio.run(main(args))
````

## File: eval/script.py
````python
"""eval/script.py — Comprehensive benchmark for all 4 agents.

Covers all 35 tools (Graph: 11, Salesforce: 5, SmartSales: 19) across 4 agent
modes. After collecting responses an LLM evaluator scores each one (1–5) by
comparing it to a human-written expected answer.

Output: benchmark_results.xlsx with one sheet per agent + a Summary sheet.
Each run appends new rows (identified by run_id) so results accumulate.

Usage (from project root):
    python eval/script.py
"""

import asyncio
import configparser
import json
import os
import socket
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse

import httpx
import msal
import openpyxl
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI
from openpyxl.styles import Font, PatternFill

from agent_framework import MCPStreamableHTTPTool
from agents.graph_agent import create_graph_agent
from agents.orchestrator_agent import create_orchestrator_agent
from agents.salesforce_agent import create_salesforce_agent
from agents.smartsales_agent import create_smartsales_agent

load_dotenv()


# ── Prompt dataclass ──────────────────────────────────────────────────────────

@dataclass
class Prompt:
    text: str
    category: str       # e.g. "email", "locations", "cross-system"
    difficulty: str     # "simple" | "medium" | "hard"
    expected_answer: str = ""   # human-written description of a correct response
    tags: list[str] = field(default_factory=list)


# ── Graph prompts — 11 tools ──────────────────────────────────────────────────

GRAPH_PROMPTS: list[Prompt] = [
    # # whoami
    # Prompt(
    #     text="Who am I in Microsoft 365?",
    #     category="identity",
    #     difficulty="simple",
    #     expected_answer=(
    #         "The response contains the authenticated user's display name and "
    #         "email address from Microsoft 365."
    #     ),
    #     tags=["whoami"],
    # ),
    # # list_email
    # Prompt(
    #     text="Show me my 5 most recent emails.",
    #     category="email",
    #     difficulty="simple",
    #     expected_answer=(
    #         "A list of the 5 most recent inbox emails, each with at minimum the "
    #         "subject line, sender name or email address, and received date/time."
    #     ),
    #     tags=["list_email"],
    # ),
    # # search_email — by subject keyword
    # Prompt(
    #     text="Search for emails that have the word 'meeting' in the subject.",
    #     category="email",
    #     difficulty="medium",
    #     expected_answer=(
    #         "A list of emails whose subject contains 'meeting', showing subject, "
    #         "sender, and date. If no results are found, the response clearly states so."
    #     ),
    #     tags=["search_email"],
    # ),
    # # search_email — by date range
    # Prompt(
    #     text="Have I received any emails in the last 7 days? List sender and subject.",
    #     category="email",
    #     difficulty="medium",
    #     expected_answer=(
    #         "A list of emails received in the past 7 days, each showing the sender "
    #         "and subject. If none, the response clearly states the inbox was empty for that period."
    #     ),
    #     tags=["search_email"],
    # ),
    # # read_email — chained: list_email → read_email
    # Prompt(
    #     text="What does my most recent email say? Give me the full body.",
    #     category="email",
    #     difficulty="hard",
    #     expected_answer=(
    #         "The full body text of the most recent email, preceded by its subject "
    #         "and sender. The body is not truncated or summarised."
    #     ),
    #     tags=["list_email", "read_email"],
    # ),
    # # findpeople
    # Prompt(
    #     text="Find the email address of Dorian.",
    #     category="people",
    #     difficulty="simple",
    #     expected_answer=(
    #         "The email address(es) associated with a person named Dorian found in "
    #         "the Microsoft 365 directory, along with their display name."
    #     ),
    #     tags=["findpeople"],
    # ),
    # # list_calendar
    # Prompt(
    #     text="What are my upcoming calendar events this week?",
    #     category="calendar",
    #     difficulty="simple",
    #     expected_answer=(
    #         "A list of calendar events for the current week, each with event title, "
    #         "start date and time, and optionally end time or location."
    #     ),
    #     tags=["list_calendar"],
    # ),
    # # search_calendar
    # Prompt(
    #     text="Search my calendar for any events or meetings in the next 14 days.",
    #     category="calendar",
    #     difficulty="medium",
    #     expected_answer=(
    #         "A list of calendar events occurring in the next 14 days, each showing "
    #         "the event title and start date/time."
    #     ),
    #     tags=["search_calendar"],
    # ),
    # # list_contacts
    # Prompt(
    #     text="Show me my Microsoft 365 contacts.",
    #     category="contacts",
    #     difficulty="simple",
    #     expected_answer=(
    #         "A list of the user's Microsoft 365 contacts, each with display name "
    #         "and email address."
    #     ),
    #     tags=["list_contacts"],
    # ),
    # # search_files
    # Prompt(
    #     text="Find any Excel or PDF files in my OneDrive.",
    #     category="files",
    #     difficulty="medium",
    #     expected_answer=(
    #         "A list of Excel (.xlsx/.xls) or PDF files found in OneDrive, each "
    #         "with the file name and its ID."
    #     ),
    #     tags=["search_files"],
    # ),
    # # search_files → read_file (chained)
    # Prompt(
    #     text="Search OneDrive for a file called 'report' and read its content.",
    #     category="files",
    #     difficulty="hard",
    #     expected_answer=(
    #         "The text content of a file whose name contains 'report', preceded by "
    #         "the file name. If no such file is found, the response clearly states so."
    #     ),
    #     tags=["search_files", "read_file"],
    # ),
]


# ── Salesforce prompts — 5 tools ──────────────────────────────────────────────

SALESFORCE_PROMPTS: list[Prompt] = [
    # find_accounts — basic
    # Prompt(
    #     text="List 5 Salesforce accounts.",
    #     category="accounts",
    #     difficulty="simple",
    #     expected_answer=(
    #         "A list of exactly 5 Salesforce account records, each with at minimum "
    #         "the Id and Name fields."
    #     ),
    #     tags=["find_accounts"],
    # ),
    # # find_accounts — extra_fields + filter
    # Prompt(
    #     text="Find Salesforce accounts in Belgium, including their billing address.",
    #     category="accounts",
    #     difficulty="medium",
    #     expected_answer=(
    #         "A list of Salesforce accounts where BillingCountry is Belgium, each "
    #         "showing Name and billing address fields (BillingStreet, BillingCity, BillingCountry)."
    #     ),
    #     tags=["find_accounts"],
    # ),
    # # find_contacts — basic
    # Prompt(
    #     text="Show me 5 Salesforce contacts with their email addresses.",
    #     category="contacts",
    #     difficulty="simple",
    #     expected_answer=(
    #         "A list of 5 Salesforce contact records, each with Name and Email fields."
    #     ),
    #     tags=["find_contacts"],
    # ),
    # # find_contacts — filter
    # Prompt(
    #     text="Find Salesforce contacts in the Sales department.",
    #     category="contacts",
    #     difficulty="medium",
    #     expected_answer=(
    #         "A list of Salesforce contacts where Department equals 'Sales', each "
    #         "showing Name and Department. If none found, the response states so clearly."
    #     ),
    #     tags=["find_contacts"],
    # ),
    # # find_leads — basic
    # Prompt(
    #     text="Show me 5 leads in Salesforce.",
    #     category="leads",
    #     difficulty="simple",
    #     expected_answer=(
    #         "A list of 5 Salesforce lead records, each with at minimum Name and Company fields."
    #     ),
    #     tags=["find_leads"],
    # ),
    # # find_leads — industry filter
    # Prompt(
    #     text="Find Salesforce leads from the Technology or Software industry.",
    #     category="leads",
    #     difficulty="medium",
    #     expected_answer=(
    #         "A list of Salesforce leads where Industry is Technology or Software, "
    #         "each showing Name and Industry."
    #     ),
    #     tags=["find_leads"],
    # ),
    # # get_opportunities — basic
    # Prompt(
    #     text="List 5 open opportunities in Salesforce.",
    #     category="opportunities",
    #     difficulty="simple",
    #     expected_answer=(
    #         "A list of 5 open Salesforce opportunities, each with Name and StageName fields."
    #     ),
    #     tags=["get_opportunities"],
    # ),
    # # get_opportunities — amount filter + extra field
    # Prompt(
    #     text="Show me Salesforce opportunities with an amount greater than 10,000. Include probability.",
    #     category="opportunities",
    #     difficulty="medium",
    #     expected_answer=(
    #         "A list of Salesforce opportunities where Amount > 10000, each showing "
    #         "Name, Amount, and Probability."
    #     ),
    #     tags=["get_opportunities"],
    # ),
    # # get_cases — open
    # Prompt(
    #     text="List open support cases in Salesforce.",
    #     category="cases",
    #     difficulty="simple",
    #     expected_answer=(
    #         "A list of open Salesforce cases (Status != Closed), each with "
    #         "CaseNumber and Status fields."
    #     ),
    #     tags=["get_cases"],
    # ),
    # # get_cases — closed + extra fields
    # Prompt(
    #     text="Show me 5 closed Salesforce cases including their close date and description.",
    #     category="cases",
    #     difficulty="medium",
    #     expected_answer=(
    #         "A list of 5 closed Salesforce cases, each with CaseNumber, Status "
    #         "(Closed), ClosedDate, and Description fields."
    #     ),
    #     tags=["get_cases"],
    # ),
]


# ── SmartSales prompts — all 19 tools ────────────────────────────────────────

SMARTSALES_PROMPTS: list[Prompt] = [
    # # ── LOCATIONS ─────────────────────────────────────────────────────────────
    # # list_locations — basic
    # Prompt(
    #     text="List all SmartSales locations.",
    #     category="locations",
    #     difficulty="simple",
    #     expected_answer=(
    #         "A JSON array of SmartSales location objects. Each object contains at "
    #         "minimum the uid and name fields. The response also reports the total count."
    #     ),
    #     tags=["list_locations"],
    # ),
    # # list_locations — city filter
    # Prompt(
    #     text="Find SmartSales locations in Brussels.",
    #     category="locations",
    #     difficulty="medium",
    #     expected_answer=(
    #         "A JSON array of SmartSales locations where city equals Brussels. Each "
    #         "object has at minimum uid and name. If none found, states so clearly."
    #     ),
    #     tags=["list_locations"],
    # ),
    # # list_locations — sort + projection
    # Prompt(
    #     text="List SmartSales locations in Belgium sorted by name, using full projection.",
    #     category="locations",
    #     difficulty="medium",
    #     expected_answer=(
    #         "A JSON array of SmartSales locations in Belgium (country eq Belgium), "
    #         "sorted alphabetically by name, with full projection fields for each entry."
    #     ),
    #     tags=["list_locations"],
    # ),
    # # list_locations → get_location (chained)
    # Prompt(
    #     text="List all SmartSales locations, then retrieve the full details of the first result.",
    #     category="locations",
    #     difficulty="hard",
    #     expected_answer=(
    #         "First the list of locations, then the complete detail object of the "
    #         "first location retrieved by its uid, containing all available fields."
    #     ),
    #     tags=["list_locations", "get_location"],
    # ),
    # # list_displayable_fields
    # Prompt(
    #     text="What fields are available to display in the SmartSales location list?",
    #     category="locations",
    #     difficulty="simple",
    #     expected_answer=(
    #         "A list or array of field descriptors indicating which fields can be "
    #         "shown in the SmartSales location list view (e.g. name, city, country, uid)."
    #     ),
    #     tags=["list_displayable_fields"],
    # ),
    # # list_queryable_fields
    # Prompt(
    #     text="What fields can I use to filter SmartSales locations?",
    #     category="locations",
    #     difficulty="simple",
    #     expected_answer=(
    #         "A list or array of field descriptors showing which fields support "
    #         "query/filter operators for SmartSales locations (e.g. city, country, name)."
    #     ),
    #     tags=["list_queryable_fields"],
    # ),
    # # list_sortable_fields
    # Prompt(
    #     text="What fields can I use to sort SmartSales locations?",
    #     category="locations",
    #     difficulty="simple",
    #     expected_answer=(
    #         "A list or array of field descriptors showing which fields can be used "
    #         "as sort keys for SmartSales locations."
    #     ),
    #     tags=["list_sortable_fields"],
    # ),
    # # ── CATALOG ───────────────────────────────────────────────────────────────
    # # list_catalog_items — basic
    # Prompt(
    #     text="List SmartSales catalog items.",
    #     category="catalog",
    #     difficulty="simple",
    #     expected_answer=(
    #         "A JSON array of SmartSales catalog item objects. Each object contains "
    #         "at minimum the uid field."
    #     ),
    #     tags=["list_catalog_items"],
    # ),
    # # list_catalog_items — sorted + projection
    # Prompt(
    #     text="List SmartSales catalog items with simple projection, sorted by name.",
    #     category="catalog",
    #     difficulty="medium",
    #     expected_answer=(
    #         "A JSON array of catalog items with simple projection fields, returned "
    #         "in alphabetical order by name."
    #     ),
    #     tags=["list_catalog_items"],
    # ),
    # # list_catalog_items → get_catalog_item (chained)
    # Prompt(
    #     text="List SmartSales catalog items, then retrieve the full details of the first one.",
    #     category="catalog",
    #     difficulty="hard",
    #     expected_answer=(
    #         "First the list of catalog items, then the full detail object of the "
    #         "first item retrieved by its uid, containing all available fields."
    #     ),
    #     tags=["list_catalog_items", "get_catalog_item"],
    # ),
    # # list_catalog_displayable_fields
    # Prompt(
    #     text="What fields can be displayed for SmartSales catalog items?",
    #     category="catalog",
    #     difficulty="simple",
    #     expected_answer=(
    #         "A list or array of field descriptors indicating which fields can be "
    #         "shown in the SmartSales catalog item list view."
    #     ),
    #     tags=["list_catalog_displayable_fields"],
    # ),
    # # list_catalog_queryable_fields
    # Prompt(
    #     text="What fields can I filter SmartSales catalog items by?",
    #     category="catalog",
    #     difficulty="simple",
    #     expected_answer=(
    #         "A list or array of field descriptors showing which fields support "
    #         "query/filter operators for SmartSales catalog items."
    #     ),
    #     tags=["list_catalog_queryable_fields"],
    # ),
    # # list_catalog_sortable_fields
    # Prompt(
    #     text="What fields can I sort SmartSales catalog items by?",
    #     category="catalog",
    #     difficulty="simple",
    #     expected_answer=(
    #         "A list or array of field descriptors showing which fields can be used "
    #         "as sort keys for SmartSales catalog items."
    #     ),
    #     tags=["list_catalog_sortable_fields"],
    # ),
    # # ── ORDERS ────────────────────────────────────────────────────────────────
    # # list_orders — basic
    # Prompt(
    #     text="List recent SmartSales orders.",
    #     category="orders",
    #     difficulty="simple",
    #     expected_answer=(
    #         "A JSON array of SmartSales order objects. Each object contains at "
    #         "minimum the uid field."
    #     ),
    #     tags=["list_orders"],
    # ),
    # # list_orders — full projection
    # Prompt(
    #     text="List SmartSales orders with full projection.",
    #     category="orders",
    #     difficulty="medium",
    #     expected_answer=(
    #         "A JSON array of SmartSales orders with the full projection applied, "
    #         "meaning each order object contains all available fields."
    #     ),
    #     tags=["list_orders"],
    # ),
    # # list_orders → get_order (chained)
    # Prompt(
    #     text="List SmartSales orders, then retrieve the full details of the first order.",
    #     category="orders",
    #     difficulty="hard",
    #     expected_answer=(
    #         "First the list of orders, then the complete detail object of the first "
    #         "order retrieved by its uid, containing all available fields."
    #     ),
    #     tags=["list_orders", "get_order"],
    # ),
    # # get_order_configuration
    # Prompt(
    #     text="What is the SmartSales order configuration?",
    #     category="orders",
    #     difficulty="simple",
    #     expected_answer=(
    #         "A JSON object describing the global SmartSales order configuration, "
    #         "including form sections, configurable fields, and order settings."
    #     ),
    #     tags=["get_order_configuration"],
    # ),
    # # list_approbation_statuses
    # Prompt(
    #     text="List all SmartSales order approbation statuses.",
    #     category="orders",
    #     difficulty="simple",
    #     expected_answer=(
    #         "A JSON array of SmartSales order approbation (approval) status objects, "
    #         "each with at minimum a uid field."
    #     ),
    #     tags=["list_approbation_statuses"],
    # ),
    # # list_approbation_statuses → get_approbation_status (chained)
    # Prompt(
    #     text="List SmartSales approbation statuses, then get the full details of the first one.",
    #     category="orders",
    #     difficulty="hard",
    #     expected_answer=(
    #         "First the list of approbation statuses, then the full detail object of "
    #         "the first status retrieved by its uid."
    #     ),
    #     tags=["list_approbation_statuses", "get_approbation_status"],
    # ),
    # # list_order_displayable_fields
    # Prompt(
    #     text="What fields can be displayed for SmartSales orders?",
    #     category="orders",
    #     difficulty="simple",
    #     expected_answer=(
    #         "A list or array of field descriptors indicating which fields can be "
    #         "shown in the SmartSales order list view."
    #     ),
    #     tags=["list_order_displayable_fields"],
    # ),
    # # list_order_queryable_fields
    # Prompt(
    #     text="What fields can I filter SmartSales orders by?",
    #     category="orders",
    #     difficulty="simple",
    #     expected_answer=(
    #         "A list or array of field descriptors showing which fields support "
    #         "query/filter operators for SmartSales orders."
    #     ),
    #     tags=["list_order_queryable_fields"],
    # ),
    # # list_order_sortable_fields
    # Prompt(
    #     text="What fields can I sort SmartSales orders by?",
    #     category="orders",
    #     difficulty="simple",
    #     expected_answer=(
    #         "A list or array of field descriptors showing which fields can be used "
    #         "as sort keys for SmartSales orders."
    #     ),
    #     tags=["list_order_sortable_fields"],
    # ),
]


# ── Orchestrator prompts — routing + cross-system ─────────────────────────────

_ORCHESTRATOR_ROUTING: list[Prompt] = [
    Prompt(
        text="Who am I in Microsoft 365?",
        category="routing/graph",
        difficulty="simple",
        expected_answer=(
            "The authenticated user's display name and email address from Microsoft "
            "365, routed correctly via the Graph agent."
        ),
        tags=["orchestrator", "routing"],
    ),
    Prompt(
        text="List 5 Salesforce accounts.",
        category="routing/salesforce",
        difficulty="simple",
        expected_answer=(
            "A list of 5 Salesforce account records with Id and Name, routed "
            "correctly via the Salesforce agent."
        ),
        tags=["orchestrator", "routing"],
    ),
    Prompt(
        text="List SmartSales locations.",
        category="routing/smartsales",
        difficulty="simple",
        expected_answer=(
            "A JSON array of SmartSales location objects with uid and name fields, "
            "routed correctly via the SmartSales agent."
        ),
        tags=["orchestrator", "routing"],
    ),
]

_ORCHESTRATOR_CROSS: list[Prompt] = [
    Prompt(
        text="Find contacts named 'John' in both Microsoft 365 and Salesforce.",
        category="cross-system",
        difficulty="hard",
        expected_answer=(
            "Results from both systems, clearly labelled. From Microsoft 365: any "
            "contacts named John with their email. From Salesforce: any contacts "
            "named John with their email and account."
        ),
        tags=["orchestrator", "multi-agent", "graph", "salesforce"],
    ),
    Prompt(
        text="Show me my calendar events for the next 7 days and check whether any organizers appear as contacts in Salesforce.",
        category="cross-system",
        difficulty="hard",
        expected_answer=(
            "A list of calendar events for the next 7 days (title, date, organizer "
            "email), followed by a note for each organizer whether they were found "
            "in Salesforce contacts."
        ),
        tags=["orchestrator", "multi-agent", "graph", "salesforce"],
    ),
    Prompt(
        text="List SmartSales locations in Brussels and check if there are any matching Salesforce accounts in the same city.",
        category="cross-system",
        difficulty="hard",
        expected_answer=(
            "SmartSales locations in Brussels (uid, name) labelled 'From SmartSales', "
            "followed by Salesforce accounts with BillingCity Brussels labelled "
            "'From Salesforce'."
        ),
        tags=["orchestrator", "multi-agent", "smartsales", "salesforce"],
    ),
    Prompt(
        text="What are my 3 most recent emails? Are any of those senders listed as contacts in Salesforce?",
        category="cross-system",
        difficulty="hard",
        expected_answer=(
            "The 3 most recent emails (subject, sender), then a check for each "
            "sender in Salesforce contacts, clearly stating whether each was found."
        ),
        tags=["orchestrator", "multi-agent", "graph", "salesforce"],
    ),
    Prompt(
        text="Show me open Salesforce opportunities and SmartSales locations in Belgium. Give me a summary of both.",
        category="cross-system",
        difficulty="hard",
        expected_answer=(
            "Two clearly labelled sections: open Salesforce opportunities (Name, "
            "StageName, Amount) and SmartSales locations in Belgium (uid, name), "
            "followed by a short summary of each."
        ),
        tags=["orchestrator", "multi-agent", "salesforce", "smartsales"],
    ),
]

ORCHESTRATOR_PROMPTS = _ORCHESTRATOR_ROUTING + _ORCHESTRATOR_CROSS


# ── Excel schema ──────────────────────────────────────────────────────────────

EXCEL_FILE = "benchmark_results.xlsx"

# One sheet per agent + summary
AGENT_SHEETS = {
    "GraphAgent":        "Graph",
    "SalesforceAgent":   "Salesforce",
    "SmartSalesAgent":   "SmartSales",
    "OrchestratorAgent": "Orchestrator",
}
SUMMARY_SHEET = "Summary"

RESULT_COLUMNS = [
    "run_id", "timestamp", "prompt",
    "category", "difficulty", "tags",
    "expected_answer",
    "actual_response",
    "response_time_s",
    "input_tokens", "output_tokens", "total_tokens",
    "response_length",
    "llm_score",        # 1–5
    "llm_rationale",
    "llm_comments",
    "success",
    "error",
]

SUMMARY_COLUMNS = [
    "run_id", "timestamp", "agent",
    "prompts_run", "success_rate_%",
    "avg_response_time_s",
    "avg_input_tokens", "avg_output_tokens", "avg_total_tokens",
    "avg_llm_score",
]


# ── Excel helpers ─────────────────────────────────────────────────────────────

def _load_or_create_workbook():
    if os.path.exists(EXCEL_FILE):
        wb = openpyxl.load_workbook(EXCEL_FILE)
    else:
        wb = openpyxl.Workbook()
        wb.remove(wb.active)  # remove default blank sheet

    agent_sheets = {}
    for agent_key, sheet_name in AGENT_SHEETS.items():
        if sheet_name not in wb.sheetnames:
            ws = wb.create_sheet(sheet_name)
            ws.append(RESULT_COLUMNS)
            _style_header(ws)
        agent_sheets[agent_key] = wb[sheet_name]

    if SUMMARY_SHEET not in wb.sheetnames:
        ws_s = wb.create_sheet(SUMMARY_SHEET)
        ws_s.append(SUMMARY_COLUMNS)
        _style_header(ws_s)
    summary_sheet = wb[SUMMARY_SHEET]

    return wb, agent_sheets, summary_sheet


def _style_header(ws) -> None:
    fill = PatternFill("solid", fgColor="4472C4")
    font = Font(color="FFFFFF", bold=True)
    for cell in ws[1]:
        cell.fill = fill
        cell.font = font


def _auto_width(ws) -> None:
    for col in ws.columns:
        max_len = max((len(str(cell.value or "")) for cell in col), default=0)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 80)


# ── LLM evaluator ─────────────────────────────────────────────────────────────

_EVAL_SYSTEM = (
    "You are a benchmark evaluator for an AI agent system. "
    "Your job is to score how well an agent's actual response matches an expected answer."
)

_EVAL_USER_TMPL = """\
Question asked to the agent:
{question}

Expected answer (description of what a correct response should contain):
{expected_answer}

Actual agent response:
{actual_response}

Rate the actual response on a scale of 1 to 5:
  1 – Completely wrong, irrelevant, or no meaningful response
  2 – Partially correct but with major gaps or errors
  3 – Mostly correct with some notable gaps or inaccuracies
  4 – Correct with only minor gaps or formatting differences
  5 – Fully correct and complete

Respond ONLY with valid JSON in this exact format:
{{"score": <integer 1-5>, "rationale": "<one or two sentence justification of the score>", "comments": "<optional broader observations: what was done well, what was missing, or how the response could be improved>"}}
"""


async def evaluate_response(
    openai_client: AsyncAzureOpenAI,
    deployment: str,
    prompt: Prompt,
    actual_response: str,
    success: bool,
) -> tuple[int | None, str, str]:
    """Return (score 1-5, rationale, comments). Returns (None, reason, "") on failure."""
    if not success or not actual_response.strip():
        return 1, "Agent call failed or returned an empty response.", ""

    user_msg = _EVAL_USER_TMPL.format(
        question=prompt.text,
        expected_answer=prompt.expected_answer,
        actual_response=actual_response[:4000],
    )
    try:
        resp = await openai_client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": _EVAL_SYSTEM},
                {"role": "user",   "content": user_msg},
            ],
            temperature=0,
            max_tokens=300,
        )
        raw = resp.choices[0].message.content or ""
        data = json.loads(raw)
        score     = int(data["score"])
        rationale = str(data.get("rationale", ""))
        comments  = str(data.get("comments", ""))
        return score, rationale, comments
    except Exception as exc:
        return None, f"Evaluator error: {exc}", ""


# ── Auth / server helpers ─────────────────────────────────────────────────────

_TOKEN_CACHE_FILE = ".token_cache.bin"


def _build_msal_app(client_id: str, tenant_id: str):
    cache = msal.SerializableTokenCache()
    if os.path.exists(_TOKEN_CACHE_FILE):
        with open(_TOKEN_CACHE_FILE, "r") as f:
            cache.deserialize(f.read())
    return msal.PublicClientApplication(
        client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        token_cache=cache,
    ), cache


def _persist_cache(cache: msal.SerializableTokenCache) -> None:
    if cache.has_state_changed:
        with open(_TOKEN_CACHE_FILE, "w") as f:
            f.write(cache.serialize())


def authenticate_microsoft(client_id: str, tenant_id: str, scopes: list[str]) -> str:
    app, cache = _build_msal_app(client_id, tenant_id)
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(scopes, account=accounts[0])
        if result and "access_token" in result:
            _persist_cache(cache)
            return result["access_token"]
    flow = app.initiate_device_flow(scopes=scopes)
    print(f"\nAuthenticate at: {flow['verification_uri']}")
    print(f"Enter code:      {flow['user_code']}\n")
    result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        raise RuntimeError(f"Auth failed: {result.get('error_description', 'unknown')}")
    _persist_cache(cache)
    return result["access_token"]


def _wait_for_port(host: str, port: int, timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return
        except OSError:
            time.sleep(0.25)
    raise TimeoutError(f"Server at {host}:{port} not ready within {timeout}s")


def _is_local(url: str) -> bool:
    return (urlparse(url).hostname or "") in ("localhost", "127.0.0.1", "::1")


def _start_server(module: str, env: dict, url: str) -> subprocess.Popen:
    proc = subprocess.Popen(
        [sys.executable, "-m", module],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    parsed = urlparse(url)
    _wait_for_port(parsed.hostname or "localhost", parsed.port or 8000)
    return proc


def _resolve_sf_session(sf_mcp_url: str) -> str:
    parsed = urlparse(sf_mcp_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    try:
        resp = httpx.get(f"{base}/auth/salesforce/session", timeout=5)
        if resp.status_code == 200:
            return resp.json()["session_token"]
    except httpx.RequestError as exc:
        raise RuntimeError(f"Cannot reach Salesforce MCP server: {exc}") from exc
    raise RuntimeError(
        "No active Salesforce session. Run main.py first to authenticate via browser."
    )


def _resolve_ss_session(ss_mcp_url: str) -> str:
    parsed = urlparse(ss_mcp_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    try:
        resp = httpx.get(f"{base}/auth/smartsales/session", timeout=10)
        if resp.status_code == 200:
            return resp.json()["session_token"]
        raise RuntimeError(f"SmartSales session returned {resp.status_code}: {resp.text}")
    except httpx.RequestError as exc:
        raise RuntimeError(f"Cannot reach SmartSales MCP server: {exc}") from exc


# ── Core benchmark ────────────────────────────────────────────────────────────

async def run_prompt(agent, prompt: Prompt) -> dict:
    t0 = time.perf_counter()
    response_text = ""
    error = ""
    success = False
    input_tokens = output_tokens = total_tokens = None

    try:
        response = await agent.run(prompt.text)
        response_text = response.text or ""
        print("response_text", response_text)
        success = True

        usage = response.usage_details or {}
        input_tokens  = usage.get("input_token_count")
        output_tokens = usage.get("output_token_count")
        total_tokens  = usage.get("total_token_count")
        if total_tokens is None and input_tokens is not None and output_tokens is not None:
            total_tokens = input_tokens + output_tokens

    except Exception as exc:
        error = str(exc)
        print(f"    ERROR: {exc}")

    return {
        "response_text":  response_text,
        "response_time":  time.perf_counter() - t0,
        "input_tokens":   input_tokens,
        "output_tokens":  output_tokens,
        "total_tokens":   total_tokens,
        "response_length": len(response_text),
        "success":        success,
        "error":          error,
    }


async def benchmark(graph_agent, sf_agent, ss_agent, orchestrator) -> list[dict]:
    timestamp = datetime.now().isoformat(timespec="seconds")
    run_id    = str(uuid.uuid4())[:8]
    results   = []

    modes = [
        ("GraphAgent",        graph_agent,   GRAPH_PROMPTS),
        ("SalesforceAgent",   sf_agent,      SALESFORCE_PROMPTS),
        ("SmartSalesAgent",   ss_agent,      SMARTSALES_PROMPTS),
        ("OrchestratorAgent", orchestrator,  ORCHESTRATOR_PROMPTS),
    ]

    for mode_name, agent, prompts in modes:
        print(f"\n{'─' * 65}")
        print(f"  {mode_name}  ({len(prompts)} prompts)")
        print(f"{'─' * 65}")

        for i, prompt in enumerate(prompts, 1):
            print(f"  [{i:02d}/{len(prompts):02d}] [{prompt.difficulty}] {prompt.text!r}")
            metrics = await run_prompt(agent, prompt)
            status = "OK  " if metrics["success"] else "FAIL"
            print(
                f"           → {status} | {metrics['response_time']:.2f}s "
                f"| tokens in={metrics['input_tokens']} out={metrics['output_tokens']}"
            )
            results.append({
                "run_id":    run_id,
                "timestamp": timestamp,
                "agent_mode": mode_name,
                "prompt":    prompt,   # keep the Prompt object for evaluation step
                **metrics,
            })

    return results


async def evaluate_all(
    results: list[dict],
    openai_client: AsyncAzureOpenAI,
    deployment: str,
) -> None:
    """Add llm_score and llm_rationale to each result dict in-place."""
    total = len(results)
    print(f"\nEvaluating {total} responses with LLM…")
    for i, r in enumerate(results, 1):
        prompt: Prompt = r["prompt"]
        score, rationale, comments = await evaluate_response(
            openai_client, deployment,
            prompt, r["response_text"], r["success"],
        )
        r["llm_score"]     = score
        r["llm_rationale"] = rationale
        r["llm_comments"]  = comments
        status = f"{score}/5" if score is not None else "ERR"
        print(f"  [{i:02d}/{total:02d}] {status}  {prompt.text[:60]!r}")


def save_results(results: list[dict]) -> None:
    wb, agent_sheets, summary_sheet = _load_or_create_workbook()

    # Group by agent
    by_agent: dict[str, list[dict]] = {}
    for r in results:
        by_agent.setdefault(r["agent_mode"], []).append(r)

    for agent_mode, rows in by_agent.items():
        ws = agent_sheets[agent_mode]
        for r in rows:
            prompt: Prompt = r["prompt"]
            ws.append([
                r["run_id"],
                r["timestamp"],
                prompt.text,
                prompt.category,
                prompt.difficulty,
                ",".join(prompt.tags),
                prompt.expected_answer,
                r["response_text"],
                round(r["response_time"], 3) if r["response_time"] is not None else None,
                r["input_tokens"],
                r["output_tokens"],
                r["total_tokens"],
                r["response_length"],
                r.get("llm_score"),
                r.get("llm_rationale", ""),
                r.get("llm_comments", ""),
                r["success"],
                r["error"],
            ])
        _auto_width(ws)

    # Summary
    run_id    = results[0]["run_id"]    if results else ""
    timestamp = results[0]["timestamp"] if results else ""

    for agent_mode, rows in by_agent.items():
        n         = len(rows)
        successes = sum(1 for r in rows if r["success"])
        times  = [r["response_time"]  for r in rows if r["response_time"]  is not None]
        in_t   = [r["input_tokens"]   for r in rows if r["input_tokens"]   is not None]
        out_t  = [r["output_tokens"]  for r in rows if r["output_tokens"]  is not None]
        tot_t  = [r["total_tokens"]   for r in rows if r["total_tokens"]   is not None]
        scores = [r["llm_score"]      for r in rows if r.get("llm_score")  is not None]
        summary_sheet.append([
            run_id,
            timestamp,
            agent_mode,
            n,
            round(successes / n * 100, 1) if n else None,
            round(sum(times) / len(times), 3) if times else None,
            round(sum(in_t)  / len(in_t))     if in_t   else None,
            round(sum(out_t) / len(out_t))    if out_t  else None,
            round(sum(tot_t) / len(tot_t))    if tot_t  else None,
            round(sum(scores) / len(scores), 2) if scores else None,
        ])
    _auto_width(summary_sheet)

    target = EXCEL_FILE
    try:
        wb.save(target)
    except PermissionError:
        target = EXCEL_FILE.replace(".xlsx", f"_{datetime.now():%Y%m%d_%H%M%S}.xlsx")
        wb.save(target)
        print(f"\nWARNING: {EXCEL_FILE} is locked. Saved to {target}")
    print(f"\nResults saved → {target}  ({len(results)} rows)")


# ── Entry point ───────────────────────────────────────────────────────────────

async def main() -> None:
    config = configparser.ConfigParser()
    config.read(["config.cfg"])
    azure  = config["azure"]
    sf_cfg = config["salesforce"]
    ss_cfg = config["smartsales"] if config.has_section("smartsales") else {}

    deployment = os.environ["deployment"]
    endpoint   = os.environ["AZURE_OPENAI_ENDPOINT"]
    api_key    = os.environ["AZURE_OPENAI_API_KEY"]

    total = (
        len(GRAPH_PROMPTS) + len(SALESFORCE_PROMPTS)
        + len(SMARTSALES_PROMPTS) + len(ORCHESTRATOR_PROMPTS)
    )
    print(
        f"\nBenchmark plan: {len(GRAPH_PROMPTS)} graph + {len(SALESFORCE_PROMPTS)} salesforce"
        f" + {len(SMARTSALES_PROMPTS)} smartsales + {len(ORCHESTRATOR_PROMPTS)} orchestrator"
        f" = {total} prompts\n"
    )

    # ── Microsoft Graph ────────────────────────────────────────────────────────
    client_id     = azure["clientId"]
    tenant_id     = azure["tenantId"]
    scopes        = azure["graphUserScopes"].split()
    graph_mcp_url = azure.get("mcpServerUrl", "http://localhost:8000/mcp")

    print("Authenticating with Microsoft…")
    ms_token = authenticate_microsoft(client_id, tenant_id, scopes)
    print("OK")

    graph_env = os.environ.copy()
    parsed    = urlparse(graph_mcp_url)
    graph_env["MCP_RESOURCE_URI"] = f"{parsed.scheme}://{parsed.netloc}"

    graph_proc = None
    if _is_local(graph_mcp_url):
        print("Starting Graph MCP server…")
        graph_proc = _start_server("graph.mcp_server", graph_env, graph_mcp_url)
        print("OK")

    graph_http = httpx.AsyncClient(headers={"Authorization": f"Bearer {ms_token}"})
    graph_mcp  = MCPStreamableHTTPTool(name="graph", url=graph_mcp_url, http_client=graph_http)

    # ── Salesforce ─────────────────────────────────────────────────────────────
    sf_mcp_url = sf_cfg.get("mcpServerUrl", "http://localhost:8001/mcp")
    sf_env     = os.environ.copy()
    sf_parsed  = urlparse(sf_mcp_url)
    sf_env["MCP_RESOURCE_URI"] = f"{sf_parsed.scheme}://{sf_parsed.netloc}"

    sf_proc = None
    if _is_local(sf_mcp_url):
        print("Starting Salesforce MCP server…")
        sf_proc = _start_server("salesforce.mcp_server", sf_env, sf_mcp_url)
        print("OK")

    print("Resolving Salesforce session…")
    sf_token = _resolve_sf_session(sf_mcp_url)
    print("OK")

    sf_http = httpx.AsyncClient(headers={"Authorization": f"Bearer {sf_token}"})
    sf_mcp  = MCPStreamableHTTPTool(name="salesforce", url=sf_mcp_url, http_client=sf_http)

    # ── SmartSales ─────────────────────────────────────────────────────────────
    ss_mcp_url = ss_cfg.get("mcpServerUrl", "http://localhost:8002/mcp")
    ss_env     = os.environ.copy()
    ss_parsed  = urlparse(ss_mcp_url)
    ss_env["MCP_RESOURCE_URI"] = f"{ss_parsed.scheme}://{ss_parsed.netloc}"

    ss_proc = None
    if _is_local(ss_mcp_url):
        print("Starting SmartSales MCP server…")
        ss_proc = _start_server("smartsales.mcp_server", ss_env, ss_mcp_url)
        print("OK")

    print("Resolving SmartSales session…")
    ss_token = _resolve_ss_session(ss_mcp_url)
    print("OK")

    ss_http = httpx.AsyncClient(headers={"Authorization": f"Bearer {ss_token}"})
    ss_mcp  = MCPStreamableHTTPTool(name="smartsales", url=ss_mcp_url, http_client=ss_http)

    # ── Build agents ───────────────────────────────────────────────────────────
    graph_agent  = create_graph_agent(graph_mcp=graph_mcp)
    sf_agent     = create_salesforce_agent(salesforce_mcp=sf_mcp)
    ss_agent     = create_smartsales_agent(smartsales_mcp=ss_mcp)
    orchestrator = create_orchestrator_agent(
        graph_agent=graph_agent,
        salesforce_agent=sf_agent,
        smartsales_agent=ss_agent,
    )

    # ── LLM evaluator client ───────────────────────────────────────────────────
    eval_client = AsyncAzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version="2024-12-01-preview",
    )

    # ── Run ────────────────────────────────────────────────────────────────────
    try:
        print(f"Starting benchmark — {datetime.now():%Y-%m-%d %H:%M:%S}")
        results = await benchmark(graph_agent, sf_agent, ss_agent, orchestrator)
        await evaluate_all(results, eval_client, deployment)
        save_results(results)
    finally:
        await graph_http.aclose()
        await sf_http.aclose()
        await ss_http.aclose()
        for proc in (graph_proc, sf_proc, ss_proc):
            if proc is not None:
                proc.terminate()
                proc.wait()


def _exception_handler(loop, context):
    if context.get("message") == "an error occurred during closing of asynchronous generator":
        asyncgen = context.get("asyncgen")
        filename = getattr(getattr(asyncgen, "ag_code", None), "co_filename", "")
        if "streamable_http" in filename:
            return
    loop.default_exception_handler(context)


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.set_exception_handler(_exception_handler)
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
````

## File: graph/context.py
````python
import logging
import re
from typing import Any

from agent_framework._sessions import BaseContextProvider, AgentSession, SessionContext
from agent_framework._types import Message

log = logging.getLogger(__name__)

_FILE_TOOLS = {"search_files", "read_file", "read_multiple_files"}


def _parse_files_from_output(text: str) -> dict[str, str]:
    """Extract {id: name} pairs from search_files output text."""
    ids = re.findall(r"^ID:\s*(.+)$", text, re.MULTILINE)
    names = re.findall(r"^Name:\s*(.+)$", text, re.MULTILINE)
    return {fid.strip(): name.strip() for fid, name in zip(ids, names)}


class DocumentContextProvider(BaseContextProvider):
    def __init__(self) -> None:
        super().__init__(source_id="document_context")

    async def before_run(
        self,
        *,
        agent: Any,
        session: AgentSession,
        context: SessionContext,
        state: dict[str, Any],
    ) -> None:
        doc_ctx = session.state.get("doc_context")
        if not doc_ctx:
            log.debug("[doc_ctx] before_run: no session context yet, skipping injection")
            return

        lines = ["[Session Context]"]
        if topic := doc_ctx.get("topic"):
            lines.append(f"Current topic: {topic}")
        if last_query := doc_ctx.get("last_query"):
            lines.append(f'Last search: "{last_query}"')
        if files := doc_ctx.get("files"):
            file_list = ", ".join(f"{name} ({fid})" for fid, name in files.items())
            lines.append(f"Files found: {file_list}")

        if len(lines) > 1:
            text = "\n".join(lines)
            log.info("[doc_ctx] before_run: injecting context:\n%s", text)
            context.extend_messages(self, [Message("system", [text])])

    async def after_run(
        self,
        *,
        agent: Any,
        session: AgentSession,
        context: SessionContext,
        state: dict[str, Any],
    ) -> None:
        if not context.response or not context.response.messages:
            log.debug("[doc_ctx] after_run: no response messages, skipping")
            return

        # First pass: collect function_call entries for our file tools.
        call_map: dict[str, dict[str, Any]] = {}  # call_id -> {name, args}
        for message in context.response.messages:
            for content in message.contents or []:
                if content.type == "function_call" and content.name in _FILE_TOOLS:
                    args = content.parse_arguments() or {}
                    log.info("[doc_ctx] after_run: saw tool call — %s(%s)", content.name, args)
                    call_map[content.call_id] = {"name": content.name, "args": args}

        if not call_map:
            log.debug("[doc_ctx] after_run: no file tool calls in this turn, skipping state update")
            return

        doc_ctx: dict[str, Any] = session.state.setdefault("doc_context", {})

        # Second pass: match function_result messages and extract state.
        for message in context.response.messages:
            for content in message.contents or []:
                if content.type != "function_result":
                    continue
                call = call_map.get(content.call_id)
                if not call:
                    continue

                tool_name: str = call["name"]
                result_text = str(content.result or "")

                if tool_name == "search_files":
                    query: str = call["args"].get("query", "")
                    doc_ctx["topic"] = query
                    doc_ctx["last_query"] = query
                    new_files = _parse_files_from_output(result_text)
                    doc_ctx.setdefault("files", {}).update(new_files)
                    log.info(
                        "[doc_ctx] after_run: search_files(query=%r) → found %d file(s): %s",
                        query,
                        len(new_files),
                        list(new_files.values()),
                    )

        log.debug("[doc_ctx] after_run: session state now: %s", doc_ctx)
````

## File: graph/interface.py
````python
from abc import ABC, abstractmethod

class IGraphRepository(ABC):

    @abstractmethod
    async def get_user(self): ...

    @abstractmethod
    async def get_inbox(self): ...

    @abstractmethod
    async def get_drive_items(self): ...

    @abstractmethod
    async def get_contacts(self): ...

    @abstractmethod
    async def get_upcoming_events(self): ...

    @abstractmethod
    async def get_message_body(self, message_id: str): ...
````

## File: graph/mcp_router.py
````python
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
    return await repo.find_people(name)


async def _list_email(repo: GraphRepository, **kwargs):
    return await repo.get_inbox()


async def _read_email(repo: GraphRepository, message_id: str, **kwargs):
    return await repo.get_message_body(message_id)


async def _search_files(repo: GraphRepository, query: str, drive_id=None, folder_id="root", **kwargs):
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
````

## File: graph/mcp_server.py
````python
import configparser
import os

from mcp.server.fastmcp import FastMCP, Context
from starlette.requests import Request
from starlette.responses import JSONResponse

from graph.mcp_router import register_graph_tools


mcp = FastMCP("graph", port=8000)

_config = configparser.ConfigParser()
_config.read(["config.cfg"])
_azure_settings = _config["azure"]

_TENANT_ID = _azure_settings["tenantId"]
_GRAPH_SCOPES = _azure_settings["graphUserScopes"].split(" ")
_RESOURCE_URI = os.environ.get("MCP_RESOURCE_URI", "http://localhost:8000")


@mcp.custom_route("/.well-known/oauth-protected-resource", methods=["GET"])
async def protected_resource_metadata(_request: Request) -> JSONResponse:
    return JSONResponse({
        "resource": _RESOURCE_URI,
        "authorization_servers": [
            f"https://login.microsoftonline.com/{_TENANT_ID}/v2.0"
        ],
        "bearer_methods_supported": ["header"],
        "scopes_supported": _GRAPH_SCOPES,
    })


def _extract_token(ctx: Context) -> str:
    http_request = ctx.request_context.request
    if http_request is None:
        raise RuntimeError(
            "No HTTP request in context. "
            "This tool requires streamable-http transport."
        )
    auth = http_request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise RuntimeError(
            "Missing or invalid Authorization header. "
            "Authenticate via the authorization server listed at "
            f"{_RESOURCE_URI}/.well-known/oauth-protected-resource"
        )
    return auth[7:]


register_graph_tools(mcp, _azure_settings, _extract_token)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
````

## File: graph/models.py
````python
from datetime import datetime
from typing import Literal, Optional, List
from pydantic import BaseModel


class EmailAddress(BaseModel):
    name: str | None
    address: str | None


class Attendee(BaseModel):
    email: EmailAddress


class Email(BaseModel):
    id: str
    subject: str
    sender_name: str
    sender_email: str | None
    received: datetime
    body: str | None = None
    web_link: str | None = None


class File(BaseModel):
    id: str
    name: str
    is_folder: bool
    size: int | None
    created: datetime | None
    modified: datetime | None
    parent_id: str | None
    web_link: str | None


class Contact(BaseModel):
    id: str
    name: str
    email: str | None


class CalendarEvent(BaseModel):
    id: str
    subject: str
    start: str | None
    end: str | None
    organizer: EmailAddress | None
    attendees: list[Attendee]
    web_link: str | None


# ---------------------------------------------------------------------
EntityType = Literal["email", "file", "event", "contact"]


class SearchResult(BaseModel):
    type: EntityType
    id: str
    title: Optional[str]
    snippet: Optional[str]
    timestamp: Optional[datetime]
    people: List[EmailAddress]
    web_link: Optional[str]
    source: str = "graph"


class User(BaseModel):
    display_name: str | None
    email: str | None
````

## File: graph/repository.py
````python
import sys
from dataclasses import dataclass
from typing import Optional
from configparser import SectionProxy
from datetime import datetime, timezone
from typing import List
import httpx
import asyncio
from azure.identity import DeviceCodeCredential
from msgraph import GraphServiceClient

from msgraph.generated.users.item.user_item_request_builder import (
    UserItemRequestBuilder,
)
from msgraph.generated.users.item.mail_folders.item.messages.messages_request_builder import (
    MessagesRequestBuilder,
)
from msgraph.generated.users.item.messages.item.message_item_request_builder import (
    MessageItemRequestBuilder,
)

from msgraph.generated.drives.item.items.item.children.children_request_builder import (
    ChildrenRequestBuilder,
)

from msgraph.generated.users.item.contacts.contacts_request_builder import (
    ContactsRequestBuilder,
)

from msgraph.generated.users.item.events.events_request_builder import (
    EventsRequestBuilder,
)

from msgraph.generated.drives.item.items.item.search_with_q.search_with_q_request_builder import (
    SearchWithQRequestBuilder,
)

from msgraph.generated.users.users_request_builder import UsersRequestBuilder

from msgraph.generated.search.query.query_post_request_body import QueryPostRequestBody
from msgraph.generated.models.search_request import SearchRequest
from msgraph.generated.models.search_query import SearchQuery


from graph.interface import IGraphRepository
from graph.models import Email, File, Contact, CalendarEvent, EmailAddress, Attendee

import logging
log = logging.getLogger("graph")
log.setLevel(logging.INFO)


class GraphRepository(IGraphRepository):
    settings: SectionProxy
    device_code_credential: DeviceCodeCredential
    user_client: GraphServiceClient

    def __init__(self, config: SectionProxy, credential=None):
        self.settings = config

        client_id = self.settings["clientId"]
        tenant_id = self.settings["tenantId"]
        graph_scopes = self.settings["graphUserScopes"].split(" ")

        if credential is not None:
            self.device_code_credential = credential
        else:
            self.device_code_credential = DeviceCodeCredential(
                client_id=client_id,
                tenant_id=tenant_id,
                prompt_callback=self._device_code_callback,
            )

        self.user_client = GraphServiceClient(
            self.device_code_credential,
            graph_scopes,
        )

    def get_user_token(self):
        scopes = self.settings["graphUserScopes"].split(" ")
        token = self.device_code_credential.get_token(*scopes)
        return token.token

    def _device_code_callback(self, verification_uri, user_code, expires_on):
        print("\nAuthenticate here:", file=sys.stderr)
        print(verification_uri, file=sys.stderr)
        print("Code:", user_code, file=sys.stderr)
        print(file=sys.stderr)

    async def get_user(self):
        query_params = (
            UserItemRequestBuilder.UserItemRequestBuilderGetQueryParameters(
                select=["displayName", "mail", "userPrincipalName"]
            )
        )

        request_config = (
            UserItemRequestBuilder.UserItemRequestBuilderGetRequestConfiguration(
                query_parameters=query_params
            )
        )

        user = await self.user_client.me.get(
            request_configuration=request_config
        )

        return user


# people ------------------------------------------------------------------

    async def _find_directory_users(self, query: str, top: int = 5) -> list[EmailAddress]:
        params = UsersRequestBuilder.UsersRequestBuilderGetQueryParameters(
            select=["displayName", "mail", "userPrincipalName"],
            top=top,
            filter=f"startswith(displayName,'{query}') or startswith(mail,'{query}') or startswith(userPrincipalName,'{query}')"
        )

        cfg = UsersRequestBuilder.UsersRequestBuilderGetRequestConfiguration(
            query_parameters=params
        )

        users = await self.user_client.users.get(request_configuration=cfg)

        out = []
        if users and users.value:
            for u in users.value:
                email = u.mail or u.user_principal_name
                if email:
                    out.append(EmailAddress(name=u.display_name, address=email))

        return out

    async def _find_mail_people(self, query: str, top: int = 5) -> list[EmailAddress]:
        params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
            search=f'"{query}"',
            select=["from","toRecipients","ccRecipients"],
            top=top,
        )

        cfg = MessagesRequestBuilder.MessagesRequestBuilderGetRequestConfiguration(
            query_parameters=params
        )

        res = await self.user_client.me.messages.get(request_configuration=cfg)

        found = {}

        if res and res.value:
            for m in res.value:
                candidates = []

                if m.from_ and m.from_.email_address:
                    candidates.append(m.from_.email_address)

                for lst in [m.to_recipients, m.cc_recipients]:
                    if lst:
                        for r in lst:
                            if r.email_address:
                                candidates.append(r.email_address)

                for c in candidates:
                    if not c.address:
                        continue
                    key = c.address.lower()
                    if key not in found:
                        found[key] = EmailAddress(
                            name=c.name,
                            address=c.address
                        )

        return list(found.values())

    async def _find_contacts(self, query: str, top: int = 5) -> list[EmailAddress]:
        params = ContactsRequestBuilder.ContactsRequestBuilderGetQueryParameters(
            select=["displayName","emailAddresses"],
            top=top,
        )


        cfg = ContactsRequestBuilder.ContactsRequestBuilderGetRequestConfiguration(
            query_parameters=params
        )

        print("before res")
        res = await self.user_client.me.contacts.get(request_configuration=cfg)
        print("after res")

        out = []
        if res and res.value:
            for c in res.value:
                if c.email_addresses:
                    e = c.email_addresses[0]
                    out.append(EmailAddress(name=e.name, address=e.address))

        return out

    async def find_people(self, query: str, top: int = 5) -> list[EmailAddress]:
        print("fetching contacts / dir / mail")
        contacts = await self._find_contacts(query, top)
        print("find contacts done")
        directory = await self._find_directory_users(query, top)
        mail = await self._find_mail_people(query, top)
        print("fetching contacts / dir / mail done")

        print(f"[find_people] query={query!r}")
        print("  contacts :", [(p.name, p.address) for p in contacts])
        print("  directory:", [(p.name, p.address) for p in directory])
        print("  mail     :", [(p.name, p.address) for p in mail])

        merged = {}

        for src in (contacts + directory + mail):
            if not src.address:
                continue
            merged[src.address.lower()] = src

        merged_list = list(merged.values())[:top]

        print("  merged   :", [(p.name, p.address) for p in merged_list])
        print()

        return merged_list

# email ------------------------------------------------------------------

    async def get_inbox(self) -> List[Email]:
        query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
            select=["id", "from", "isRead", "receivedDateTime", "subject", "webLink"],
            top=25,
            orderby=["receivedDateTime DESC"],
        )
        request_config = MessagesRequestBuilder.MessagesRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )

        messages = await self.user_client.me.mail_folders.by_mail_folder_id("inbox").messages.get(
            request_configuration=request_config
        )

        emails: List[Email] = []
        if not messages or not messages.value:
            return emails

        for m in messages.value:
            sender_name = ""
            sender_email = None

            if m.from_ and m.from_.email_address:
                sender_name = (
                    m.from_.email_address.name
                    or m.from_.email_address.address
                    or ""
                )
                sender_email = m.from_.email_address.address


            emails.append(
                Email(
                    id=m.id or "",
                    subject=m.subject or "",
                    sender_name=sender_name,
                    sender_email=sender_email,
                    received=m.received_date_time,
                    web_link=m.web_link
                )
            )

        return emails

    async def get_message_body(self, message_id: str) -> Email | None:
        query_params = MessageItemRequestBuilder.MessageItemRequestBuilderGetQueryParameters(
            select=["id", "subject", "from", "receivedDateTime", "body", "webLink"],
        )

        request_config = MessageItemRequestBuilder.MessageItemRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )

        m = await self.user_client.me.messages.by_message_id(message_id).get(
            request_configuration=request_config
        )

        if not m:
            return None

        sender_name = ""
        sender_email = None

        if m.from_ and m.from_.email_address:
            sender_name = (
                m.from_.email_address.name
                or m.from_.email_address.address
                or ""
            )
            sender_email = m.from_.email_address.address

        body = m.body.content if m.body and m.body.content else None

        return Email(
            id=m.id or "",
            subject=m.subject or "",
            sender_name=sender_name,
            sender_email=sender_email,
            received=m.received_date_time,
            body=body,
            web_link=m.web_link,   # ← correct
        )


    async def search_emails(
        self,
        sender: str | None = None,
        subject: str | None = None,
        received_after: datetime | None = None,
        received_before: datetime | None = None,
        top: int = 25,
    ) -> list[Email]:
        filters: list[str] = []

        if subject:
            filters.append(f"contains(subject, '{subject}')")

        if sender:
            filters.append(f"contains(from/emailAddress/address,'{sender}')")

        if received_after:
            filters.append(f"receivedDateTime ge {received_after}")

        if received_before:
            filters.append(f"receivedDateTime le {received_before}")

        f = " and ".join(filters) if filters else None

        qp = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
            select=["id", "subject", "from", "receivedDateTime", "webLink"],
            top=top,
            filter=f,
        )

        cfg = MessagesRequestBuilder.MessagesRequestBuilderGetRequestConfiguration(
            query_parameters=qp
        )

        res = await self.user_client.me.messages.get(request_configuration=cfg)

        out: list[Email] = []
        for m in (res.value or []) if res else []:
            name = ""
            addr = None
            if m.from_ and m.from_.email_address:
                name = m.from_.email_address.name or m.from_.email_address.address or ""
                addr = m.from_.email_address.address

            out.append(
                Email(
                    id=m.id or "",
                    subject=m.subject or "",
                    sender_name=name,
                    sender_email=addr,
                    received=m.received_date_time,
                    web_link=m.web_link,
                )
            )

        return out


# files ------------------------------------------------------------------

    async def get_drive_items(self) -> List[File]:
        query_params = ChildrenRequestBuilder.ChildrenRequestBuilderGetQueryParameters(
            select=[
                "id",
                "name",
                "webUrl",
                "size",
                "createdDateTime",
                "lastModifiedDateTime",
                "file",
                "folder",
                "parentReference",
            ],
            top=20,
            orderby=["name"]
        )

        request_config = ChildrenRequestBuilder.ChildrenRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )

        drive = await self.user_client.me.drive.get()

        items = await self.user_client.drives.by_drive_id(
            drive.id
        ).items.by_drive_item_id("root").children.get(
            request_configuration=request_config
        )

        files: list[File] = []

        if not items or not items.value: 
            return []

        for item in items.value:
            files.append(
                File(
                    id=item.id,
                    name=item.name,
                    is_folder=item.folder is not None,
                    size=item.size,
                    created=item.created_date_time,
                    modified=item.last_modified_date_time,
                    parent_id=item.parent_reference.id if item.parent_reference else None,
                    web_link=item.web_url,
                )
            )

        return files 



    async def get_file_text(self, file_id: str) -> str:
        content_bytes = await self.get_file_content(file_id)

        # Detect docx by ZIP magic bytes (docx is a zip archive)
        if content_bytes[:4] == b'PK\x03\x04':
            try:
                import io
                from docx import Document
                doc = Document(io.BytesIO(content_bytes))
                text = "\n".join(p.text for p in doc.paragraphs if p.text)
            except Exception:
                try:
                    text = content_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    text = content_bytes.decode("latin-1")
        else:
            try:
                text = content_bytes.decode("utf-8")
            except UnicodeDecodeError:
                text = content_bytes.decode("latin-1")

        MAX_CHARS = 12_000
        if len(text) > MAX_CHARS:
            text = text[:MAX_CHARS] + "\n\n[... content truncated ...]"
        return text

    async def get_files_text_batch(self, file_ids: list[str]) -> list[str]:
        results = await asyncio.gather(
            *[self.get_file_text(fid) for fid in file_ids],
            return_exceptions=True,
        )
        return [
            r if isinstance(r, str) else f"Error reading file {fid}: {r}"
            for fid, r in zip(file_ids, results)
        ]

    async def get_file_content(self, file_id: str, drive_id: str | None = None) -> bytes:
        if drive_id is None:
            drive = await self.user_client.me.drive.get()
            drive_id = drive.id

        content = await (
            self.user_client.drives.by_drive_id(drive_id)
            .items.by_drive_item_id(file_id)
            .content.get()
        )
        return content or b""

    async def search_drive_items_sdk(self, query: str, top: int = 25, drive_id: str | None = None) -> list[File]:
        if drive_id is None:
            drive = await self.user_client.me.drive.get()
            drive_id = drive.id

        qp = SearchWithQRequestBuilder.SearchWithQRequestBuilderGetQueryParameters(
            select=[
                "id","name","webUrl","size","createdDateTime","lastModifiedDateTime",
                "file","folder","parentReference"
            ],
            top=top,
        )
        cfg = SearchWithQRequestBuilder.SearchWithQRequestBuilderGetRequestConfiguration(
            query_parameters=qp
        )

        res = await (
            self.user_client.drives.by_drive_id(drive_id)
            .items.by_drive_item_id("root")
            .search_with_q(query)
            .get(request_configuration=cfg)
        )

        out: list[File] = []
        for item in (res.value or []) if res else []:
            out.append(File(
                id=item.id or "",
                name=item.name or "",
                is_folder=item.folder is not None,
                size=item.size,
                created=item.created_date_time,
                modified=item.last_modified_date_time,
                parent_id=item.parent_reference.id if item.parent_reference else None,
                web_link=item.web_url,
            ))
        return out



        


# contacts ------------------------------------------------------------------

    async def get_contacts(self) -> list[Contact]:
        query_params = ContactsRequestBuilder.ContactsRequestBuilderGetQueryParameters(
            select=["id", "displayName", "emailAddresses"],
            top=15
        )

        request_config = ContactsRequestBuilder.ContactsRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )

        result = await self.user_client.me.contacts.get(
            request_configuration=request_config
        )

        contacts: list[Contact] = []

        if not result or not result.value:
            return []
        
        for c in result.value:
            email = c.email_addresses[0].address if c.email_addresses else None
            contacts.append(
                Contact(
                    id=c.id,
                    name=c.display_name,
                    email=email
                )
            )

        return contacts

# calendar ------------------------------------------------------------------

    async def get_upcoming_events(self) -> list[CalendarEvent]:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

        query_params = EventsRequestBuilder.EventsRequestBuilderGetQueryParameters(
            select=["id", "subject", "start", "end", "attendees", "organizer"],
            top=10,
            orderby=["start/dateTime"],
            filter=f"start/dateTime ge '{now}'",
        )

        request_config = EventsRequestBuilder.EventsRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )

        result = await self.user_client.me.events.get(
            request_configuration=request_config
        )

        events: list[CalendarEvent] = []
        if not result or not result.value:
            return events

        for e in result.value:
            events.append(self.map_event(e))

        return events

    async def get_past_events(self) -> list[CalendarEvent]:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

        query_params = EventsRequestBuilder.EventsRequestBuilderGetQueryParameters(
            select=["id", "subject", "start", "end", "attendees", "organizer"],
            top=10,
            orderby=["start/dateTime desc"],
            filter=f"start/dateTime lt '{now}'",
        )

        request_config = EventsRequestBuilder.EventsRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )

        result = await self.user_client.me.events.get(
            request_configuration=request_config
        )

        events: list[CalendarEvent] = []
        if not result or not result.value:
            return events

        for e in result.value:
            events.append(self.map_event(e))

        return events

    def map_event(self, ev) -> CalendarEvent:
        organizer = None
        if ev.organizer and ev.organizer.email_address:
            organizer = EmailAddress(
                name=ev.organizer.email_address.name,
                address=ev.organizer.email_address.address,
            )

        attendees = []
        if ev.attendees:
            attendees = [
                Attendee(
                    email=EmailAddress(
                        name=a.email_address.name,
                        address=a.email_address.address,
                    )
                )
                for a in ev.attendees
                if a.email_address
            ]

        return CalendarEvent(
            id=ev.id,
            subject=ev.subject,
            start=ev.start.date_time if ev.start else None,
            end=ev.end.date_time if ev.end else None,
            organizer=organizer,
            attendees=attendees,
            web_link=ev.web_link,   # hier
        )


    async def search_events(
        self,
        text: str | None = None,
        location: str | None = None,
        attendee_query: str | None = None,
        start_after: datetime | None = None,
        start_before: datetime | None = None,
        top: int = 25,
    ) -> list[CalendarEvent]:

        filters: list[str] = []

        if text:
            filters.append(f"contains(subject,'{text}')")

        if location:
            filters.append(f"contains(location/displayName,'{location}')")

        if start_after:
            iso = start_after.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            filters.append(f"start/dateTime ge '{iso}'")

        if start_before:
            iso = start_before.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            filters.append(f"start/dateTime le '{iso}'")

        f = " and ".join(filters) if filters else None

        qp = EventsRequestBuilder.EventsRequestBuilderGetQueryParameters(
            select=["id","subject","start","end","attendees","organizer","location", "webLink"],
            top=top,
            filter=f,
            orderby=["start/dateTime"],
        )

        cfg = EventsRequestBuilder.EventsRequestBuilderGetRequestConfiguration(
            query_parameters=qp
        )

        res = await self.user_client.me.events.get(request_configuration=cfg)

        events: list[CalendarEvent] = []
        if not res or not res.value:
            return events

        mapped = [self.map_event(e) for e in res.value]

        # attendee filter (client-side)
        if attendee_query:
            people = await self.find_people(attendee_query)
            emails = {p.address.lower() for p in people if p.address}

            def match(ev: CalendarEvent) -> bool:
                for a in ev.attendees:
                    if a.email and a.email.address and a.email.address.lower() in emails:
                        return True
                return False

            mapped = [ev for ev in mapped if match(ev)]

        return mapped













    ## this is a backup
    # async def search_drive_items(
    #     self,
    #     query: str,
    #     top: int = 25,
    #     drive_id: str | None = None,
    #     folder_id: str = "root",
    # ) -> list[File]:
    #     if drive_id is None:
    #         drive = await self.user_client.me.drive.get()
    #         drive_id = drive.id

    #     # escape single quotes for OData string literal
    #     q = query.replace("'", "''")

    #     if folder_id == "root":
    #         url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root/search(q='{q}')"
    #     else:
    #         url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{folder_id}/search(q='{q}')"

    #     params = {
    #         "$select": ",".join([
    #             "id",
    #             "name",
    #             "webUrl",
    #             "size",
    #             "createdDateTime",
    #             "lastModifiedDateTime",
    #             "file",
    #             "folder",
    #             "parentReference",
    #         ]),
    #         "$top": str(top),
    #     }

    #     token = self.get_user_token()
    #     headers = {"Authorization": f"Bearer {token}"}

    #     async with httpx.AsyncClient(timeout=30) as client:
    #         r = await client.get(url, params=params, headers=headers)
    #         r.raise_for_status()
    #         data = r.json()

    #     out: list[File] = []
    #     for item in data.get("value", []):
    #         out.append(
    #             File(
    #                 id=item.get("id") or "",
    #                 name=item.get("name") or "",
    #                 is_folder=item.get("folder") is not None,
    #                 size=item.get("size"),
    #                 created=item.get("createdDateTime"),
    #                 modified=item.get("lastModifiedDateTime"),
    #                 parent_id=(item.get("parentReference") or {}).get("id"),
    #                 web_link=item.get("webUrl"),
    #             )
    #         )

    #     return out
````

## File: graph/tools.yaml
````yaml
- name: whoami
  description: Identify the currently authenticated user
  method: whoami

# ------------------------------------------------------------------------------- 

- name: findpeople
  description: Resolve a person name to one or more email addresses
  method: find_people
  params:
    - name: name
      type: str

# ------------------------------------------------------------------------------- 

- name: list_email
  description: List the 25 most recent emails from the inbox
  method: list_email

# ------------------------------------------------------------------------------- 

- name: search_email
  description: Search emails by sender address, subject, or received date range
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

# ------------------------------------------------------------------------------- 

- name: read_email
  description: Read the full body of a specific email by its ID
  method: read_email
  params:
    - name: message_id
      type: str

# ------------------------------------------------------------------------------- 

- name: search_files
  description: Search files and folders in OneDrive
  method: search_files
  params:
    - name: query
      type: str
    - name: drive_id
      type: "str | None"
    - name: folder_id
      type: str
      default: "root"

# -------------------------------------------------------------------------------

- name: read_file
  description: Read the text content of a OneDrive file by its ID. Use this after search_files to retrieve the actual contents of a file.
  method: read_file
  params:
    - name: file_id
      type: str

# -------------------------------------------------------------------------------

- name: read_multiple_files
  description: Read the text contents of multiple OneDrive files at once.
    Pass a comma-separated list of file IDs (e.g. "id1,id2,id3").
    Use this when the user asks a question that spans multiple documents.
  method: read_multiple_files
  params:
    - name: file_ids
      type: str

# ------------------------------------------------------------------------------- 

- name: list_contacts
  description: List the user's contacts
  method: list_contacts

# ------------------------------------------------------------------------------- 

- name: list_calendar
  description: List upcoming and recent calendar events
  method: list_calendar

# ------------------------------------------------------------------------------- 

- name: search_calendar
  description: Search calendar events by subject text, location, attendee, or date range
  method: search_events
  params:
    - name: text
      type: "str | None"
    - name: location
      type: "str | None"
    - name: attendee
      type: "str | None"
    - name: start_after
      type: "str | None"
    - name: start_before
      type: "str | None"
````

## File: md/2_6_securityshit.md
````markdown
Ja, maar je mag 2.6 niet reduceren tot: “als de user geen access heeft, geeft de API een fout”.

Dat is **een deel** van security, maar veel te beperkt voor een scriptie.
In dat hoofdstuk moet je tonen welke bredere risico’s en vereisten er zijn wanneer een AI-systeem toegang krijgt tot bedrijfsdata.

## Wat moet daar zeker in?

### 1. Authenticatie en autorisatie

Hier leg je uit:

* **authenticatie**: het verifiëren van de identiteit van de gebruiker of applicatie
* **autorisatie**: bepalen tot welke data en functionaliteiten die geauthenticeerde entiteit toegang heeft

In jouw case is dat inderdaad vaak user-based toegang:

* de agent of MCP-tool roept een externe API aan in naam van de gebruiker
* de onderliggende systemen blijven hun eigen toegangsrechten afdwingen
* als een gebruiker geen rechten heeft, zal de API de toegang weigeren

Maar je moet erbij zeggen dat dit nuttig is omdat:

* de bestaande toegangscontrole van bronsystemen behouden blijft
* de agent dus niet zomaar meer rechten krijgt dan de gebruiker zelf

### 2. Privacy van bedrijfsdata

Hier gaat het over:

* gevoelige informatie
* persoonsgegevens
* vertrouwelijke documenten
* interne communicatie
* klantgegevens

Je systeem haalt mogelijk data op uit e-mails, CRM, documenten enzovoort. Dus je moet uitleggen dat niet alle data zomaar naar een taalmodel gestuurd mag worden. Belangrijke vragen:

* welke data mag doorgestuurd worden?
* hoeveel context geef je mee?
* vermijd je onnodige blootstelling van gevoelige data?
* hoe ga je om met logging en caching?

Dit is belangrijker dan veel studenten denken.

### 3. Governance

Dit is het meest vage begrip, dus je moet het concreet maken. In jouw context betekent governance vooral:

* duidelijke regels over welke tools beschikbaar zijn
* controle over welke databronnen aangesproken mogen worden
* afbakening van welke acties agents mogen uitvoeren
* auditability: kunnen nagaan wat het systeem deed
* traceerbaarheid: welke tool werd aangeroepen, met welke input, en welk resultaat kwam terug

Dus governance = controle en beleid rond het gebruik van data en tools.

### 4. Least privilege

Heel belangrijk om te vermelden:
agents en tools mogen idealiter enkel toegang hebben tot wat strikt noodzakelijk is.

Dus:

* geen brede rechten als read-only volstaat
* geen toegang tot alle mailboxen of alle documentsites als dat niet nodig is
* scoped permissions waar mogelijk

Dat is een sterk principe om expliciet te noemen.

### 5. Risico van indirecte data-exposure

Zelfs als een API correct toegang weigert, kan er nog risico zijn:

* gevoelige data kan in prompts terechtkomen
* output kan informatie samenvatten die de gebruiker niet volledig had mogen zien als filtering fout loopt
* logs kunnen gevoelige info bevatten
* tussenresultaten of caches kunnen data bewaren

Dus security is niet alleen “API geeft 403”.

### 6. Tool- en action control

Niet elke tool is even veilig:

* read-only tools zijn veiliger
* write-acties, deletes of updates zijn gevoeliger
* een agent mag niet zomaar autonome acties uitvoeren zonder controle

Dus je kan zeggen dat in enterprisecontext expliciet moet worden bepaald:

* welke tools read-only zijn
* welke acties menselijke bevestiging vereisen
* welke oproepen gelogd of beperkt worden

### 7. Foutafhandeling en veilige defaults

Ook relevant:
als een tool faalt of een gebruiker geen rechten heeft, moet het systeem:

* veilig falen
* geen ongeoorloofde fallback doen
* geen misleidend antwoord hallucineren alsof de data wel beschikbaar was

Dat is een heel goed punt voor jouw thesis:
een autorisatiefout moet correct behandeld
````

## File: md/ARCHITECTURE.md
````markdown
# Architectuur & Request-flow — graphxmaf

## Overzicht

```
Gebruiker
   │
   ▼
[main.py]  ──── MSAL auth (device code / cache) ──▶ Azure AD token
   │
   ├─ start lokale MCP server (subprocess: mcp_api_tool.py :8000)
   │
   ├─ maak httpx.AsyncClient  (Authorization: Bearer <token>)
   │
   ├─ MCPStreamableHTTPTool("graph", url="http://localhost:8000/mcp")
   │
   └─ create_graph_agent(graph_mcp)
         └─ Agent(OpenAIChatClient, tools=[graph_mcp])
               │
               ▼
         agent_framework.devui.serve()  →  browser UI op :8080
```

---

## Lagen

| Laag | Bestand | Rol |
|---|---|---|
| **Entry point** | `main.py` | Auth, server opstarten, agent bouwen |
| **AI agent** | `agent.py` | LLM + MCP tool wrappen in `Agent` |
| **MCP server** | `mcp_api_tool.py` | FastMCP HTTP server, tool-definities |
| **Domain agent** | `entities/graph_agent.py` | Businesslogica, caching, formattering |
| **Repository** | `graph/repository.py` | Graph SDK calls, OData filters |
| **Auth helper** | `auth/token_credential.py` | Bearer token als `azure.core.credentials` |
| **Data models** | `data/classes.py` | Dataclasses: Email, File, Contact, … |
| **Interface** | `entities/IGraphRepository.py` | Abstract base voor repository |

---

## Authenticatie

### Client-side (main.py)
1. `msal.PublicClientApplication` met `client_id` + `tenant_id` uit `config.cfg`.
2. Eerst proberen via **token cache** (`.token_cache.bin`).
3. Als geen cache → **device code flow**: gebruiker gaat naar `login.microsoftonline.com` en vult code in.
4. Resulterende `access_token` wordt opgeslagen en meegestuurd als `Authorization: Bearer <token>` header bij elk HTTP request naar de MCP server.

### Server-side (mcp_api_tool.py)
- Exposeert `/.well-known/oauth-protected-resource` (PRM endpoint) zodat MCP clients weten hoe ze moeten authenticeren.
- `_extract_token(ctx)`: haalt de Bearer token uit de inkomende HTTP request.
- `StaticTokenCredential` (auth/token_credential.py): wrapet de token als `azure.core.credentials.AccessToken` zodat de Graph SDK hem kan gebruiken.

---

## Request-flow: van gebruiker tot Microsoft Graph

```
Gebruiker typt vraag in browser UI (:8080)
   │
   ▼
Agent (OpenAI LLM via agent_framework)
   │   beslist welke tool nodig is
   ▼
MCPStreamableHTTPTool
   │   HTTP POST naar http://localhost:8000/mcp
   │   header: Authorization: Bearer <token>
   ▼
FastMCP server (mcp_api_tool.py)
   │   _extract_token(ctx)  →  token uit header
   │   _make_agent(token)   →  GraphAgent (of uit cache)
   ▼
GraphAgent (entities/graph_agent.py)
   │   businesslogica + in-memory caching
   ▼
GraphRepository (graph/repository.py)
   │   msgraph-sdk  (GraphServiceClient)
   │   OData query parameters samenstellen
   ▼
Microsoft Graph API (graph.microsoft.com)
   │   HTTP response
   ▼
GraphRepository  →  dataclasses (Email, File, …)
GraphAgent       →  formatteert naar tekst string
MCP tool         →  stuurt string terug naar LLM
LLM              →  antwoord naar gebruiker
```

---

## Concrete Graph-aanroepen per tool

### `whoami`
```
GET /me?$select=displayName,mail,userPrincipalName
```

### `findpeople(name)`
Drie parallelle zoekopdrachten, resultaten samenvoegen:
1. **Directory**: `GET /users?$filter=startswith(displayName,'...')` (top 5)
2. **Mail**: `GET /me/messages?$search="..."&$select=from,toRecipients,ccRecipients` (top 5)
3. **Contacts**: `GET /me/contacts?$select=displayName,emailAddresses` (top 5)

### `search_email`
```
GET /me/messages
  ?$select=id,subject,from,receivedDateTime,webLink
  &$filter=contains(from/emailAddress/address,'...')
           and contains(subject,'...')
           and receivedDateTime ge ...
           and receivedDateTime le ...
  &$top=25
```

### `list_email`
```
GET /me/mailFolders/inbox/messages
  ?$select=id,from,isRead,receivedDateTime,subject,webLink
  &$top=25
  &$orderby=receivedDateTime DESC
```

### `read_email(message_id)`
Eerst in-memory cache controleren, anders:
```
GET /me/messages/{id}
  ?$select=id,subject,from,receivedDateTime,body,webLink
```

### `search_files(query)`
```
GET /drives/{drive_id}/items/root/search(q='{query}')
  ?$select=id,name,webUrl,size,createdDateTime,...
  &$top=25
```
Drive ID wordt eerst opgehaald via `GET /me/drive`.

### `list_contacts`
```
GET /me/contacts
  ?$select=id,displayName,emailAddresses
  &$top=15
```

### `list_calendar`
Twee calls:
```
GET /me/events?$filter=start/dateTime ge '{now}'&$orderby=start/dateTime&$top=10
GET /me/events?$filter=start/dateTime lt '{now}'&$orderby=start/dateTime desc&$top=10
```

### `search_calendar`
```
GET /me/events
  ?$filter=contains(subject,'...')
           and contains(location/displayName,'...')
           and start/dateTime ge '...'
           and start/dateTime le '...'
  &$top=25
```
Attendee-filter wordt **client-side** gedaan (Graph OData ondersteunt dit niet direct):
→ `findpeople(attendee)` aanroepen, daarna events filteren op email-adressen.

---

## In-memory caching (GraphAgent)

`GraphAgent` houdt per server-instantie (= per token) een cache bij:

| Cache | Key | Gevuld door |
|---|---|---|
| `_email_cache` | message id | `list_email`, `search_email` |
| `_file_cache` | item id | `list_files`, `search_files` |
| `_contact_cache` | contact id | `list_contacts` |
| `_event_cache` | event id | `list_calendar` |
| `_people_cache` | email address | `find_people` |

`read_email` kijkt eerst in cache voor het opgeslagen bericht; pas als het er niet in staat, doet het een Graph API call.

---

## Configuratie

`config.cfg`:
```ini
[azure]
clientId     = <app registration id>
tenantId     = <tenant id>
graphUserScopes = User.Read Mail.Read Calendars.Read Contacts.Read Files.Read Chat.Read
mcpServerUrl = http://localhost:8000/mcp
```

`.env`:
- `deployment` — naam van het Azure OpenAI deployment (gebruikt door `OpenAIChatClient`)

---

## Lokaal vs. cloud

`main.py` detecteert automatisch of de MCP server lokaal of remote is:

```python
if _is_local_url(mcp_url):        # localhost / 127.0.0.1
    server_proc = _start_local_mcp_server(server_env)
```

- **Lokaal**: `mcp_api_tool.py` wordt gestart als subprocess, poort 8000.
- **Cloud (APIM)**: alleen de `httpx.AsyncClient` met Bearer token is nodig; de server draait al elders.

---

## Dependencies

| Package | Waarvoor |
|---|---|
| `msal` | MSAL OAuth2 / device code flow |
| `azure-identity` | `DeviceCodeCredential` (fallback in repo) |
| `msgraph-sdk` | Typed Graph API client |
| `mcp` / `fastmcp` | MCP server (Streamable HTTP transport) |
| `httpx` | HTTP client voor MCP calls |
| `openai` | LLM backend (via agent_framework) |
| `agent-framework` | Agent loop + devUI + `MCPStreamableHTTPTool` |
| `starlette` | Web framework onder FastMCP |
````

## File: md/CAPABILITIES.md
````markdown
# Agent Capabilities Overview

This MCP server exposes your Microsoft 365 data (mail, calendar, files, contacts, people) via the Microsoft Graph API. Below is a description of everything a user can ask the agent.

---

## Identity

### Who am I?
Returns the display name and email address of the currently authenticated user.

**Example prompts:**
- "Who am I?"
- "What is my email address?"
- "Show me my account info."

---

## People

### Find a person
Search for people by name within your organisation's directory.

**Example prompts:**
- "Find John Doe."
- "Look up people named Sarah."
- "Who is Jan Peeters?"

---

## Email

### List inbox
Returns the most recent emails from your inbox, including subject, sender, and received date.

**Example prompts:**
- "Show me my emails."
- "List my inbox."
- "What are my latest messages?"

### Search emails
Filter emails by one or more criteria. All filters are optional and can be combined.

| Filter | Description | Example value |
|---|---|---|
| `sender` | Filter by sender name or email address | `"jan@example.com"` |
| `subject` | Filter by subject line (partial match) | `"project update"` |
| `received_after` | Only show emails received after this date | `"2024-01-01"` |
| `received_before` | Only show emails received before this date | `"2024-12-31"` |

**Example prompts:**
- "Find emails from jan@example.com."
- "Show me emails with 'invoice' in the subject."
- "Search for emails received after January 2024."
- "Find emails from Sarah about the budget received last month."

### Read an email
Open and read the full body of a specific email. Requires a message ID (returned by list or search).

**Example prompts:**
- "Read that email." *(after a search/list)*
- "Open the email with ID `<message_id>`."
- "What does that message say?"

---

## Files (OneDrive)

### Search files
Search for files or folders in your OneDrive by name or content keyword. Optionally scope the search to a specific drive or folder.

**Example prompts:**
- "Find files named 'budget'."
- "Search for PowerPoint files about Q3."
- "Look for the contract document."
- "Find files in my OneDrive related to the project."

---

## Contacts

### List contacts
Returns all contacts from your Outlook contact list, including name and email address.

**Example prompts:**
- "Show me my contacts."
- "List all my contacts."
- "Who is in my contact list?"

---

## Calendar

### List calendar
Returns upcoming and recent past calendar events, including subject, start time, and end time.

**Example prompts:**
- "Show me my calendar."
- "What meetings do I have?"
- "List my upcoming events."

### Search calendar events
Filter calendar events by one or more criteria. All filters are optional and can be combined.

| Filter | Description | Example value |
|---|---|---|
| `text` | Search by keyword in event title or description | `"standup"` |
| `location` | Filter by meeting location | `"Brussels"` |
| `attendee` | Filter by attendee name or email | `"jan@example.com"` |
| `start_after` | Only show events starting after this date | `"2024-06-01"` |
| `start_before` | Only show events starting before this date | `"2024-06-30"` |

**Example prompts:**
- "Find meetings about the sprint review."
- "Search for events in Brussels."
- "Show me all meetings with Jan next week."
- "What events do I have between June 1 and June 15?"
- "Find all standups after March 1."

---

## Summary Table

| Category | What you can ask | Tool |
|---|---|---|
| Identity | Who am I / my email | `whoami` |
| People | Find a person by name | `findpeople` |
| Email | List inbox | `list_email` |
| Email | Search by sender / subject / date | `search_email` |
| Email | Read full email body | `read_email` |
| Files | Search OneDrive by keyword | `search_files` |
| Contacts | List all contacts | `list_contacts` |
| Calendar | List upcoming & past events | `list_calendar` |
| Calendar | Search events by keyword / location / attendee / date | `search_calendar` |
````

## File: md/declarative_shit.md
````markdown
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
````

## File: md/document-reasoning.md
````markdown
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
````

## File: md/hoofdstuk6_evaluatie.md
````markdown
# Hoofdstuk 6 — Evaluatie

> **Structuurgids voor de masterproef**
> Dit document geeft per sectie uitleg, methodologie, voorbeeldformuleringen en concrete suggesties.
> Het is geen definitieve thesistekst, maar een bouwplan dat je sectie per sectie zelf uitwerkt.

---

## 6.1 Evaluatie-opzet

### Wat staat er in deze sectie?

De evaluatie-opzet beschrijft het *kader* en de *methodologie* van de evaluatie voordat je de resultaten presenteert. Je beantwoordt hier de vragen: wat meet je, hoe meet je het, en waarom op die manier?

### Onderzoeksvragen die deze sectie ondersteunt

- Hoe goed presteert het multi-agent systeem op typische enterprise-gebruiksvragen?
- Is de evaluatiemethode valide en reproduceerbaar?

### Wat je hier opneemt

**a) Overzicht van de evaluatiedimensies**

Je systeem wordt beoordeeld op vier orthogonale dimensies:

| Dimensie | Vraag |
|---|---|
| **Correctheid** | Geeft de agent het juiste antwoord? |
| **Routing** | Wordt de query naar de juiste subagent gestuurd? |
| **Performantie** | Hoe snel reageert het systeem? |
| **Kost** | Hoeveel tokens en API-kosten genereert een query? |

**b) Evaluatiestrategie**

Het systeem maakt gebruik van Large Language Models (LLM's) als kern, wat twee gevolgen heeft voor de evaluatie:

1. *Niet-deterministisch gedrag*: dezelfde query kan bij herhaalde uitvoering een licht ander antwoord opleveren. Je dient dit te vermelden en bij voorkeur elke query meerdere keren uit te voeren (minstens 3 runs) en gemiddelden te rapporteren.
2. *Open antwoorden*: in tegenstelling tot klassieke IR-systemen met binaire relevantie (relevant/niet-relevant) zijn de antwoorden van een LLM-gebaseerde agent vrijgesteld tekst. Dit vereist een LLM-as-evaluator aanpak (zie §6.3).

**c) Testomgeving**

Beschrijf de infrastructuur:
- Model: Azure OpenAI (deployment: `gpt-4o` of equivalent)
- MCP-servers: lokaal gedeployed op poorten 8000 (Graph), 8001 (Salesforce), 8002 (SmartSales)
- Evaluatietool: `eval/script.py` — automatische benchmark die antwoorden opslaat en door een LLM-evaluator laat beoordelen

**d) Automatisering**

Vermeld dat je een geautomatiseerd evaluatiescript hebt ontwikkeld (`eval/script.py`) dat:
- Alle testprompts sequentieel uitvoert per agent
- Latency, tokengebruik en het ruwe antwoord registreert
- Na afloop een LLM-evaluator inschakelt die elk antwoord scoort op een schaal van 1 tot 5
- Resultaten wegschrijft naar een Excel-werkmap met aparte tabbladen per agent

**Voorbeeldformulering:**

> "De evaluatie van het voorgestelde multi-agent systeem is opgebouwd rond vier complementaire dimensies: correctheid van antwoorden, nauwkeurigheid van query-routing, responstijd en tokenkosten. Voor elke dimensie worden zowel kwantitatieve als kwalitatieve methoden gehanteerd. De volledige evaluatieprocedure is geautomatiseerd via een benchmarkscript dat voor elke testvraag de agentrespons registreert, de latency meet, het tokenverbruik logt en de kwaliteit van het antwoord beoordeelt via een afzonderlijke LLM-evaluator."

---

## 6.2 Testscenario's en querycategorieën

### Wat staat er in deze sectie?

Een beschrijving van de testset: welke vragen zijn opgesteld, waarom, en hoe zijn ze gecategoriseerd. Dit is het equivalent van een *benchmark dataset* in klassiek IR-onderzoek.

### Onderzoeksvraag die deze sectie ondersteunt

- Zijn de testscenario's representatief voor de beoogde gebruiksscenario's in een enterprise-omgeving?

### Structuur van de testset

De testset bestaat uit **vier categorieën** queries, ingedeeld per agent en op basis van complexiteit:

#### 6.2.1 Single-agent queries

Single-agent queries testen één gespecialiseerde agent in isolatie. Ze meten of de agent de juiste tools selecteert, de parameters correct construeert en een inhoudelijk correct antwoord retourneert.

**Microsoft Graph Agent** — 11 queries, gedekt door alle 11 beschikbare tools:

| Subcategorie | Voorbeeldquery | Moeilijkheid |
|---|---|---|
| Identiteit | "Who am I in Microsoft 365?" | Eenvoudig |
| E-mail — lijst | "Show me my 5 most recent emails." | Eenvoudig |
| E-mail — zoeken op onderwerp | "Search for emails with 'meeting' in the subject." | Gemiddeld |
| E-mail — zoeken op datum | "Have I received any emails in the last 7 days?" | Gemiddeld |
| E-mail — lezen (geketend) | "What does my most recent email say?" | Moeilijk |
| Personen | "Find the email address of Dorian." | Eenvoudig |
| Kalender — lijst | "What are my upcoming calendar events this week?" | Eenvoudig |
| Kalender — zoeken | "Search my calendar for events in the next 14 days." | Gemiddeld |
| Contacten | "Show me my Microsoft 365 contacts." | Eenvoudig |
| Bestanden — zoeken | "Find any Excel or PDF files in my OneDrive." | Gemiddeld |
| Bestanden — lezen (geketend) | "Search OneDrive for a file called 'report' and read it." | Moeilijk |

**Salesforce Agent** — 10 queries, gedekt door alle 5 tools (`find_accounts`, `find_contacts`, `find_leads`, `get_opportunities`, `get_cases`):

Elke tool wordt getest met minstens één eenvoudige query (basislijst) en één query met filters of extra velden, om te verifiëren of de agent de `filters`- en `extra_fields`-parameters correct benut.

Voorbeelden:
- "List 5 Salesforce accounts." *(eenvoudig)*
- "Find Salesforce accounts in Belgium, including their billing address." *(gemiddeld, vereist `extra_fields` + `filters`)*
- "Show me Salesforce opportunities with an amount greater than 10,000. Include probability." *(gemiddeld)*

**SmartSales Agent** — 22 queries, gedekt door alle 19 tools (locaties, catalogus, orders):

De SmartSales agent beschikt over de rijkste toolset. De testset omvat:
- Basislijst-queries (projectie `simple`)
- Gefilterde queries (via de `q`-parameter met JSON-querysyntax, bv. `{"city":"eq:Brussels"}`)
- Gesorteerde queries (via de `s`-parameter)
- Geketende queries waarbij de agent eerst een lijst ophaalt en vervolgens het uid van het eerste resultaat gebruikt om de detailpagina op te vragen (test of de agent meerdere tools kan combineren)
- Metadataqueries (welke velden zijn filterbaar, sorteerbaar of weergaveerbaar)

#### 6.2.2 Cross-agent queries

Cross-agent queries vereisen dat de orchestrator meerdere subagents aanroept, de tussenresultaten interpreteert en een gecombineerd antwoord retourneert. Deze scenario's testen de coördinatiefunctie van de orchestrator.

| Voorbeeldquery | Betrokken agents |
|---|---|
| "Find contacts named 'John' in both Microsoft 365 and Salesforce." | Graph + Salesforce |
| "Show my calendar events and check if organizers are in Salesforce." | Graph + Salesforce |
| "List SmartSales locations in Brussels and matching Salesforce accounts." | SmartSales + Salesforce |
| "What are my 3 most recent emails? Are those senders in Salesforce?" | Graph + Salesforce |
| "Show open Salesforce opportunities and SmartSales locations in Belgium." | Salesforce + SmartSales |

#### 6.2.3 Moeilijkheidsindeling

Elke query krijgt een van drie moeilijkheidsniveaus:

- **Eenvoudig**: één tool, directe parameters, geen interpretatie vereist
- **Gemiddeld**: filterparameters opstellen, bewuste keuze van extra velden, of kennis van de querysyntax
- **Moeilijk**: meerdere tools achter elkaar (geketend), cross-agent samenwerking, of complexe parameterredenering

**Voorbeeldformulering:**

> "De testset omvat [N] queries verdeeld over vier categorieën: Microsoft Graph ([n1] queries), Salesforce ([n2] queries), SmartSales ([n3] queries) en cross-agent scenarios ([n4] queries). Elke query is geclassificeerd op moeilijkheidsgraad (eenvoudig, gemiddeld of moeilijk) en getagd met de betrokken tools, zodat de resultaten per tool of per moeilijkheidsniveau geaggregeerd kunnen worden. Cross-agent queries worden uitsluitend via de orchestratoragent uitgevoerd en dienen om de coördinatie- en synthesecapaciteiten van het systeem te beoordelen."

---

## 6.3 Evaluatie van correctheid

### Wat staat er in deze sectie?

Hoe beoordeel je of het antwoord van de agent inhoudelijk correct is? Dit is de moeilijkste dimensie omdat antwoorden vrijgesteld tekst zijn en afhankelijk van de werkelijke data in de verbonden systemen.

### Onderzoeksvraag

- Retourneert het systeem inhoudelijk correcte en volledige antwoorden op de gestelde vragen?

### Methode: LLM-as-evaluator

Omdat de antwoorden niet volledig objectief verifieerbaar zijn (de data in Microsoft 365, Salesforce en SmartSales is dynamisch), gebruiken we een *LLM-as-evaluator* aanpak. Dit is een gevestigde methode in recent onderzoek naar LLM-evaluatie (Zheng et al., 2023; Liu et al., 2023).

**Werkwijze:**

Voor elke query is een *verwacht antwoord* opgesteld — een beschrijving van wat een correct en volledig antwoord zou moeten bevatten, onafhankelijk van de specifieke datawaarden. Voorbeeld:

> Query: "Show me my 5 most recent emails."
> Verwacht antwoord: "A list of the 5 most recent inbox emails, each with at minimum the subject line, sender name or email address, and received date/time."

Na het uitvoeren van alle queries beoordeelt een afzonderlijke LLM-instantie (dezelfde Azure OpenAI deployment) elk daadwerkelijk antwoord op een schaal van **1 tot 5**:

| Score | Betekenis |
|---|---|
| 1 | Volledig fout, irrelevant of geen zinvol antwoord |
| 2 | Gedeeltelijk correct, maar met grote lacunes of fouten |
| 3 | Grotendeels correct met enkele opmerkelijke tekortkomingen |
| 4 | Correct met slechts kleine lacunes of opmaakproblemen |
| 5 | Volledig correct en compleet |

De evaluator krijgt als invoer: de oorspronkelijke query, het verwachte antwoord en het daadwerkelijke agentantwoord. Hij retourneert een JSON-object met score en rationale.

**Waarom niet handmatig scoren?**

Handmatige scoring van 50+ queries is tijdsintensief en subjectief. Een LLM-evaluator is sneller, consistent en — bij een goede promptopzet — betrouwbaar genoeg voor een eerste iteratie. Je kunt de validiteit versterken door een steekproef handmatig na te kijken en de overeenstemming te rapporteren.

**Onderscheid: objectief vs. open antwoorden**

| Type antwoord | Voorbeeld | Evaluatiestrategie |
|---|---|---|
| Objectief verifieerbaar | "Who am I?" → displayName + e-mailadres | Controleer of beide velden aanwezig zijn |
| Structureel verifieerbaar | "List locations" → JSON-array met uid-veld | Controleer structuur/formaat |
| Open antwoord | "What does this email say?" → vrije tekst | LLM-evaluator met verwacht antwoord |
| Cross-agent synthese | Gecombineerd antwoord uit twee systemen | LLM-evaluator op volledigheid en bronvermelding |

**Voorbeeldformulering:**

> "De correctheid van de agentantwoorden wordt beoordeeld via een LLM-as-evaluator methodologie. Voor elke testvraag is vooraf een referentieantwoord opgesteld dat beschrijft welke informatie een correct en volledig antwoord dient te bevatten. Een afzonderlijke LLM-instantie — geïsoleerd van de agentuitvoering — vergelijkt het daadwerkelijke agentantwoord met dit referentieantwoord en kent een score toe op een ordinale schaal van 1 tot 5. Deze aanpak is gevalideerd in recent onderzoek naar automatische evaluatie van generatieve systemen (Zheng et al., 2023). Om de betrouwbaarheid van de LLM-evaluator te staven, werd een steekproef van [n] query-antwoordparen tevens handmatig beoordeeld. De inter-rater overeenkomst tussen de LLM-evaluator en de menselijke beoordeling wordt uitgedrukt via de gewogen kappa-score."

---

## 6.4 Evaluatie van query routing

### Wat staat er in deze sectie?

Query routing is de functie van de orchestratoragent: op basis van de inhoud van de vraag beslissen welke subagent(s) worden aangeroepen. Dit is meetbaar en objectief toetsbaar.

### Onderzoeksvraag

- Routeert de orchestrator queries naar de juiste subagent(s)?

### Methode

**a) Grondwaarheid definiëren**

Voor elke query in de testset wordt de *verwachte routing* vooraf bepaald:

| Query | Verwachte routing |
|---|---|
| "Who am I in Microsoft 365?" | `ask_graph_agent` |
| "List 5 Salesforce accounts." | `ask_salesforce_agent` |
| "List SmartSales locations." | `ask_smartsales_agent` |
| "Find contacts in M365 and Salesforce." | `ask_graph_agent` + `ask_salesforce_agent` |

**b) Meten van de werkelijke routing**

De routeringsbeslissing van de orchestrator is observeerbaar via de tool-calls die de agent uitvoert. Het benchmarkscript kan deze loggen door de agentrespons te inspecteren of door de MCP-serverlogs te analyseren.

**c) Metrics**

- **Routing accuracy** (voor single-agent queries): percentage queries waarbij exact de verwachte tool werd aangeroepen.
- **Precision / Recall** (voor cross-agent queries): werden alle verwachte agents aangeroepen (recall) en werden er geen onnodige agents aangeroepen (precision)?

| Metric | Formule |
|---|---|
| Routing accuracy | correct gerouteerde queries / totaal aantal queries |
| Precision (cross-agent) | TP / (TP + FP) |
| Recall (cross-agent) | TP / (TP + FN) |

Waarbij TP = terecht aangeroepen agent, FP = onterecht aangeroepen agent, FN = verwachte agent niet aangeroepen.

**d) Veelvoorkomende routeringsfouten**

- **Over-routing**: de orchestrator roept meerdere agents aan terwijl één volstaat (verhoogt latency en kost)
- **Under-routing**: bij cross-agent queries wordt slechts één agent aangeroepen
- **Mis-routing**: de query wordt naar de verkeerde agent gestuurd (bv. een Salesforce-vraag naar Graph)

**Voorbeeldformulering:**

> "De nauwkeurigheid van query-routing wordt beoordeeld door voor elke testvraag de werkelijke tool-calls van de orchestratoragent te vergelijken met de vooraf bepaalde grondwaarheid. Voor single-agent queries wordt de routing accuracy gerapporteerd als het percentage correct gerouteerde queries. Voor cross-agent queries worden precision en recall berekend op basis van de aanwezigheid of afwezigheid van de verwachte subagenten in de tool-call reeks. Fouten worden gecategoriseerd als over-routing, under-routing of mis-routing."

---

## 6.5 Evaluatie van performantie

### Wat staat er in deze sectie?

Hoe snel reageert het systeem? Performantie is voor een enterprise-zoeksysteem kritisch vanuit gebruiksperspectief.

### Onderzoeksvraag

- Wat is de responstijd van het systeem voor verschillende querytypes, en wat zijn de bottlenecks?

### Gemeten variabelen

Voor elke query wordt de **end-to-end latency** gemeten: de tijd tussen het versturen van de query en het ontvangen van het volledige antwoord van de agent.

```
t_start → agent.run(query) → t_end
response_time = t_end - t_start
```

Dit omvat alle componenten: de LLM-inferentie van de agent, de tool-calls naar de MCP-servers, de externe API-calls (Graph API, Salesforce API, SmartSales API) en de synthese van het antwoord.

### Uitsplitsing per laag (indien instrumentatie beschikbaar)

| Laag | Wat het meet |
|---|---|
| Agent LLM | Tijd voor reasoning + tool-selectie |
| MCP-server | Tijd voor tool-verwerking + authenticatie |
| Externe API | Netwerklatency + API-responstijd |

In de huidige implementatie is end-to-end latency de meest praktische maatstaf, tenzij je aanvullend per-laag logging implementeert.

### Analyse

Rapporteer de volgende statistieken per agent en per moeilijkheidsniveau:

- Gemiddelde responstijd (`μ`)
- Mediaan (`p50`)
- 95e percentiel (`p95`) — relevant voor worst-case gebruikservaring
- Standaarddeviatie (`σ`)

**Hypothese om te testen:**

> *Cross-agent queries hebben een significant hogere latency dan single-agent queries, omdat de orchestrator sequentieel meerdere subagents aanroept.*

Dit is te toetsen met een eenvoudige statistische test (bv. Mann-Whitney U-test) gegeven de kleine steekproefomvang.

**Invloedsfactoren om te vermelden:**

- Geketende tool-calls (bv. `list_locations` → `get_location`) verhogen de latency lineair
- Externe API's (Graph, Salesforce, SmartSales) introduceren variabele netwerkvertraging
- LLM-inferentie is afhankelijk van de outputlengte (meer tokens = trager)

**Voorbeeldformulering:**

> "De performantie van het systeem wordt uitgedrukt in end-to-end responstijd, gemeten als het tijdsinterval tussen het indienen van de query en het ontvangen van het volledige agentantwoord. Per query worden gemiddelde, mediaan en 95e percentiel gerapporteerd. De verwachting is dat cross-agent queries — waarbij de orchestratoragent meerdere subagents sequentieel aanroept — een significant hogere latency vertonen dan single-agent queries. Dit patroon wordt empirisch getoetst op basis van de benchmarkresultaten."

---

## 6.6 Evaluatie van kost

### Wat staat er in deze sectie?

Hoeveel tokens verbruikt het systeem per query, en wat zijn de geschatte API-kosten? Dit is relevant voor schaalbaarheid en bedrijfsmatige inzetbaarheid.

### Onderzoeksvraag

- Wat is het tokenverbruik per querykategorie, en welke cost drivers zijn het meest impactvol?

### Gemeten variabelen

Voor elke query wordt geregistreerd:

| Variabele | Definitie |
|---|---|
| `input_tokens` | Tokens in de prompt (systeemprompt + gebruikersvraag + tool-beschrijvingen + tool-resultaten) |
| `output_tokens` | Tokens in het antwoord van de agent |
| `total_tokens` | `input_tokens` + `output_tokens` |

Deze waarden zijn beschikbaar via de `usage`-velden in de Azure OpenAI API-respons.

### Kost berekening

De kosten per query worden berekend als:

```
kost (USD) = (input_tokens / 1000) × prijs_input + (output_tokens / 1000) × prijs_output
```

De prijzen zijn afhankelijk van het gebruikte model (bv. voor GPT-4o: $2.50 / 1M input tokens, $10.00 / 1M output tokens — controleer actuele Azure-prijzen).

### Analyse

Rapporteer per agent en per querykategorie:

- Gemiddeld totaal tokenverbruik
- Verhouding input/output tokens (hoge input-tokens wijzen op grote tool-resultaten of lange systeemprompts)
- Geschatte kosten per query en geëxtrapoleerde maandkost bij typisch gebruik

**Cost drivers identificeren:**

Bij LLM-gebaseerde agenten zijn de grootste cost drivers:
1. **Systeemprompt**: de instructies voor elke agent worden bij elke aanroep meegestuurd
2. **Tool-beschrijvingen**: de MCP-tools worden als JSON-schema aan de LLM doorgegeven
3. **Tool-resultaten**: de ruwe API-respons (bv. een lijst van 50 locaties) kan groot zijn
4. **Geketende calls**: bij meerdere tool-calls worden de tussenresultaten accumulatief meegestuurd in de context

**Hypothese:**

> *Cross-agent queries genereren significant meer tokens dan single-agent queries, omdat de orchestrator de volledige subagent-respons opneemt in zijn context voordat hij het eindantwoord formuleert.*

**Voorbeeldformulering:**

> "Het tokenverbruik per query wordt gerapporteerd op basis van de `usage`-metadata die door de Azure OpenAI API wordt teruggegeven. Onderscheid wordt gemaakt tussen input- en outputtokens, waarbij inputtokens de systeemprompt, gebruikersvraag, tool-schemabeschrijvingen en eventuele tool-resultaten omvatten. Op basis van de actuele Azure OpenAI-prijslijst wordt de kostprijs per query en per querycategorie berekend. De resultaten illustreren de trade-off tussen querycomplexiteit en operationele kost."

---

## 6.7 Beperkingen van de evaluatie

### Wat staat er in deze sectie?

Elke evaluatie heeft limieten. Het is academisch belangrijk om deze eerlijk te benoemen — het versterkt de geloofwaardigheid van je werk.

### Beperkingen en hoe ze te formuleren

**a) Kleine testset**

De testset bestaat uit [N] queries. Dit is voldoende om de functionaliteit te demonstreren, maar te klein voor statistische generalisering. De resultaten zijn indicatief, niet exhaustief.

> "De testset omvat [N] queries en is derhalve niet representatief voor alle mogelijke enterprise-gebruiksvragen. De gepresenteerde resultaten dienen als indicatieve benchmark en laten geen veralgemenende statistische uitspraken toe."

**b) Dynamische data — geen reproduceerbare grondwaarheid**

De onderliggende data in Microsoft 365, Salesforce en SmartSales is dynamisch: e-mails, agenda-items en CRM-records wijzigen continu. Hierdoor zijn de antwoorden van het systeem niet exact reproduceerbaar tussen twee opeenvolgende testmomenten.

> "Omdat de onderliggende bedrijfssystemen dynamische data bevatten, zijn de agentantwoorden afhankelijk van de toestand van die systemen op het moment van testuitvoering. Dit maakt exacte reproduceerbaarheid onmogelijk en vereist de LLM-as-evaluator aanpak waarbij correctheid structureel — en niet datawaarde-specifiek — wordt beoordeeld."

**c) LLM-evaluator bias**

De LLM-evaluator is zelf een LLM en kan systematisch bepaalde antwoordstijlen prefereren (bv. uitgebreidere antwoorden hoger scoren). Bovendien gebruikt de evaluator hetzelfde basismodel als de geëvalueerde agent, wat een potentieel zelfbeoordelingseffect introduceert.

> "De LLM-evaluator is niet vrij van bias: er bestaat een risico op zelfbeoordelingseffecten wanneer dezelfde modelarchitectuur zowel de antwoorden genereert als beoordeelt. Toekomstig onderzoek zou een externe evaluator (bv. een ander model of menselijke beoordelaars) kunnen inzetten om dit risico te mitigeren."

**d) Niet-deterministisch gedrag**

LLM's produceren bij herhaalde uitvoering licht afwijkende antwoorden (temperature > 0). Zelfs bij temperature = 0 kunnen kleine variaties optreden door tokensampling. Dit introduceert variantie in de correctheids- en latentymetingen.

> "Het niet-deterministische karakter van LLM-inferentie impliceert dat de gemeten latency en correctheidsscores variëren bij herhaalde uitvoering van dezelfde query. Om dit effect te beperken worden gemiddelden over meerdere runs gerapporteerd."

**e) Geen gebruikersstudie**

De evaluatie is volledig geautomatiseerd. Er is geen gebruikersstudie uitgevoerd om te meten of de antwoorden ook als nuttig worden ervaren door echte eindgebruikers. Gepercipieerde bruikbaarheid (usability) is een andere dimensie dan technische correctheid.

> "De evaluatie beperkt zich tot technische correctheid en performantie. Gebruikerstevredenheid en gepercipieerde bruikbaarheid — dimensies die relevant zijn vanuit een HCI-perspectief — vallen buiten het bestek van dit onderzoek en bieden aanknopingspunten voor vervolgonderzoek."

**f) Beperkte dekking van randgevallen**

De testset bevat geen adversariale queries (queries die het systeem bewust proberen te misleiden), ambigue queries (waarbij meerdere routeringsbeslissingen verdedigbaar zijn) of queries over niet-bestaande data. Deze randgevallen zijn relevant voor productie-inzet maar vallen buiten de scope van deze evaluatie.

---

## Referenties (suggesties)

Voeg in je bibliografie minstens de volgende types bronnen toe voor het evaluatiehoofdstuk:

- **LLM-as-evaluator**: Zheng, L. et al. (2023). *Judging LLM-as-a-judge with MT-Bench and Chatbot Arena.* NeurIPS.
- **RAG-evaluatie**: Es, S. et al. (2023). *RAGAS: Automated Evaluation of Retrieval Augmented Generation.* arXiv.
- **Agent-evaluatie**: Liu, X. et al. (2023). *AgentBench: Evaluating LLMs as Agents.* arXiv.
- **Multi-agent systemen**: Wang, L. et al. (2024). *A Survey on Large Language Model based Autonomous Agents.* Frontiers of Computer Science.

---

## Overzichtstabel: evaluatiedimensies

| Dimensie | Sectie | Metric | Methode |
|---|---|---|---|
| Correctheid | 6.3 | LLM-score 1–5 | LLM-as-evaluator met referentieantwoord |
| Routing | 6.4 | Routing accuracy, Precision, Recall | Vergelijking tool-calls met grondwaarheid |
| Performantie | 6.5 | Latency (μ, p50, p95, σ) | Tijdmeting per query (end-to-end) |
| Kost | 6.6 | Input/output tokens, USD/query | Azure OpenAI `usage`-metadata |

---

*Gegenereerd als schrijfhulp voor masterproef, sectie 6 — Evaluatie.*
*Pas de formulering en de concrete getallen aan op basis van je werkelijke resultaten.*
````

## File: md/LOCATIONS.md
````markdown
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
````

## File: md/salesforce_agent.md
````markdown
# Salesforce Agent — Architecture & Auth Reference

## Overview

The Salesforce integration is a full stack: auth → MCP server subprocess → tool routing → SOQL repository → AI agent → orchestrator. Everything is wired up in `main.py` at startup.

```
main.py
  ├── authenticate_salesforce()       # JWT Bearer → access_token + instance_url
  ├── _start_salesforce_mcp_server()  # spawns salesforce.mcp_server as subprocess
  ├── MCPStreamableHTTPTool           # HTTP client with Bearer token header
  └── create_salesforce_agent()       # Agent wrapping the MCP tool
        └── create_orchestrator_agent()  # routes queries to SF or Graph agent
```

---

## 1. Authentication — JWT Bearer Token Flow

**File:** `salesforce/auth.py`

Salesforce is authenticated **before** anything else starts. The app uses the **OAuth 2.0 JWT Bearer Token flow** — no interactive login, no password prompt, no MFA issues.

### How it works

1. Read `SF_CLIENT_ID` and `SF_USERNAME` from `.env`.
2. Load the RSA private key from `SF_PRIVATE_KEY_PATH` (file path, e.g. `salesforce.key`) or `SF_PRIVATE_KEY` (PEM string in env).
3. Build a signed JWT with these claims:

   | Claim | Value |
   |-------|-------|
   | `iss` | `SF_CLIENT_ID` (the Connected App's Consumer Key) |
   | `sub` | `SF_USERNAME` (e.g. `aalb@easi.net/ai-search`) |
   | `aud` | `SF_LOGIN_URL` (e.g. `https://test.salesforce.com`) |
   | `exp` | `now + 180 seconds` (Salesforce maximum) |

4. Sign the JWT with `RS256` using the private key (PyJWT + cryptography).
5. POST to `{login_url}/services/oauth2/token` with:
   ```
   grant_type = urn:ietf:params:oauth:grant-type:jwt-bearer
   assertion  = <signed JWT>
   ```
6. Parse the response → `SalesforceCredentials(access_token, instance_url)`.

### Entry point

`main.py` calls:
```python
sf_creds = authenticate_salesforce(login_url=sf_login_url)
```

`authenticate_salesforce()` reads env vars and delegates to `authenticate_jwt()`, which does the JWT construction and POST.

### Required files & env vars

| Env var | Purpose |
|---------|---------|
| `SF_CLIENT_ID` / `SF_CONSUMER_KEY` | Connected App consumer key |
| `SF_USERNAME` | Salesforce username (with sandbox alias suffix if needed) |
| `SF_PRIVATE_KEY_PATH` | Path to the RSA `.key` file (currently `salesforce.key`) |
| `SF_PRIVATE_KEY` | Alternative: PEM string directly in env |
| `SF_LOGIN_URL` | `https://test.salesforce.com` for sandbox, `https://login.salesforce.com` for prod |

**Key files in repo root:**
- `salesforce.key` — RSA private key (PEM format), used to sign the JWT
- `salesforce.crt` — Certificate (public key), uploaded to the Salesforce Connected App

### Salesforce side requirements

The Connected App in Salesforce must:
- Have the digital certificate (`salesforce.crt`) uploaded under "Use digital signatures"
- Have the user (`SF_USERNAME`) pre-authorized in the Connected App policies
- Have the OAuth scopes: `api`, `refresh_token` (at minimum)

### Error type

Any failure raises `SalesforceAuthError(RuntimeError)` with the Salesforce JSON `error_description` included.

---

## 2. MCP Server — `salesforce/mcp_server.py`

After auth, `main.py` spawns the MCP server as a **subprocess** (only when the URL is localhost):

```python
sf_proc = _start_salesforce_mcp_server(sf_server_env, sf_mcp_url)
```

The server runs at `http://localhost:8001/mcp` (FastMCP, streamable-HTTP transport).

Two critical env vars are passed to the subprocess:
- `SF_INSTANCE_URL` — the resolved Salesforce instance URL from auth (e.g. `https://yourorg.my.salesforce.com`)
- `MCP_RESOURCE_URI` — the MCP server's own base URL

### OAuth metadata endpoint

The server exposes:
```
GET /.well-known/oauth-protected-resource
→ { "resource": "<MCP_RESOURCE_URI>", "bearer_methods_supported": ["header"] }
```

This is the standard MCP OAuth discovery endpoint.

### Token extraction

Each tool call extracts the Bearer token from the incoming HTTP `Authorization` header:
```python
def _extract_token(ctx: Context) -> str:
    auth = http_request.headers.get("authorization", "")
    return auth[7:]  # strips "Bearer "
```

The token passed in is the **Salesforce access token** acquired during startup in `main.py`, forwarded via `httpx.AsyncClient(headers={"Authorization": f"Bearer {sf_creds.access_token}"})`.

---

## 3. Tool Registration — `salesforce/mcp_router.py`

Tools are not hardcoded — they are loaded dynamically from `salesforce/tools.yaml` at server startup.

```python
register_salesforce_tools(mcp, _INSTANCE_URL, _extract_token)
```

For each tool definition in the YAML:
1. Build a dynamic `async def handler(ctx, **kwargs)` closure.
2. Construct a proper `inspect.Signature` so FastMCP can introspect parameter types.
3. Register with `mcp.tool(name=..., description=...)`.

### Method alias

`find_accounts` in the YAML maps to `get_accounts` in the repository (via `_SF_METHOD_ALIASES`).

### Repo caching

`SalesforceRepository` instances are cached per access token:
```python
_repo_cache: dict[str, SalesforceRepository] = {}
```

---

## 4. Tools — `salesforce/tools.yaml`

Five tools are registered:

| Tool name | Repository method | Description |
|-----------|-------------------|-------------|
| `find_accounts` | `get_accounts` | Search accounts by name or filter by industry/type/etc. |
| `find_contacts` | `find_contacts` | Search contacts by name or email |
| `find_leads` | `find_leads` | Search leads by name, email, or company |
| `get_opportunities` | `get_opportunities` | List opportunities, filter by account ID or stage |
| `get_cases` | `get_cases` | List cases, filter by account ID or status |

Each tool supports:
- `query` — plain text keyword (triggers a `LIKE` condition on the primary name field)
- `extra_fields` — list of extra SOQL columns to SELECT (strict allowlist per object)
- `filters` — `{SoqlField: value}` dict for additional WHERE conditions (strict allowlist)

---

## 5. Repository — `salesforce/repository.py`

`SalesforceRepository` executes **SOQL queries** against the Salesforce REST API.

**API version:** `v59.0`
**Endpoint pattern:** `{instance_url}/services/data/v59.0/query?q=<soql>`

### Key design decisions

- **Allowlists** — every object has `_*_SELECTABLE` (extra fields you can SELECT) and `_*_FILTERABLE` (fields you can filter on). Anything not in these sets is silently ignored.
- **Numeric fields** — fields like `NumberOfEmployees`, `AnnualRevenue`, `Probability` use exact equality (`=`); string fields use `LIKE '%...%'`.
- **SQL injection prevention** — `_esc()` escapes single quotes before interpolating user input into SOQL.
- **Default limits** — most methods default to `top=25` records.

### Base fields per object

| Object | Always selected |
|--------|----------------|
| Account | Id, Name, Industry, Website |
| Contact | Id, FirstName, LastName, Email, Account.Name |
| Lead | Id, FirstName, LastName, Email, Company, Status |
| Opportunity | Id, Name, StageName, Amount, CloseDate, Account.Name |
| Case | Id, Subject, Status, Priority, Account.Name, CreatedDate |

### Pydantic models — `salesforce/models.py`

Each repository method returns typed Pydantic models:
- `SalesforceAccount`
- `SalesforceContact`
- `SalesforceLead`
- `SalesforceOpportunity`
- `SalesforceCase`

---

## 6. The Agent — `agents/salesforce_agent.py`

```python
def create_salesforce_agent(salesforce_mcp):
    return Agent(
        client=AzureOpenAIChatClient(deployment="gpt-4o-mini", ...),
        name="SalesforceAgent",
        tools=[salesforce_mcp],   # the MCPStreamableHTTPTool
        ...
    )
```

### LLM

Azure OpenAI — `gpt-4o-mini`, endpoint/key from `.env` (`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `deployment`), API version `2024-12-01-preview`.

### Tool selection rules (from system prompt)

- `find_accounts` → questions about companies or accounts
- `find_contacts` → questions about existing CRM people
- `find_leads` → questions about prospective customers
- `get_opportunities` → questions about deals or sales pipeline
- `get_cases` → questions about support tickets

Rules are strict: only call tools the request explicitly requires, never speculatively.

### Output format

The agent returns **raw JSON** — no prose:
- Single tool called → return the tool result directly
- Multiple tools called → return `[{"tool": "<name>", "result": <result>}, ...]`

---

## 7. Orchestrator — `agents/orchestrator_agent.py`

The `OrchestratorAgent` sits above both agents and routes queries:

```python
def create_orchestrator_agent(graph_agent: Agent, salesforce_agent: Agent) -> Agent:
```

It wraps each sub-agent as a `FunctionTool`:
- `ask_graph_agent` — Microsoft 365 data (email, calendar, OneDrive, contacts, identity)
- `ask_salesforce_agent` — CRM data (accounts, contacts, leads, opportunities, cases)

Routing rules:
- M365 data → `ask_graph_agent`
- CRM data → `ask_salesforce_agent`
- Spans both → call both, combine results (clearly labeled "From Microsoft 365:" / "From Salesforce:")

Both sub-agent tools have `approval_mode="never_require"` — no human confirmation needed.

---

## 8. Startup flow (end-to-end)

```
main.py
│
├─ 1. Read config.cfg → sf_login_url, sf_mcp_url
│
├─ 2. authenticate_salesforce(sf_login_url)
│     ├─ read SF_CLIENT_ID, SF_USERNAME, SF_PRIVATE_KEY_PATH from .env
│     ├─ load salesforce.key
│     ├─ build & sign JWT (RS256, exp=now+180s)
│     ├─ POST https://test.salesforce.com/services/oauth2/token
│     └─ return SalesforceCredentials(access_token, instance_url)
│
├─ 3. Pass SF_INSTANCE_URL to subprocess env
│
├─ 4. _start_salesforce_mcp_server(env, "http://localhost:8001/mcp")
│     ├─ python -m salesforce.mcp_server
│     ├─ FastMCP starts on :8001
│     ├─ loads tools from salesforce/tools.yaml
│     └─ waits for port 8001 to be ready
│
├─ 5. Build httpx.AsyncClient with Authorization: Bearer <access_token>
│
├─ 6. MCPStreamableHTTPTool("salesforce", url="http://localhost:8001/mcp", http_client)
│
├─ 7. create_salesforce_agent(salesforce_mcp)
│
├─ 8. create_orchestrator_agent(graph_agent, sf_agent)
│
└─ 9. serve([orchestrator, graph_agent, sf_agent], port=8080)
```

On shutdown (finally block), both the Graph and Salesforce MCP server subprocesses are terminated.

---

## 9. Configuration reference

### `config.cfg` (active section)

```ini
[salesforce]
loginUrl      = https://test.salesforce.com
mcpServerUrl_sf = https://salesforce-mcp.calmsea-ac909996.norwayeast.azurecontainerapps.io/mcp
mcpUserScopes = User.Read
```

> **Note:** `mcpServerUrl_sf` points to Azure Container Apps in production. The `_is_local_url()` check in `main.py` determines whether to spawn the local subprocess or connect to the cloud URL directly.

### `.env` (Salesforce-relevant vars)

```
SF_LOGIN_URL=https://test.salesforce.com
SF_CLIENT_ID=<consumer key from Connected App>
SF_CONSUMER_KEY=<same as SF_CLIENT_ID>
SF_USERNAME=<salesforce username>
SF_PRIVATE_KEY_PATH=salesforce.key
```

The `SF_CLIENT_SECRET`, `SF_PASSWORD`, and `SF_SECURITY_TOKEN` vars in `.env` are **not used** — they are leftovers from an older password-grant flow that was replaced by JWT.
````

## File: md/salesforce_oauth.md
````markdown
# Salesforce OAuth 2.0 Authorization Code Flow

> This document replaces the JWT-Bearer section in `salesforce_agent.md`.
> The JWT flow still exists in `salesforce/auth.py` but is no longer used by
> the MCP server or `main.py`.

---

## Architecture overview

```
Browser / user
  └─ GET /auth/salesforce/login
       └─ 302 → Salesforce OAuth consent page
            └─ GET /auth/salesforce/callback?code=...&state=...
                 ├─ exchange code → SF token endpoint
                 ├─ StoredTokens saved to token_store
                 └─ JSON { "session_token": "<uuid>" }

MCP client (main.py / agent)
  └─ Authorization: Bearer <session_token (UUID)>
       └─ mcp_server._resolve_session(session_token)
            ├─ token_store.get(session_token) → StoredTokens
            ├─ is_expired(buffer=300s)?
            │     yes → refresh_access_token() → token_store.save()
            └─ SalesforceRepository(access_token, instance_url) → SOQL
```

The **session token** is a UUID — it is what the MCP client puts in the
`Authorization: Bearer` header.  The raw Salesforce access token never leaves
the MCP server process.

---

## New files & modules

### `salesforce/token_store.py`

| Symbol | Purpose |
|--------|---------|
| `StoredTokens` | Dataclass: `access_token`, `refresh_token`, `instance_url`, `expires_at`, `user_id`, `username` |
| `StoredTokens.is_expired(buffer=300)` | True if token expires within `buffer` seconds |
| `StoredTokens.from_token_response(dict)` | Build from a raw SF `/services/oauth2/token` response |
| `SalesforceTokenStore` (ABC) | `get`, `save`, `delete`, `generate_session_token` |
| `JsonFileTokenStore` | Dev store: JSON file (`.salesforce_tokens.json`), asyncio-locked |
| `AzureKeyVaultTokenStore` | Prod store: secrets named `sf-session-<uuid>` in Key Vault |
| `build_token_store()` | Factory — reads `SF_TOKEN_STORE` env var |

### New functions in `salesforce/auth.py`

| Function | What it does |
|----------|-------------|
| `build_authorization_url(...)` | Returns the SF `/services/oauth2/authorize?...` redirect URL |
| `async exchange_code_for_tokens(...)` | POST to SF token endpoint with `grant_type=authorization_code` |
| `async refresh_access_token(...)` | POST to SF token endpoint with `grant_type=refresh_token` |

`SalesforceCredentials` gained an optional `expires_at: float` field.

---

## OAuth routes on the MCP server

All routes are served by `salesforce/mcp_server.py` (FastMCP custom routes).

### `GET /auth/salesforce/login`

| Query param | Purpose |
|------------|---------|
| `redirect_after` | (optional) URL to redirect to after login |

1. Generates a CSRF `state` UUID and stores it in `_pending_states`.
2. Calls `build_authorization_url(client_id, redirect_uri, login_url, state)`.
3. Returns `302 → <SF authorize URL>`.

### `GET /auth/salesforce/callback`

| Query param | Required |
|------------|---------|
| `code` | Yes — authorization code from SF |
| `state` | Yes — must match a value in `_pending_states` |

1. Validates state (CSRF protection).
2. Calls `exchange_code_for_tokens(code, client_id, client_secret, redirect_uri, login_url)`.
3. Builds `StoredTokens.from_token_response(token_data)`.
4. Calls `token_store.save(session_token, tokens)`.
5. Returns `200 { "session_token": "<uuid>", "username": "..." }`.

### `POST /auth/salesforce/logout`

Reads the `Authorization: Bearer <session_token>` header, calls
`token_store.delete(session_token)`.

---

## Session resolution (`_resolve_session`)

Called on **every** MCP tool invocation:

```
session_token (UUID from Bearer header)
  │
  ├─ token_store.get(session_token)
  │     None  → RuntimeError("Re-authenticate at /auth/salesforce/login")
  │
  ├─ tokens.is_expired(buffer=300s)?
  │     No  → use as-is
  │     Yes →
  │       refresh_access_token(refresh_token, client_id, client_secret, login_url)
  │         OK     → StoredTokens.from_token_response(refreshed)
  │                   preserve existing refresh_token if not returned
  │                   token_store.save(session_token, new_tokens)
  │         Error  → token_store.delete(session_token)
  │                   RuntimeError("Token refresh failed. Re-authenticate.")
  │
  └─ return SalesforceCredentials(access_token, instance_url, expires_at)
```

---

## Token lifecycle

```
expires_at = issued_at + expires_in   (default: 7200 s / 2 h)
buffer     = 300 s                    (refresh 5 min before actual expiry)

Every MCP tool call:
  is_expired(300)?
    No  → pass access_token directly to SalesforceRepository
    Yes → POST /services/oauth2/token {grant_type=refresh_token, ...}
          → new access_token + new expires_at
          → refresh_token unchanged (unless SF rotates it)
```

Salesforce returns `issued_at` as **epoch milliseconds** (string).
`from_token_response` converts it: `float(issued_at) / 1000`.

---

## Token store backends

| Backend | `SF_TOKEN_STORE` value | Storage |
|---------|----------------------|---------|
| `JsonFileTokenStore` | `file` (default) | `.salesforce_tokens.json` |
| `AzureKeyVaultTokenStore` | `azure_keyvault` | Key Vault secrets `sf-session-<uuid>` |

Optional encryption for the file store: set `SF_TOKEN_STORE_ENCRYPTION_KEY`
to a Fernet key (requires `cryptography` package).

---

## Repo cache invalidation

`mcp_router.py` caches `SalesforceRepository` instances per session:

```python
_repo_cache: dict[str, tuple[SalesforceRepository, str]] = {}
# key = session_token → (repo, cached_access_token)
```

When `_resolve_session` returns a **new** access token after a refresh, the
cached access token no longer matches and a fresh `SalesforceRepository` is
created automatically.

---

## First-time dev setup

```
1.  python -m salesforce.mcp_server        # start MCP server standalone

2.  Open in browser:
    http://localhost:8001/auth/salesforce/login

3.  Log in to Salesforce (sandbox or prod)

4.  Browser lands on callback → returns JSON:
    { "session_token": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx", "username": "..." }

5.  Copy the UUID into .env:
    SF_SESSION_TOKEN=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

6.  Ctrl+C the standalone server

7.  python main.py   ← picks up SF_SESSION_TOKEN, starts everything normally
```

---

## Startup flow in `main.py` (updated)

```
main.py
│
├─ 1. Read config.cfg → sf_mcp_url
│
├─ 2. Read SF_SESSION_TOKEN from env
│     missing → print re-auth instructions → sys.exit(1)
│
├─ 3. Build sf_server_env (os.environ.copy + MCP_RESOURCE_URI)
│     (no SF_INSTANCE_URL injection — MCP server reads it from token_store)
│
├─ 4. _start_salesforce_mcp_server(sf_server_env, sf_mcp_url)
│     └─ python -m salesforce.mcp_server
│          ├─ build_token_store()        → JsonFileTokenStore
│          ├─ _token_store singleton ready
│          └─ FastMCP registers OAuth routes + MCP tools
│
├─ 5. httpx.AsyncClient(Authorization: Bearer <session_token UUID>)
│
├─ 6. MCPStreamableHTTPTool("salesforce", url=sf_mcp_url, http_client)
│
└─ 7. create_salesforce_agent(sf_mcp) → orchestrator → serve(:8080)
```

---

## Environment variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `SF_SESSION_TOKEN` | Yes (at runtime) | — | UUID from the callback; passed as Bearer token |
| `SF_CLIENT_ID` | Yes | — | Connected App consumer key |
| `SF_CLIENT_SECRET` | Yes | — | Connected App consumer secret |
| `SF_LOGIN_URL` | No | `https://test.salesforce.com` | Sandbox or prod login URL |
| `SF_OAUTH_CALLBACK_URL` | No | `http://localhost:8001/auth/salesforce/callback` | Must match Connected App settings |
| `SF_TOKEN_STORE` | No | `file` | `file` or `azure_keyvault` |
| `SF_TOKEN_STORE_FILE` | No | `.salesforce_tokens.json` | Path for the file store |
| `SF_KEY_VAULT_URL` | If KV | — | `https://<vault>.vault.azure.net` |
| `SF_TOKEN_STORE_ENCRYPTION_KEY` | No | — | Fernet key for file encryption |

---

## Salesforce Connected App requirements

The Connected App must have:
- **OAuth scopes**: `api`, `refresh_token` (at minimum)
- **Callback URL**: `http://localhost:8001/auth/salesforce/callback` (dev)
- **Consumer secret** accessible (needed for authorization code exchange)

The digital certificate (`salesforce.crt`) and JWT private key (`salesforce.key`)
are **no longer required** for the authorization code flow.

---

## What did NOT change

| File | Status |
|------|--------|
| `salesforce/repository.py` | Unchanged |
| `salesforce/models.py` | Unchanged |
| `salesforce/tools.yaml` | Unchanged |
| `salesforce/auth.py` (JWT functions) | Unchanged — `authenticate_jwt()` and `authenticate_salesforce()` still exist |
| `agents/salesforce_agent.py` | Unchanged |
| `agents/orchestrator_agent.py` | Unchanged |
| Graph / MSAL auth in `main.py` | Unchanged |
````

## File: md/sequentiediagram.puml
````
@startuml
sequenceDiagram
    actor User as Gebruiker
    participant O as Orchestrator
    participant L as LLM / modelcomponent
    participant GA as Graph agent
    participant SA as Salesforce agent
    participant SMA as SmartSales agent
    participant GMCP as Graph MCP-server
    participant SMCP as Salesforce MCP-server
    participant SMMCP as SmartSales MCP-server
    participant G as Microsoft Graph
    participant SF as Salesforce
    participant SS as SmartSales

    User->>O: Natuurlijke taalquery
    O->>L: Interpreteer query en bepaal relevante agents
    L-->>O: Intentie / routingvoorstel

    alt Query voor Microsoft Graph
        O->>GA: Vraag gegevens op
        GA->>GMCP: Toolaanroep
        GMCP->>G: API-call
        G-->>GMCP: Resultaten
        GMCP-->>GA: Gestructureerde output
        GA-->>O: Deelresultaten
    end

    alt Query voor Salesforce
        O->>SA: Vraag gegevens op
        SA->>SMCP: Toolaanroep
        SMCP->>SF: API-call
        SF-->>SMCP: Resultaten
        SMCP-->>SA: Gestructureerde output
        SA-->>O: Deelresultaten
    end

    alt Query voor SmartSales
        O->>SMA: Vraag gegevens op
        SMA->>SMMCP: Toolaanroep
        SMMCP->>SS: API-call
        SS-->>SMMCP: Resultaten
        SMMCP-->>SMA: Gestructureerde output
        SMA-->>O: Deelresultaten
    end

    O->>L: Combineer en formuleer antwoord
    L-->>O: Samengebracht antwoord
    O-->>User: Eindantwoord
@enduml
````

## File: md/todo.md
````markdown
Authentication Issues

  1. No Salesforce token refresh / expiry handling
  - main.py:188 gets a Salesforce token once at startup, then it's baked into httpx.AsyncClient headers forever. JWT tokens expire (typically 1–2 hours). The app will silently fail mid-session with 401s.
  - The StaticTokenCredential in auth/token_credential.py:14 also fakes expiry as now + 3600 — it never actually refreshes.

  2. Salesforce token passed as a plain dict key in _agent_cache
  - salesforce/mcp_router.py:22 — the cache key is the raw access token string. This creates a memory leak: every new token creates a new cache entry. There's no eviction, no TTL, no max size.

  3. Token stored in a plaintext file
  - main.py:33 — .token_cache.bin is a plaintext MSAL token cache on disk. Not encrypted, not .gitignored safely. Anyone with filesystem access can replay the token.

  4. Microsoft auth only tries accounts[0]
  - main.py:73 — if multiple accounts are cached, it silently uses the first one without checking if it's the right user.

  ---
  Salesforce-specific Issues

  5. print() left in production code
  - salesforce/repository.py:192 — print("soql: ", soql) — debug statement that logs full SOQL queries to stdout.

  6. Private key files in the repo root
  - salesforce.crt and salesforce.key are sitting at the project root. Even if .gitignored they're risky. These should be in a secrets store or at minimum a separate non-committed location.

  7. No SOQL injection protection for numeric fields
  - repository.py:162-163 — numeric fields skip the LIKE escape and are inserted raw: f"{field} = {v}". If someone passes "1 OR 1=1" as a numeric value, it becomes invalid SOQL rather than a security error,
  but there's no explicit numeric validation.

  8. API version hardcoded
  - repository.py:13 — _API_VERSION = "v59.0" — v59.0 is old (Winter '23). Salesforce is at v63.0 now.

  ---
  Architecture Issues

  9. No error handling for sub-agent failures in orchestrator
  - orchestrator_agent.py:19,23 — both ask_graph_agent and ask_salesforce_agent return "(no response from X)" as a string, but exceptions from agent.run() will propagate unhandled up to the orchestrator.

  10. Duplicate env loading across every agent file
  - salesforce_agent.py:6-11, orchestrator_agent.py:8-12, and agents/graph_agent.py all call load_dotenv() and re-read the same env vars independently. This is fine functionally but messy — the config should
  be centralized.


iets van ik vind geen entries met rrne -> bedoel je arne? 

---
- vraag aan dorian: 
2. Privacy van bedrijfsdata

Hier gaat het over:

gevoelige informatie

persoonsgegevens

vertrouwelijke documenten

interne communicatie

klantgegevens

Je systeem haalt mogelijk data op uit e-mails, CRM, documenten enzovoort. Dus je moet uitleggen dat niet alle data zomaar naar een taalmodel gestuurd mag worden. Belangrijke vragen:

welke data mag doorgestuurd worden?

hoeveel context geef je mee?

vermijd je onnodige blootstelling van gevoelige data?

hoe ga je om met logging en caching?

Dit is belangrijker dan veel studenten denken.

---

---
> fetch me all information you can find on Advanced Communications -> done

Here is the information available about Advanced Communications:

From Salesforce:
- **Account Information:**
  - **Name:** Advanced Communications
  - **Industry:** Communications
  - **Website:** [www.advancedcomms.net](http://www.advancedcomms.net)
  - **Phone:** Not available
  - **Number of Employees:** Not available
  - **Annual Revenue:** Not available
  - **Description:** Not available
  
- **Contacts:** No contact information found.

- **Leads:** No leads found.

### From Microsoft 365:
- No information retrieved.

If you need specific details or further assistance, please let me know!

-> maar is wel informatie over anual revenue en stuff
---


- nog geen mogelijkheid om te vragen geef me alle informatie over x 
  - zoekt dan binnen graph -> door emails / calenders / ...
  - zoekt dan binnen salesforce leads / accounts / ... 
      - combineert dan de output

    voor de moment vooral nog vragen van ejo vind me alle emails van / over / ...
    aandacht aan geven pls

-> doet dit automatisch tho
---

Here are the links to the files related to Nutella:

nutella sales.docx
Document.docx
origin.docx

4:40:30 PM
•
↑1453
↓317
(1770 tokens)
•

1
are there any salesforce accounts related to these files?

4:40:59 PM

en dan vraagt ie voor welke files? dus da moet nog beter gedaan worden tho, moet meer state bijhouden binnen de huidige converstatie



---
shit achter die external app checken van salesforce
- wat als meerdere users in 1 app zitten

---
SmartSales — v2

- Verify the exact queryable field name for filtering orders by customer/supplier uid
  (likely `customerUid` / `supplierUid` — confirm via `list_order_queryable_fields` on the live API)
  and update the example in the `list_orders` tool description in smartsales/tools.yaml accordingly.

- Agent should resolve entity names to uids automatically without the user having to specify steps.
  Example: "show me orders from Customer1" should trigger:
  1. list_locations to resolve "Customer1" → uid
  2. list_orders filtered on that uid
  Currently this works if the tool description is explicit enough, but needs validation
  that the agent does this reliably across different phrasings.
````

## File: salesforce/auth.py
````python
# auth.py
"""Salesforce OAuth 2.0 authentication helpers.

Supports two flows (mirrored from simple-salesforce login.py, no dependency):
  - Password Grant  – client_id + client_secret + username + password
  - JWT Bearer      – client_id + RSA private key  (works with MFA)

Call `authenticate_password()` or `authenticate_jwt()` directly, or let
`authenticate_from_env()` pick the right flow from environment variables.
"""

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

import httpx
import jwt as _jwt  # PyJWT[cryptography]

log = logging.getLogger("salesforce.auth")

# ──────────────────────────────────────────────────────────────────────────────
# Public types
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class SalesforceCredentials:
    """Successful Salesforce auth result."""
    access_token: str
    instance_url: str
    expires_at: Optional[float] = None


class SalesforceAuthError(RuntimeError):
    """Raised for any Salesforce authentication failure."""


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _post_token(login_url: str, data: dict) -> SalesforceCredentials:
    """POST to the Salesforce token endpoint and parse the response."""
    url = f"{login_url.rstrip('/')}/services/oauth2/token"
    log.debug("Token request  url=%s  grant_type=%s", url, data.get("grant_type"))

    resp = httpx.post(url, data=data, timeout=30)

    if not resp.is_success:
        # Always include the JSON error_description when Salesforce provides it.
        try:
            body = resp.json()
            code = body.get("error", resp.status_code)
            msg = body.get("error_description", resp.text)
        except Exception:
            code, msg = resp.status_code, resp.text
        raise SalesforceAuthError(f"Salesforce auth failed [{code}]: {msg}")

    result = resp.json()
    creds = SalesforceCredentials(
        access_token=result["access_token"],
        instance_url=result["instance_url"],
    )
    log.info("Salesforce auth OK instance_url=%s", creds.instance_url)
    return creds


# ──────────────────────────────────────────────────────────────────────────────
# Public auth functions
# ──────────────────────────────────────────────────────────────────────────────



def authenticate_jwt(
    *,
    client_id: str,
    username: str,
    private_key: str | None = None,
    private_key_path: str | None = None,
    login_url: str = "https://test.salesforce.com",
) -> SalesforceCredentials:
    """OAuth 2.0 JWT Bearer Token Flow.

    Requires a Connected App with a digital certificate uploaded and the user
    pre-authorised in the Connected App policies.  Works even when MFA is
    enforced because no interactive login takes place.

    Provide exactly one of:
      ``private_key``       – PEM string (e.g. read from env var SF_PRIVATE_KEY)
      ``private_key_path``  – path to a .pem file   (env var SF_PRIVATE_KEY_PATH)

    JWT claims follow simple-salesforce conventions:
      iss = client_id (consumer key)
      sub = username
      aud = login_url  (https://test.salesforce.com or https://login.salesforce.com)
      exp = now + 3 min  (Salesforce maximum)
    """
    if private_key is None and private_key_path is None:
        raise ValueError("Provide either private_key or private_key_path")

    key: str = (
        private_key
        if private_key is not None
        else Path(private_key_path).read_text(encoding="utf-8")  # type: ignore[arg-type]
    )

    log.info("Salesforce JWT bearer  user=%s  login_url=%s", username, login_url)

    payload = {
        "iss": client_id,
        "sub": username,
        "aud": login_url.rstrip("/"),
        "exp": int(time.time()) + 180,  # 3 minutes — Salesforce maximum
    }
    assertion = _jwt.encode(payload, key, algorithm="RS256")

    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": assertion,
    }
    return _post_token(login_url, data)


# ──────────────────────────────────────────────────────────────────────────────
# Convenience: pick flow from environment
# ──────────────────────────────────────────────────────────────────────────────

def authenticate_salesforce(login_url: str) -> SalesforceCredentials:
    client_id = _require_env("SF_CLIENT_ID")
    username = _require_env("SF_USERNAME")

    private_key_path = os.environ.get("SF_PRIVATE_KEY_PATH")
    private_key = os.environ.get("SF_PRIVATE_KEY")
    print("private_key: ", private_key)

    return authenticate_jwt(
        client_id=client_id,
        username=username,
        private_key=private_key,
        private_key_path=private_key_path,
        login_url=login_url,
    )




def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SalesforceAuthError(f"Required environment variable {name!r} is not set")
    return value


# ──────────────────────────────────────────────────────────────────────────────
# OAuth 2.0 Authorization Code Flow
# ──────────────────────────────────────────────────────────────────────────────

def build_authorization_url(
    *,
    client_id: str,
    redirect_uri: str,
    login_url: str,
    state: str,
    scope: str = "api refresh_token",
) -> str:
    """Return the Salesforce OAuth 2.0 authorization URL to redirect the user to."""
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": scope,
    }
    base = f"{login_url.rstrip('/')}/services/oauth2/authorize"
    return f"{base}?{urlencode(params)}"


async def exchange_code_for_tokens(
    *,
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    login_url: str,
) -> dict:
    """Exchange an authorization code for access + refresh tokens.

    Returns the raw JSON response dict from Salesforce.
    Raises ``SalesforceAuthError`` on failure.
    """
    url = f"{login_url.rstrip('/')}/services/oauth2/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, data=data)

    if not resp.is_success:
        try:
            body = resp.json()
            err_code = body.get("error", resp.status_code)
            msg = body.get("error_description", resp.text)
        except Exception:
            err_code, msg = resp.status_code, resp.text
        raise SalesforceAuthError(f"Token exchange failed [{err_code}]: {msg}")

    log.info("OAuth code exchange OK instance_url=%s", resp.json().get("instance_url"))
    return resp.json()


async def refresh_access_token(
    *,
    refresh_token: str,
    client_id: str,
    client_secret: str,
    login_url: str,
) -> dict:
    """Use a refresh token to obtain a new access token.

    Returns the raw JSON response dict from Salesforce.
    Raises ``SalesforceAuthError`` on failure (e.g. ``invalid_grant``).
    """
    url = f"{login_url.rstrip('/')}/services/oauth2/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, data=data)

    if not resp.is_success:
        try:
            body = resp.json()
            err_code = body.get("error", resp.status_code)
            msg = body.get("error_description", resp.text)
        except Exception:
            err_code, msg = resp.status_code, resp.text
        raise SalesforceAuthError(f"Token refresh failed [{err_code}]: {msg}")

    log.info("OAuth token refresh OK")
    return resp.json()
````

## File: salesforce/mcp_router.py
````python
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
````

## File: salesforce/mcp_server.py
````python
# mcp_server.py
import json
import logging
import os
import uuid
from pathlib import Path

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

_RESOURCE_URI = os.environ.get("MCP_RESOURCE_URI", "http://localhost:8001")

# OAuth config — all from env.
_SF_LOGIN_URL = os.environ.get("SF_LOGIN_URL", "https://test.salesforce.com")
_SF_CLIENT_ID = os.environ.get("SF_CLIENT_ID", "")
_SF_CLIENT_SECRET = os.environ.get("SF_CLIENT_SECRET", "")
_SF_CALLBACK_URL = os.environ.get("SF_OAUTH_CALLBACK_URL", "http://localhost:8001/auth/salesforce/callback")

# Token store singleton (file-backed for dev, Key Vault for prod).
_token_store = build_token_store()

log.info(
    "SF OAuth config  client_id=%s  callback=%s  login_url=%s  store=%s",
    _SF_CLIENT_ID[:8] + "…" if _SF_CLIENT_ID else "MISSING",
    _SF_CALLBACK_URL,
    _SF_LOGIN_URL,
    type(_token_store).__name__,
)

# for csrf 
_pending_states: set[str] = set()

# Local pointer file: stores the UUID of the most recently authenticated session.
# main.py reads this via /auth/salesforce/session so it never needs SF_SESSION_TOKEN in .env.
_SESSION_REF_FILE = Path(os.environ.get("SF_SESSION_REF_FILE", ".sf_session.json"))


def _write_session_ref(session_token: str) -> None:
    """Persist the active session UUID so main.py can discover it automatically."""
    _SESSION_REF_FILE.write_text(json.dumps({"session_token": session_token}), encoding="utf-8")
    log.info("Session ref written to %s  session=%s", _SESSION_REF_FILE, session_token)


def _read_session_ref() -> str | None:
    if not _SESSION_REF_FILE.exists():
        return None
    try:
        return json.loads(_SESSION_REF_FILE.read_text(encoding="utf-8")).get("session_token")
    except Exception:
        return None


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
# Session discovery (used by main.py on startup)
# ──────────────────────────────────────────────────────────────────────────────

@mcp.custom_route("/auth/salesforce/session", methods=["GET"])
async def salesforce_current_session(_request: Request) -> JSONResponse:
    """Return the active session token, or 404 if no authenticated session exists.

    main.py calls this on startup instead of reading SF_SESSION_TOKEN from .env.
    The session token is written here by the callback after every successful auth.
    """
    session_token = _read_session_ref()
    if not session_token:
        return JSONResponse({"error": "no_session"}, status_code=404)

    tokens = await _token_store.get(session_token)
    if tokens is None:
        log.warning("Session ref points to unknown session=%s — clearing ref", session_token)
        _SESSION_REF_FILE.unlink(missing_ok=True)
        return JSONResponse({"error": "session_not_found"}, status_code=404)

    return JSONResponse({"session_token": session_token, "username": tokens.username})


# ──────────────────────────────────────────────────────────────────────────────
# OAuth 2.0 Authorization Code Flow routes
# ──────────────────────────────────────────────────────────────────────────────

@mcp.custom_route("/auth/salesforce/login", methods=["GET"])
async def salesforce_login(_request: Request) -> RedirectResponse:
    """Redirect the browser to the Salesforce OAuth consent page."""
    state = str(uuid.uuid4())
    _pending_states.add(state)

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
        log.error("State mismatch: received=%s", state)
        return JSONResponse({"error": "invalid_state"}, status_code=400)

    _pending_states.discard(state)

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
    _write_session_ref(session_token)

    log.info("New session created user=%s session=%s", tokens.username, session_token)
    return JSONResponse({"session_token": session_token, "username": tokens.username})


@mcp.custom_route("/auth/salesforce/logout", methods=["POST"])
async def salesforce_logout(request: Request) -> JSONResponse:
    """Delete the session from the token store."""
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return JSONResponse({"error": "missing_bearer_token"}, status_code=400)

    session_token = auth[7:]
    await _token_store.delete(session_token)
    log.info("Session deleted session=%s", session_token)
    return JSONResponse({"status": "logged_out"})


# ──────────────────────────────────────────────────────────────────────────────
# Session resolution (used by every MCP tool call)
# ──────────────────────────────────────────────────────────────────────────────

async def _resolve_session(session_token: str) -> SalesforceCredentials:
    """Resolve a session UUID to live Salesforce credentials.

    Looks up the session in the token store and auto-refreshes if expired.
    Raises RuntimeError (with a re-auth hint) on any unrecoverable error.
    """
    tokens = await _token_store.get(session_token)
    if tokens is None:
        raise RuntimeError(f"Session not found. Re-authenticate at {_RESOURCE_URI}/auth/salesforce/login")

    if tokens.is_expired():
        if not tokens.refresh_token:
            await _token_store.delete(session_token)
            raise RuntimeError(
                "Session expired and no refresh token available. "
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
            # Preserve identity fields absent from a refresh response.
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
````

## File: salesforce/models.py
````python
from datetime import datetime, date
from pydantic import BaseModel


class SalesforceAccount(BaseModel):
    """
    Salesforce Account record.

    Base fields (always returned): Id, Name, Industry, Website

    Extra fields available via extra_fields parameter (use the SOQL name):
      Phone, Type, BillingStreet, BillingCity, BillingState,
      BillingPostalCode, BillingCountry, NumberOfEmployees,
      AnnualRevenue, Description, CreatedDate, LastModifiedDate

    Filterable fields (base + extra, use in filters parameter):
      Name, Industry, Website, Phone, Type, BillingStreet, BillingCity,
      BillingState, BillingPostalCode, BillingCountry,
      NumberOfEmployees (numeric =), AnnualRevenue (numeric =)
    """
    # Base fields — always returned
    id: str                                  # Id
    name: str                                # Name
    industry: str | None                     # Industry
    website: str | None                      # Website
    # Optional — populated when requested via extra_fields
    phone: str | None = None                 # Phone
    type: str | None = None                  # Type
    billing_street: str | None = None        # BillingStreet
    billing_city: str | None = None          # BillingCity
    billing_state: str | None = None         # BillingState
    billing_postal_code: str | None = None   # BillingPostalCode
    billing_country: str | None = None       # BillingCountry
    number_of_employees: int | None = None   # NumberOfEmployees
    annual_revenue: float | None = None      # AnnualRevenue
    description: str | None = None           # Description
    created_date: str | None = None          # CreatedDate
    last_modified_date: str | None = None    # LastModifiedDate


class SalesforceContact(BaseModel):
    """
    Salesforce Contact record.

    Base fields (always returned): Id, FirstName, LastName, Email, Account.Name

    Extra fields available via extra_fields parameter (use the SOQL name):
      Phone, MobilePhone, Title, Department, MailingStreet, MailingCity,
      MailingState, MailingPostalCode, MailingCountry, LeadSource, CreatedDate

    Filterable fields:
      FirstName, LastName, Email, Account.Name, Phone, Title, Department,
      MailingCity, MailingState, MailingPostalCode, MailingCountry,
      LeadSource, CreatedDate
    """
    # Base fields
    id: str                                  # Id
    first_name: str | None                   # FirstName
    last_name: str                           # LastName
    email: str | None                        # Email
    account_name: str | None                 # Account.Name
    # Optional
    phone: str | None = None                 # Phone
    mobile_phone: str | None = None          # MobilePhone
    title: str | None = None                 # Title
    department: str | None = None            # Department
    mailing_street: str | None = None        # MailingStreet
    mailing_city: str | None = None          # MailingCity
    mailing_state: str | None = None         # MailingState
    mailing_postal_code: str | None = None   # MailingPostalCode
    mailing_country: str | None = None       # MailingCountry
    lead_source: str | None = None           # LeadSource
    created_date: str | None = None          # CreatedDate


class SalesforceOpportunity(BaseModel):
    """
    Salesforce Opportunity record.

    Base fields (always returned): Id, Name, StageName, Amount, CloseDate, Account.Name

    Extra fields available via extra_fields parameter (use the SOQL name):
      Probability, Type, LeadSource, ForecastCategory, Description,
      CreatedDate, LastModifiedDate

    Filterable fields:
      Name, StageName, Account.Name, Type, LeadSource, ForecastCategory,
      Amount (numeric =), Probability (numeric =)
    """
    # Base fields
    id: str                                  # Id
    name: str                                # Name
    stage: str                               # StageName
    amount: float | None                     # Amount
    close_date: date | None                  # CloseDate
    account_name: str | None                 # Account.Name
    # Optional
    probability: float | None = None         # Probability
    type: str | None = None                  # Type
    lead_source: str | None = None           # LeadSource
    forecast_category: str | None = None     # ForecastCategory
    description: str | None = None           # Description
    created_date: str | None = None          # CreatedDate
    last_modified_date: str | None = None    # LastModifiedDate


class SalesforceCase(BaseModel):
    """
    Salesforce Case record.

    Base fields (always returned): Id, Subject, Status, Priority, Account.Name, CreatedDate

    Extra fields available via extra_fields parameter (use the SOQL name):
      Description, Origin, Type, Reason, ClosedDate, LastModifiedDate

    Filterable fields:
      Subject, Status, Priority, Account.Name, Description, Origin,
      Type, Reason
    """
    # Base fields
    id: str                                  # Id
    subject: str                             # Subject
    status: str                              # Status
    priority: str | None                     # Priority
    account_name: str | None                 # Account.Name
    created_date: datetime | None            # CreatedDate
    # Optional
    description: str | None = None           # Description
    origin: str | None = None                # Origin
    type: str | None = None                  # Type
    reason: str | None = None                # Reason
    closed_date: str | None = None           # ClosedDate
    last_modified_date: str | None = None    # LastModifiedDate


class SalesforceLead(BaseModel):
    """
    Salesforce Lead record.

    Base fields (always returned): Id, FirstName, LastName, Email, Company, Status

    Extra fields available via extra_fields parameter (use the SOQL name):
      Phone, MobilePhone, Title, Industry, LeadSource, Street, City,
      State, PostalCode, Country, Rating, NumberOfEmployees,
      AnnualRevenue, CreatedDate

    Filterable fields:
      FirstName, LastName, Email, Company, Status, Phone, Title,
      Industry, LeadSource, City, State, PostalCode, Country, Rating,
      NumberOfEmployees (numeric =), AnnualRevenue (numeric =)
    """
    # Base fields
    id: str                                  # Id
    first_name: str | None                   # FirstName
    last_name: str                           # LastName
    email: str | None                        # Email
    company: str | None                      # Company
    status: str | None                       # Status
    # Optional
    phone: str | None = None                 # Phone
    mobile_phone: str | None = None          # MobilePhone
    title: str | None = None                 # Title
    industry: str | None = None              # Industry
    lead_source: str | None = None           # LeadSource
    street: str | None = None                # Street
    city: str | None = None                  # City
    state: str | None = None                 # State
    postal_code: str | None = None           # PostalCode
    country: str | None = None               # Country
    rating: str | None = None                # Rating
    number_of_employees: int | None = None   # NumberOfEmployees
    annual_revenue: float | None = None      # AnnualRevenue
    created_date: str | None = None          # CreatedDate
````

## File: salesforce/repository.py
````python
from datetime import datetime, date

import httpx

from salesforce.models import (
    SalesforceAccount,
    SalesforceContact,
    SalesforceOpportunity,
    SalesforceCase,
    SalesforceLead,
)

_API_VERSION = "v59.0"

# ---------------------------------------------------------------------------
# Per-object field allowlists
# Keys are SOQL field names; values are the model attribute names.
# ---------------------------------------------------------------------------

_ACCOUNT_SELECTABLE: dict[str, str] = {
    "Phone":              "phone",
    "Type":               "type",
    "BillingStreet":      "billing_street",
    "BillingCity":        "billing_city",
    "BillingState":       "billing_state",
    "BillingPostalCode":  "billing_postal_code",
    "BillingCountry":     "billing_country",
    "NumberOfEmployees":  "number_of_employees",
    "AnnualRevenue":      "annual_revenue",
    "Description":        "description",
    "CreatedDate":        "created_date",
    "LastModifiedDate":   "last_modified_date",
}
_ACCOUNT_FILTERABLE = frozenset({
    "Name", "Industry", "Website",
    *_ACCOUNT_SELECTABLE,
})
_ACCOUNT_NUMERIC = frozenset({"NumberOfEmployees", "AnnualRevenue"})


_CONTACT_SELECTABLE: dict[str, str] = {
    "Phone":              "phone",
    "MobilePhone":        "mobile_phone",
    "Title":              "title",
    "Department":         "department",
    "MailingStreet":      "mailing_street",
    "MailingCity":        "mailing_city",
    "MailingState":       "mailing_state",
    "MailingPostalCode":  "mailing_postal_code",
    "MailingCountry":     "mailing_country",
    "LeadSource":         "lead_source",
    "CreatedDate":        "created_date",
}
_CONTACT_FILTERABLE = frozenset({
    "FirstName", "LastName", "Email", "Account.Name",
    *_CONTACT_SELECTABLE,
})
_CONTACT_NUMERIC: frozenset[str] = frozenset()


_LEAD_SELECTABLE: dict[str, str] = {
    "Phone":             "phone",
    "MobilePhone":       "mobile_phone",
    "Title":             "title",
    "Industry":          "industry",
    "LeadSource":        "lead_source",
    "Street":            "street",
    "City":              "city",
    "State":             "state",
    "PostalCode":        "postal_code",
    "Country":           "country",
    "Rating":            "rating",
    "NumberOfEmployees": "number_of_employees",
    "AnnualRevenue":     "annual_revenue",
    "CreatedDate":       "created_date",
}
_LEAD_FILTERABLE = frozenset({
    "FirstName", "LastName", "Email", "Company", "Status",
    *_LEAD_SELECTABLE,
})
_LEAD_NUMERIC = frozenset({"NumberOfEmployees", "AnnualRevenue"})


_OPP_SELECTABLE: dict[str, str] = {
    "Probability":      "probability",
    "Type":             "type",
    "LeadSource":       "lead_source",
    "ForecastCategory": "forecast_category",
    "Description":      "description",
    "CreatedDate":      "created_date",
    "LastModifiedDate": "last_modified_date",
}
_OPP_FILTERABLE = frozenset({
    "Name", "StageName", "Account.Name",
    *_OPP_SELECTABLE,
})
_OPP_NUMERIC = frozenset({"Probability", "Amount"})


_CASE_SELECTABLE: dict[str, str] = {
    "Description":      "description",
    "Origin":           "origin",
    "Type":             "type",
    "Reason":           "reason",
    "ClosedDate":       "closed_date",
    "LastModifiedDate": "last_modified_date",
}
_CASE_FILTERABLE = frozenset({
    "Subject", "Status", "Priority", "Account.Name",
    *_CASE_SELECTABLE,
})
_CASE_NUMERIC: frozenset[str] = frozenset()


class SalesforceRepository:
    def __init__(self, access_token: str, instance_url: str):
        self.access_token = access_token
        self.instance_url = instance_url.rstrip("/")

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}"}

    async def _query(self, soql: str) -> list[dict]:
        url = f"{self.instance_url}/services/data/{_API_VERSION}/query"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, params={"q": soql}, headers=self._headers())
            r.raise_for_status()
            return r.json().get("records", [])

    @staticmethod
    def _esc(value: str) -> str:
        return value.replace("'", "\\'")

    @staticmethod
    def _resolve_fields(
        extra_fields: list[str] | None,
        selectable: dict[str, str],
    ) -> tuple[list[str], dict[str, str]]:

        """Return (valid_soql_fields, soql→model_attr mapping) from requested extra_fields."""
        safe, mapping = [], {}
        for f in (extra_fields or []):
            if f in selectable:
                safe.append(f)
                mapping[f] = selectable[f]
        return safe, mapping

    def _apply_filters(
        self,
        conditions: list[str],
        filters: dict[str, str] | None,
        filterable: frozenset[str],
        numeric: frozenset[str],
    ) -> None:
        
        """Append validated filter conditions to the conditions list."""
        for field, value in (filters or {}).items():
            if field not in filterable:
                continue
            v = self._esc(str(value))
            if field in numeric:
                conditions.append(f"{field} = {v}")
            else:
                conditions.append(f"{field} LIKE '%{v}%'")

    # ------------------------------------------------------------------
    # Accounts
    # ------------------------------------------------------------------

    async def get_accounts(
        self,
        query: str | None = None,                   # zoekterm bv Technology
        extra_fields: list[str] | None = None,      # extra col die opgezocht meoten worden
        filters: dict[str, str] | None = None,      # filters bv {"Industry": "Technology"}
        top: int = 25,                              # aantal records
    ) -> list[SalesforceAccount]:
        safe_extras, field_map = self._resolve_fields(extra_fields, _ACCOUNT_SELECTABLE)
            # safe_extra: fieldnames voor SOQL query
            # field_map: om terug in response te steken 
        extra_cols = (", " + ", ".join(safe_extras)) if safe_extras else ""

        conditions: list[str] = []
        # Only add a Name LIKE condition from `query` when `filters` doesn't
        # already carry a Name filter (avoids duplicate Name conditions).
        if query and not (filters and "Name" in filters):
            conditions.append(f"Name LIKE '%{self._esc(query)}%'")
        self._apply_filters(conditions, filters, _ACCOUNT_FILTERABLE, _ACCOUNT_NUMERIC)

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        soql = f"SELECT Id, Name, Industry, Website{extra_cols} FROM Account{where} LIMIT {top}"

        print("soql: ", soql)

        records = await self._query(soql)
        return [
            SalesforceAccount(
                id=r["Id"],
                name=r["Name"],
                industry=r.get("Industry"),
                website=r.get("Website"),
                **{field_map[f]: r.get(f) for f in safe_extras},
            )
            for r in records
        ]

    # ------------------------------------------------------------------
    # Contacts
    # ------------------------------------------------------------------

    async def get_contact(self, contact_id: str) -> SalesforceContact | None:
        cid = self._esc(contact_id)
        soql = (
            f"SELECT Id, FirstName, LastName, Email, Account.Name "
            f"FROM Contact WHERE Id = '{cid}' LIMIT 1"
        )
        records = await self._query(soql)
        if not records:
            return None
        r = records[0]
        return SalesforceContact(
            id=r["Id"],
            first_name=r.get("FirstName"),
            last_name=r["LastName"],
            email=r.get("Email"),
            account_name=(r.get("Account") or {}).get("Name"),
        )

    async def find_contacts(
        self,
        query: str | None = None,
        extra_fields: list[str] | None = None,
        filters: dict[str, str] | None = None,
        top: int = 10,
    ) -> list[SalesforceContact]:
        safe_extras, field_map = self._resolve_fields(extra_fields, _CONTACT_SELECTABLE)
        extra_cols = (", " + ", ".join(safe_extras)) if safe_extras else ""

        conditions: list[str] = []
        if query:
            q = self._esc(query)
            conditions.append(f"(Name LIKE '%{q}%' OR Email LIKE '%{q}%')")
        self._apply_filters(conditions, filters, _CONTACT_FILTERABLE, _CONTACT_NUMERIC)

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        soql = (
            f"SELECT Id, FirstName, LastName, Email, Account.Name{extra_cols} "
            f"FROM Contact{where} LIMIT {top}"
        )
        records = await self._query(soql)
        return [
            SalesforceContact(
                id=r["Id"],
                first_name=r.get("FirstName"),
                last_name=r["LastName"],
                email=r.get("Email"),
                account_name=(r.get("Account") or {}).get("Name"),
                **{field_map[f]: r.get(f) for f in safe_extras},
            )
            for r in records
        ]

    # ------------------------------------------------------------------
    # Leads
    # ------------------------------------------------------------------

    async def find_leads(
        self,
        query: str | None = None,
        extra_fields: list[str] | None = None,
        filters: dict[str, str] | None = None,
        top: int = 25,
    ) -> list[SalesforceLead]:
        safe_extras, field_map = self._resolve_fields(extra_fields, _LEAD_SELECTABLE)
        extra_cols = (", " + ", ".join(safe_extras)) if safe_extras else ""

        conditions: list[str] = []
        if query:
            q = self._esc(query)
            conditions.append(f"(Name LIKE '%{q}%' OR Email LIKE '%{q}%' OR Company LIKE '%{q}%')")
        self._apply_filters(conditions, filters, _LEAD_FILTERABLE, _LEAD_NUMERIC)

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        soql = (
            f"SELECT Id, FirstName, LastName, Email, Company, Status{extra_cols} "
            f"FROM Lead{where} LIMIT {top}"
        )
        records = await self._query(soql)
        return [
            SalesforceLead(
                id=r["Id"],
                first_name=r.get("FirstName"),
                last_name=r["LastName"],
                email=r.get("Email"),
                company=r.get("Company"),
                status=r.get("Status"),
                **{field_map[f]: r.get(f) for f in safe_extras},
            )
            for r in records
        ]

    # ------------------------------------------------------------------
    # Opportunities
    # ------------------------------------------------------------------

    async def get_opportunities(
        self,
        account_id: str | None = None,
        stage: str | None = None,
        extra_fields: list[str] | None = None,
        filters: dict[str, str] | None = None,
        top: int = 25,
    ) -> list[SalesforceOpportunity]:
        safe_extras, field_map = self._resolve_fields(extra_fields, _OPP_SELECTABLE)
        extra_cols = (", " + ", ".join(safe_extras)) if safe_extras else ""

        conditions: list[str] = []
        if account_id:
            conditions.append(f"AccountId = '{self._esc(account_id)}'")
        if stage:
            conditions.append(f"StageName LIKE '%{self._esc(stage)}%'")
        self._apply_filters(conditions, filters, _OPP_FILTERABLE, _OPP_NUMERIC)

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        soql = (
            f"SELECT Id, Name, StageName, Amount, CloseDate, Account.Name{extra_cols} "
            f"FROM Opportunity{where} LIMIT {top}"
        )

        records = await self._query(soql)
        result = []
        for r in records:
            close_date = date.fromisoformat(r["CloseDate"]) if r.get("CloseDate") else None
            result.append(
                SalesforceOpportunity(
                    id=r["Id"],
                    name=r["Name"],
                    stage=r["StageName"],
                    amount=r.get("Amount"),
                    close_date=close_date,
                    account_name=(r.get("Account") or {}).get("Name"),
                    **{field_map[f]: r.get(f) for f in safe_extras},
                )
            )
        return result

    # ------------------------------------------------------------------
    # Cases
    # ------------------------------------------------------------------

    async def get_cases(
        self,
        account_id: str | None = None,
        status: str | None = None,
        extra_fields: list[str] | None = None,
        filters: dict[str, str] | None = None,
        top: int = 25,
    ) -> list[SalesforceCase]:
        safe_extras, field_map = self._resolve_fields(extra_fields, _CASE_SELECTABLE)
        extra_cols = (", " + ", ".join(safe_extras)) if safe_extras else ""

        conditions: list[str] = []
        if account_id:
            conditions.append(f"AccountId = '{self._esc(account_id)}'")
        if status:
            conditions.append(f"Status LIKE '%{self._esc(status)}%'")
        self._apply_filters(conditions, filters, _CASE_FILTERABLE, _CASE_NUMERIC)

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        soql = (
            f"SELECT Id, Subject, Status, Priority, Account.Name, CreatedDate{extra_cols} "
            f"FROM Case{where} LIMIT {top}"
        )

        records = await self._query(soql)
        result = []
        for r in records:
            created = (
                datetime.fromisoformat(r["CreatedDate"].replace("Z", "+00:00"))
                if r.get("CreatedDate")
                else None
            )
            result.append(
                SalesforceCase(
                    id=r["Id"],
                    subject=r["Subject"],
                    status=r["Status"],
                    priority=r.get("Priority"),
                    account_name=(r.get("Account") or {}).get("Name"),
                    created_date=created,
                    **{field_map[f]: r.get(f) for f in safe_extras},
                )
            )
        return result
````

## File: salesforce/token_store.py
````python
# token_store.py
"""Per-user Salesforce token persistence.

Provides:
  StoredTokens          – dataclass holding all per-user SF credentials
  SalesforceTokenStore  – ABC
  JsonFileTokenStore    – dev/local store backed by a JSON file
  AzureKeyVaultTokenStore – prod store backed by Azure Key Vault
  build_token_store()   – factory that reads SF_TOKEN_STORE env var
"""

import asyncio
import json
import os
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


# ──────────────────────────────────────────────────────────────────────────────
# StoredTokens
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class StoredTokens:
    """All persisted OAuth 2.0 credentials for a single user session."""
    access_token: str
    refresh_token: str
    instance_url: str
    expires_at: float       # Unix epoch seconds
    user_id: str = ""       # Salesforce user/org URL returned by /id endpoint
    username: str = ""      # last path segment of user_id URL

    def is_expired(self, buffer_seconds: int = 300) -> bool:
        """True if the access token expires within *buffer_seconds*."""
        return time.time() >= (self.expires_at - buffer_seconds)

    @classmethod
    def from_token_response(cls, data: dict) -> "StoredTokens":
        """Build from a raw Salesforce token endpoint JSON response.

        Salesforce returns ``issued_at`` as epoch milliseconds (string).
        ``expires_in`` is not always present; default to 7200 s (2 h).
        """
        issued_at_raw = data.get("issued_at")
        if issued_at_raw:
            issued_at = float(issued_at_raw) / 1000.0
        else:
            issued_at = time.time()

        expires_in = float(data.get("expires_in", 7200))
        expires_at = issued_at + expires_in

        user_id_url = data.get("id", "")
        username = user_id_url.split("/")[-1] if user_id_url else ""

        return cls(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", ""),
            instance_url=data["instance_url"],
            expires_at=expires_at,
            user_id=user_id_url,
            username=username,
        )


# ──────────────────────────────────────────────────────────────────────────────
# Abstract base
# ──────────────────────────────────────────────────────────────────────────────

class SalesforceTokenStore(ABC):
    @abstractmethod
    async def get(self, session_token: str) -> Optional[StoredTokens]:
        """Return stored tokens for *session_token*, or None if not found."""

    @abstractmethod
    async def save(self, session_token: str, tokens: StoredTokens) -> None:
        """Persist *tokens* under *session_token*."""

    @abstractmethod
    async def delete(self, session_token: str) -> None:
        """Remove the entry for *session_token* (no-op if not found)."""

    def generate_session_token(self) -> str:
        return str(uuid.uuid4())


# ──────────────────────────────────────────────────────────────────────────────
# JSON file store (dev / local)
# ──────────────────────────────────────────────────────────────────────────────

class JsonFileTokenStore(SalesforceTokenStore):
    """Stores tokens as JSON in a local file.

    Optional Fernet symmetric encryption when *SF_TOKEN_STORE_ENCRYPTION_KEY*
    is set (must be a URL-safe base64 32-byte key as produced by
    ``Fernet.generate_key()``).
    """

    def __init__(
        self,
        path: str = ".salesforce_tokens.json",
        encryption_key: Optional[str] = None,
    ) -> None:
        self._path = Path(path)
        self._lock = asyncio.Lock()
        self._fernet = None
        if encryption_key:
            try:
                from cryptography.fernet import Fernet
                self._fernet = Fernet(encryption_key.encode())
            except ImportError:
                pass  # cryptography not installed; store plain text

    # ── internal helpers ──────────────────────────────────────────────────────

    def _read_raw(self) -> dict:
        if not self._path.exists():
            return {}
        return json.loads(self._path.read_text(encoding="utf-8"))

    def _write_raw(self, data: dict) -> None:
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # ── SalesforceTokenStore interface ────────────────────────────────────────

    async def get(self, session_token: str) -> Optional[StoredTokens]:
        async with self._lock:
            entry = self._read_raw().get(session_token)
        if entry is None:
            return None
        return StoredTokens(**entry)

    async def save(self, session_token: str, tokens: StoredTokens) -> None:
        async with self._lock:
            data = self._read_raw()
            data[session_token] = asdict(tokens)
            self._write_raw(data)

    async def delete(self, session_token: str) -> None:
        async with self._lock:
            data = self._read_raw()
            data.pop(session_token, None)
            self._write_raw(data)


# ──────────────────────────────────────────────────────────────────────────────
# Azure Key Vault store (production)
# ──────────────────────────────────────────────────────────────────────────────

class AzureKeyVaultTokenStore(SalesforceTokenStore):
    """Stores tokens as JSON secrets in Azure Key Vault.

    Secret names follow the pattern ``sf-session-<uuid>``.
    Uses ``azure.identity.aio.DefaultAzureCredential`` for auth.
    """

    def __init__(self, vault_url: str) -> None:
        self._vault_url = vault_url
        self._client = None

    def _get_client(self):
        if self._client is None:
            from azure.identity.aio import DefaultAzureCredential
            from azure.keyvault.secrets.aio import SecretClient
            self._client = SecretClient(
                vault_url=self._vault_url,
                credential=DefaultAzureCredential(),
            )
        return self._client

    @staticmethod
    def _secret_name(session_token: str) -> str:
        return f"sf-session-{session_token}"

    async def get(self, session_token: str) -> Optional[StoredTokens]:
        client = self._get_client()
        try:
            secret = await client.get_secret(self._secret_name(session_token))
            return StoredTokens(**json.loads(secret.value))
        except Exception:
            return None

    async def save(self, session_token: str, tokens: StoredTokens) -> None:
        client = self._get_client()
        await client.set_secret(
            self._secret_name(session_token),
            json.dumps(asdict(tokens)),
        )

    async def delete(self, session_token: str) -> None:
        client = self._get_client()
        try:
            await client.begin_delete_secret(self._secret_name(session_token))
        except Exception:
            pass


# ──────────────────────────────────────────────────────────────────────────────
# Factory
# ──────────────────────────────────────────────────────────────────────────────

def build_token_store() -> SalesforceTokenStore:
    """Return the right token store based on the ``SF_TOKEN_STORE`` env var.

    Values:
      ``"file"``           – JsonFileTokenStore  (default)
      ``"azure_keyvault"`` – AzureKeyVaultTokenStore
    """
    store_type = os.environ.get("SF_TOKEN_STORE", "file")
    if store_type == "azure_keyvault":
        vault_url = os.environ.get("SF_KEY_VAULT_URL", "")
        return AzureKeyVaultTokenStore(vault_url=vault_url)

    path = os.environ.get("SF_TOKEN_STORE_FILE", ".salesforce_tokens.json")
    encryption_key = os.environ.get("SF_TOKEN_STORE_ENCRYPTION_KEY")
    return JsonFileTokenStore(path=path, encryption_key=encryption_key)
````

## File: salesforce/tools.yaml
````yaml
- name: find_accounts
  description: >
    Search for Salesforce accounts, optionally fetching extra columns and/or
    filtering on specific field values.

    `query` adds a WHERE Name LIKE '%...%' condition — use it ONLY when the user
    is searching for accounts by name (e.g. "find accounts named Acme").
    OMIT `query` (leave it null) when you are filtering by Industry, Type, or any
    other non-name field; in that case use `filters` exclusively.

    `extra_fields` — list of additional SOQL field names to include in the result.
    Allowed values: Phone, Type, BillingStreet, BillingCity, BillingState,
    BillingPostalCode, BillingCountry, NumberOfEmployees, AnnualRevenue,
    Description, CreatedDate, LastModifiedDate.

    `filters` — dict of {SoqlField: value} for additional WHERE conditions.
    String fields use LIKE (substring match); NumberOfEmployees and AnnualRevenue
    use exact numeric equality.
    Allowed filter fields: Name, Industry, Website, Phone, Type, BillingStreet,
    BillingCity, BillingState, BillingPostalCode, BillingCountry,
    NumberOfEmployees, AnnualRevenue, Description.

    Examples:
    - User asks for accounts in Technology sector → query=null, filters={"Industry":"Technology"}
    - User asks for accounts named "Acme" → query="Acme", filters=null
    - User asks for Technology accounts named "Acme" → query="Acme", filters={"Industry":"Technology"}
  method: find_accounts
  params:
    - name: query
      type: "str | None"
      description: >
        Name keyword for a Name LIKE search (plain text, e.g. "Acme Corp").
        Set to null when filtering by Industry or other non-name fields.
        Must NOT be a SOQL expression or field filter.
    - name: extra_fields
      type: "list[str] | None"
      description: >
        Extra SOQL field names to SELECT and return, e.g. ["BillingPostalCode", "Phone"].
    - name: filters
      type: "dict[str, str] | None"
      description: >
        Additional field filters as {SoqlField: value}, e.g. {"BillingPostalCode": "1234"}.
        Only allowed field names are applied; unknown fields are silently ignored.

# -------------------------------------------------------------------------------

- name: find_contacts
  description: >
    Search for Salesforce contacts whose Name or Email contains the given keyword,
    optionally fetching extra columns and/or filtering on specific field values.

    `query` must be a plain keyword (name or email fragment), NOT a SOQL condition.

    `extra_fields` — list of additional SOQL field names to include.
    Allowed values: Phone, MobilePhone, Title, Department, MailingStreet,
    MailingCity, MailingState, MailingPostalCode, MailingCountry,
    LeadSource, CreatedDate.

    `filters` — dict of {SoqlField: value} for WHERE conditions (LIKE substring match).
    Allowed filter fields: FirstName, LastName, Email, Account.Name, Phone, Title,
    Department, MailingCity, MailingState, MailingPostalCode, MailingCountry,
    LeadSource, CreatedDate.
  method: find_contacts
  params:
    - name: query
      type: "str | None"
      description: >
        Name or email keyword (plain text). Must NOT be a SOQL expression.
    - name: extra_fields
      type: "list[str] | None"
      description: >
        Extra SOQL field names to SELECT, e.g. ["MailingPostalCode", "Title"].
    - name: filters
      type: "dict[str, str] | None"
      description: >
        Additional field filters as {SoqlField: value}, e.g. {"MailingCity": "Amsterdam"}.

# -------------------------------------------------------------------------------

- name: find_leads
  description: >
    Search for Salesforce leads whose Name, Email, or Company contains the given keyword,
    optionally fetching extra columns and/or filtering on specific field values.

    `query` must be a plain keyword, NOT a SOQL condition.

    `extra_fields` — list of additional SOQL field names to include.
    Allowed values: Phone, MobilePhone, Title, Industry, LeadSource, Street, City,
    State, PostalCode, Country, Rating, NumberOfEmployees, AnnualRevenue, CreatedDate.

    `filters` — dict of {SoqlField: value} for WHERE conditions.
    String fields use LIKE; NumberOfEmployees and AnnualRevenue use exact equality.
    Allowed filter fields: FirstName, LastName, Email, Company, Status, Phone, Title,
    Industry, LeadSource, City, State, PostalCode, Country, Rating,
    NumberOfEmployees, AnnualRevenue.
  method: find_leads
  params:
    - name: query
      type: "str | None"
      description: >
        Name, email, or company keyword (plain text). Must NOT be a SOQL expression.
    - name: extra_fields
      type: "list[str] | None"
      description: >
        Extra SOQL field names to SELECT, e.g. ["PostalCode", "City"].
    - name: filters
      type: "dict[str, str] | None"
      description: >
        Additional field filters as {SoqlField: value}, e.g. {"Country": "Netherlands"}.

# -------------------------------------------------------------------------------

- name: get_opportunities
  description: >
    List Salesforce opportunities, optionally filtered by account ID or stage,
    with support for extra columns and additional field filters.

    `extra_fields` — list of additional SOQL field names to include.
    Allowed values: Probability, Type, LeadSource, ForecastCategory,
    Description, CreatedDate, LastModifiedDate.

    `filters` — dict of {SoqlField: value} for WHERE conditions.
    Probability and Amount use exact equality; all others use LIKE.
    Allowed filter fields: Name, StageName, Account.Name, Type, LeadSource,
    ForecastCategory, Description, Probability, Amount.
  method: get_opportunities
  params:
    - name: account_id
      type: "str | None"
    - name: stage
      type: "str | None"
    - name: extra_fields
      type: "list[str] | None"
      description: >
        Extra SOQL field names to SELECT, e.g. ["Probability", "Type"].
    - name: filters
      type: "dict[str, str] | None"
      description: >
        Additional field filters as {SoqlField: value}, e.g. {"LeadSource": "Web"}.

# -------------------------------------------------------------------------------

- name: get_cases
  description: >
    List Salesforce cases, optionally filtered by account ID or status,
    with support for extra columns and additional field filters.

    `extra_fields` — list of additional SOQL field names to include.
    Allowed values: Description, Origin, Type, Reason, ClosedDate, LastModifiedDate.

    `filters` — dict of {SoqlField: value} for WHERE conditions (all LIKE substring match).
    Allowed filter fields: Subject, Status, Priority, Account.Name,
    Description, Origin, Type, Reason.
  method: get_cases
  params:
    - name: account_id
      type: "str | None"
    - name: status
      type: "str | None"
    - name: extra_fields
      type: "list[str] | None"
      description: >
        Extra SOQL field names to SELECT, e.g. ["Origin", "Reason"].
    - name: filters
      type: "dict[str, str] | None"
      description: >
        Additional field filters as {SoqlField: value}, e.g. {"Origin": "Email"}.
````

## File: smartsales/auth.py
````python
"""SmartSales authentication helpers.

Token endpoint: POST https://proxy-smartsales.easi.net/proxy/rest/auth/v3/token
Required env vars: GRANT_TYPE, CODE_SMARTSALES, CLIENT_ID_SMARTSALES, CLIENT_SECRET_SMARTSALES
Response: { token_type, scope, expires_in, access_token, refresh_token }
"""

import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

import httpx

log = logging.getLogger("smartsales.auth")

_TOKEN_URL = "https://proxy-smartsales.easi.net/proxy/rest/auth/v3/token"


# ──────────────────────────────────────────────────────────────────────────────
# Public types
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class SmartSalesCredentials:
    """Successful SmartSales auth result."""
    access_token: str
    refresh_token: str
    expires_at: float  # Unix epoch seconds


class SmartSalesAuthError(RuntimeError):
    """Raised for any SmartSales authentication failure."""


# ──────────────────────────────────────────────────────────────────────────────
# Public auth functions
# ──────────────────────────────────────────────────────────────────────────────

def authenticate_smartsales(
    *,
    grant_type: str,
    code: str,
    client_id: str,
    client_secret: str,
) -> SmartSalesCredentials:
    """Obtain a SmartSales access token using the provided credentials."""
    data = {
        "grant_type": grant_type,
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    log.info(
        "SmartSales auth request  grant_type=%s  client_id=%s",
        grant_type,
        client_id[:4] + "…" if len(client_id) > 4 else client_id,
    )

    resp = httpx.post(_TOKEN_URL, data=data, timeout=30)

    if not resp.is_success:
        try:
            body = resp.json()
            msg = body.get("error_description") or body.get("error") or resp.text
        except Exception:
            msg = resp.text
        raise SmartSalesAuthError(f"SmartSales auth failed [{resp.status_code}]: {msg}")

    result = resp.json()
    expires_in = float(result.get("expires_in", 3600))
    creds = SmartSalesCredentials(
        access_token=result["access_token"],
        refresh_token=result.get("refresh_token", ""),
        expires_at=time.time() + expires_in,
    )
    log.info("SmartSales auth OK  expires_in=%ss", int(expires_in))
    return creds


def authenticate_from_env() -> SmartSalesCredentials:
    """Read credentials from environment variables and authenticate."""
    return authenticate_smartsales(
        grant_type=_require_env("GRANT_TYPE"),
        code=_require_env("CODE_SMARTSALES"),
        client_id=_require_env("CLIENT_ID_SMARTSALES"),
        client_secret=_require_env("CLIENT_SECRET_SMARTSALES"),
    )


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SmartSalesAuthError(f"Required environment variable {name!r} is not set")
    return value
````

## File: smartsales/mcp_router.py
````python
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
````

## File: smartsales/mcp_server.py
````python
# mcp_server.py
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from mcp.server.fastmcp import FastMCP, Context
from starlette.requests import Request
from starlette.responses import JSONResponse

from smartsales.auth import (
    SmartSalesAuthError,
    SmartSalesCredentials,
    authenticate_from_env,
)
from smartsales.mcp_router import register_smartsales_tools, _get_repo
from smartsales.token_store import StoredTokens, build_token_store

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("smartsales.mcp_server")

mcp = FastMCP("smartsales", port=8002)

_token_store = build_token_store()

# Session ref file — stores the UUID of the most recently authenticated session.
# main.py reads this via /auth/smartsales/session so it never needs to manage tokens directly.
_SESSION_REF_FILE = Path(os.environ.get("SS_SESSION_REF_FILE", ".ss_session.json"))


def _write_session_ref(session_token: str) -> None:
    _SESSION_REF_FILE.write_text(json.dumps({"session_token": session_token}), encoding="utf-8")
    log.info("Session ref written  session=%s", session_token)


def _read_session_ref() -> str | None:
    if not _SESSION_REF_FILE.exists():
        return None
    try:
        return json.loads(_SESSION_REF_FILE.read_text(encoding="utf-8")).get("session_token")
    except Exception:
        return None


async def _ensure_session() -> str:
    """Return an active session token, creating one via env-based auth if needed."""
    session_token = _read_session_ref()
    if session_token:
        tokens = await _token_store.get(session_token)
        if tokens and not tokens.is_expired():
            log.info("Existing SmartSales session valid  session=%s", session_token)
            return session_token

    # Authenticate fresh using env credentials — no browser required.
    log.info("Authenticating SmartSales via env credentials …")
    creds = authenticate_from_env()
    tokens = StoredTokens(
        access_token=creds.access_token,
        refresh_token=creds.refresh_token,
        expires_at=creds.expires_at,
    )
    session_token = _token_store.generate_session_token()
    await _token_store.save(session_token, tokens)
    _write_session_ref(session_token)
    log.info("SmartSales session created  session=%s", session_token)
    return session_token


# ──────────────────────────────────────────────────────────────────────────────
# Session discovery (used by main.py on startup)
# ──────────────────────────────────────────────────────────────────────────────

@mcp.custom_route("/auth/smartsales/session", methods=["GET"])
async def smartsales_current_session(_request: Request) -> JSONResponse:
    """Return the active session token, auto-creating one if needed.

    main.py calls this on startup to retrieve the session token without
    managing tokens directly.
    """
    try:
        session_token = await _ensure_session()
        creds = await _resolve_session(session_token)
        repo = _get_repo(session_token, creds.access_token)
        await repo.warm_field_cache()
        return JSONResponse({"session_token": session_token})
    except SmartSalesAuthError as exc:
        log.error("SmartSales auth failed: %s", exc)
        return JSONResponse({"error": str(exc)}, status_code=401)


# ──────────────────────────────────────────────────────────────────────────────
# Session resolution (used by every MCP tool call)
# ──────────────────────────────────────────────────────────────────────────────

async def _resolve_session(session_token: str) -> SmartSalesCredentials:
    """Resolve a session UUID to live SmartSales credentials.

    Auto-refreshes via env credentials if the token is expired.
    """
    tokens = await _token_store.get(session_token)
    if tokens is None:
        raise RuntimeError("Session not found — restart the server to re-authenticate.")

    if tokens.is_expired():
        log.info("SmartSales token expired — re-authenticating …")
        try:
            creds = authenticate_from_env()
            new_tokens = StoredTokens(
                access_token=creds.access_token,
                refresh_token=creds.refresh_token,
                expires_at=creds.expires_at,
            )
            await _token_store.save(session_token, new_tokens)
            tokens = new_tokens
        except SmartSalesAuthError as exc:
            await _token_store.delete(session_token)
            raise RuntimeError(f"Token re-authentication failed (session invalidated): {exc}") from exc

    return SmartSalesCredentials(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
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


register_smartsales_tools(mcp, _extract_session_token, _resolve_session)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
````

## File: smartsales/models.py
````python
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _CamelModel(BaseModel):
    """Base model that accepts camelCase JSON fields from the SmartSales API."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# ---------------------------------------------------------------------------
# Embedded / shared sub-objects
# ---------------------------------------------------------------------------

class EmbeddedUser(_CamelModel):
    uid: str | None = None
    username: str | None = None
    firstname: str | None = None
    lastname: str | None = None


class EmbeddedLocation(_CamelModel):
    uid: str | None = None
    code: str | None = None
    external_id: str | None = None
    name: str | None = None


class EmbeddedPerson(_CamelModel):
    uid: str | None = None
    code: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    mobile: str | None = None
    email: str | None = None
    language: str | None = None


class EmbeddedUserGroup(_CamelModel):
    uid: str | None = None
    name: str | None = None
    system: bool | None = None


class EmbeddedAttribute(_CamelModel):
    name: str | None = None
    value: str | None = None


class EmbeddedDocument(_CamelModel):
    uid: str | None = None
    name: str | None = None


class EmbeddedImage(_CamelModel):
    uid: str | None = None
    code: str | None = None
    name: str | None = None
    extension: str | None = None
    tech_server_update_date: str | None = None
    last_modified: str | None = None


class EmbeddedCatalogItemGroup(_CamelModel):
    uid: str | None = None
    code: str | None = None
    title: str | None = None
    parent: EmbeddedCatalogItemGroup | None = None


# ---------------------------------------------------------------------------
# Order line items and modifiers
# ---------------------------------------------------------------------------

class AutoDiscount(_CamelModel):
    code: str | None = None
    discount: float | None = None
    discount_type: str | None = None
    discount_is_percentage: bool | None = None
    discount_is_fixed_discount: bool | None = None
    discount_is_free_quantity: bool | None = None
    discount_is_fixed_price: bool | None = None


class OrderItem(_CamelModel):
    code: str | None = None
    description: str | None = None
    quantity: int | None = None
    price: float | None = None
    sales_unit: int | None = None
    packaging_unit: int | None = None
    measure: float | None = None
    unit_of_measure: str | None = None
    discount: float | None = None
    discount_is_percentage: bool | None = None
    total_price: float | None = None
    final_discount_price: float | None = None
    free: bool | None = None
    auto_discounts: list[AutoDiscount] | None = None
    has_auto_discounts: bool | None = None
    has_overridden_auto_discount: bool | None = None
    comment: str | None = None
    free_reason: str | None = None
    price_manually_set: bool | None = None


class TotalModifier(_CamelModel):
    name: str | None = None
    value: float | None = None
    value_is_percentage: bool | None = None


# ---------------------------------------------------------------------------
# Order configuration DTOs
# ---------------------------------------------------------------------------

class OrderConfigItemField(_CamelModel):
    format: str | None = None
    name: str | None = None
    type: str | None = None
    default_value: str | None = None
    free: bool | None = None


class OrderConfigSectionField(_CamelModel):
    format: str | None = None
    name: str | None = None
    type: str | None = None
    description: str | None = None
    location_attribute_name: str | None = None
    mandatory: bool | None = None
    read_only: bool | None = None
    highlight: bool | None = None


class OrderConfigSection(_CamelModel):
    name: str | None = None
    display_name: str | None = None
    read_only: bool | None = None
    fields: list[OrderConfigSectionField] | None = None


class SmartSalesOrderConfiguration(_CamelModel):
    comment_allowed: bool | None = None
    customer_vat_number_required: bool | None = None
    discount_per_item_allowed: str | None = None
    global_discount_allowed: str | None = None
    has_disclaimer: bool | None = None
    show_signature_input: bool | None = None
    show_vat_per_item: bool | None = None
    signature_required: bool | None = None
    total_modifiers: list[str] | None = None
    items: list[OrderConfigItemField] | None = None
    sections: list[OrderConfigSection] | None = None


# ---------------------------------------------------------------------------
# Approbation status
# ---------------------------------------------------------------------------

class SmartSalesApprobationStatus(_CamelModel):
    uid: str | None = None
    tech_server_creation_date: str | None = None
    tech_server_update_date: str | None = None
    type: str | None = None
    code: str | None = None
    position: int | None = None
    icon_code: str | None = None
    icon_color: str | None = None
    percent_of_success: float | None = None
    terminal: bool | None = None
    secured: bool | None = None
    system: bool | None = None
    deleted: bool | None = None
    title: dict[str, str] | None = None
    description: dict[str, str] | None = None
    mail_subject: dict[str, str] | None = None
    mail_body: dict[str, str] | None = None
    notification_types: list[str] | None = None
    security_permissions: list[EmbeddedUserGroup] | None = None


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------

class SmartSalesOrder(_CamelModel):
    uid: str | None = None
    tech_server_creation_date: str | None = None
    tech_server_update_date: str | None = None
    tech_client_creation_date: str | None = None
    tech_client_update_date: str | None = None
    tech_creation_user_uid: str | None = None
    tech_update_user_uid: str | None = None
    tech_creation_user: EmbeddedUser | None = None
    tech_update_user: EmbeddedUser | None = None
    to_synchronize: bool | None = None
    date: str | None = None
    internal_reference: str | None = None
    external_reference: str | None = None
    version_key: str | None = None
    version_history: bool | None = None
    has_manual_discount: bool | None = None
    has_new_manual_discount: bool | None = None
    comments: str | None = None
    locale: str | None = None
    total: float | None = None
    subtotal: float | None = None
    total_quantity: int | None = None
    type: str | None = None
    approbation_status: str | None = None
    user: EmbeddedUser | None = None
    customer: EmbeddedLocation | None = None
    customer_email: str | None = None
    supplier: EmbeddedLocation | None = None
    supplier_email: str | None = None
    person: EmbeddedPerson | None = None
    commented: bool | None = None
    signature_image: list[str] | None = None
    company_logo_image: list[str] | None = None
    discount_visible: bool | None = None
    form: dict[str, str] | None = None
    custom_fields: dict[str, str] | None = None
    items: list[OrderItem] | None = None
    has_auto_discounts: bool | None = None
    auto_discounts: list[AutoDiscount] | None = None
    total_modifiers: list[TotalModifier] | None = None
    offer: bool | None = None


# ---------------------------------------------------------------------------
# Location
# ---------------------------------------------------------------------------

class SmartSalesLocation(_CamelModel):
    uid: str | None = None
    tech_server_creation_date: str | None = None
    tech_server_update_date: str | None = None
    tech_client_creation_date: str | None = None
    tech_client_update_date: str | None = None
    tech_creation_user_uid: str | None = None
    tech_update_user_uid: str | None = None
    tech_creation_user: EmbeddedUser | None = None
    tech_update_user: EmbeddedUser | None = None
    to_synchronize: bool | None = None
    code: str | None = None
    external_id: str | None = None
    street: str | None = None
    city: str | None = None
    zip: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    name: str | None = None
    vat_number: str | None = None
    deleted: bool | None = None
    suppliers: list[EmbeddedLocation] | None = None
    attributes: list[EmbeddedAttribute] | None = None
    users: list[EmbeddedUser] | None = None
    groups: list[EmbeddedUserGroup] | None = None
    documents: list[EmbeddedDocument] | None = None
    tags: list[str] | None = None
    commented: bool | None = None
    last_visit_date: str | None = None
    last_order_date: str | None = None


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

class SmartSalesCatalogItemGroup(_CamelModel):
    uid: str | None = None
    tech_server_creation_date: str | None = None
    tech_server_update_date: str | None = None
    code: str | None = None
    title: str | None = None
    position: int | None = None
    image_code: str | None = None
    image: EmbeddedImage | None = None
    generate_thumbnail: bool | None = None
    parent: EmbeddedCatalogItemGroup | None = None
    deleted: bool | None = None
    type: str | None = None


class SmartSalesCatalogItem(_CamelModel):
    uid: str | None = None
    tech_server_creation_date: str | None = None
    tech_server_update_date: str | None = None
    code: str | None = None
    external_id: str | None = None
    title: str | None = None
    description: str | None = None
    position: int | None = None
    price: float | None = None
    sales_unit: int | None = None
    packaging_unit: int | None = None
    measure: float | None = None
    unit_of_measure: str | None = None
    availability: str | None = None
    group: EmbeddedCatalogItemGroup | None = None
    groups: list[EmbeddedCatalogItemGroup] | None = None
    tags: list[str] | None = None
    attributes: list[EmbeddedAttribute] | None = None
    documents: list[EmbeddedDocument] | None = None
    image: EmbeddedImage | None = None
    commented: bool | None = None
    deleted: bool | None = None


# ---------------------------------------------------------------------------
# Generic list / field-metadata wrappers
# ---------------------------------------------------------------------------

class SmartSalesListResponse(_CamelModel):
    next_page_token: str | None = None
    result_size_estimate: int | None = None
    entries: list[Any] | None = None


class DisplayField(_CamelModel):
    field_name: str | None = None
    display_name: str | None = None
    type: str | None = None
    constraint_type: str | None = None
    fixed: bool | None = None
    size: str | None = None
    audiences: list[str] | None = None


class QueryField(_CamelModel):
    field_name: str | None = None
    display_name: str | None = None
    type: str | None = None
    hidden: bool | None = None
    allow_expression: bool | None = None
    selector: str | None = None
    audiences: list[str] | None = None


class SortField(_CamelModel):
    key_name: str | None = None
    display_name: str | None = None
    hidden: bool | None = None
    audiences: list[str] | None = None
````

## File: smartsales/repository.py
````python
import json
import logging

import httpx

log = logging.getLogger("smartsales.repository")

_BASE_URL = "https://proxy-smartsales.easi.net/proxy/rest"

_field_cache: dict[str, list] = {}


class SmartSalesRepository:
    def __init__(self, access_token: str):
        self.access_token = access_token

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}"}

    # ------------------------------------------------------------------
    # Locations
    # ------------------------------------------------------------------

    async def get_location(self, uid: str) -> dict:
        """Retrieve a single location by its uid."""
        url = f"{_BASE_URL}/api/v3/location/{uid}"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, headers=self._headers())
            r.raise_for_status()
        return r.json()

    async def list_locations(
        self,
        q: str | None = None,
        s: str | None = None,
        p: str | None = "fullWithColor",
        d: str | None = None,
        nextPageToken: str | None = None,
        skipResultSize: bool | None = False,
    ) -> dict:
        """Query SmartSales locations — raw API params passed straight through.

        q               — JSON filter string, e.g. '{"city":"eq:Knokke"}'
        s               — sort expression, e.g. "name:asc"
        p               — projection: "minimal", "simple", "fullWithColor", "full"
        d               — comma-separated field list, e.g. "code,name,city,country"
        nextPageToken   — pagination token from previous response
        skipResultSize  — skip total count calculation (default True)
        """

        params: dict = {}
        if q is not None:
            params["q"] = q
        if s is not None:
            params["s"] = s
        if p is not None:
            params["p"] = p
        if d is not None:
            params["d"] = d
        if nextPageToken is not None:
            params["nextPageToken"] = nextPageToken
        if skipResultSize is not None:
            params["skipResultSize"] = str(skipResultSize).lower()

        

        log.info("list_locations params=%s", params)

        if _field_cache:
            if q is not None:
                try:
                    q_fields = set(json.loads(q).keys())
                    valid_fields = {f["fieldName"] for f in _field_cache.get("queryable", [])}
                    invalid = q_fields - valid_fields
                    if invalid:
                        return {"error": f"Unknown filter field(s): {sorted(invalid)}. Valid fields: {sorted(valid_fields)}"}
                except (json.JSONDecodeError, KeyError):
                    pass

            if s is not None:
                sort_field = s.split(":")[0]
                valid_sort = {f["keyName"] for f in _field_cache.get("sortable", [])}
                if sort_field not in valid_sort:
                    return {"error": f"Unknown sort field: '{sort_field}'. Valid fields: {sorted(valid_sort)}"}

        url = f"{_BASE_URL}/api/v3/location/list"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, params=params, headers=self._headers())
            r.raise_for_status()

        data = r.json()
        return {
            "locations": data.get("entries") or [],
            "nextPageToken": data.get("nextPageToken"),
            "resultSizeEstimate": data.get("resultSizeEstimate"),
        }


    async def list_displayable_fields(self) -> list:
        """Return the fields that can be displayed in a location list view."""
        if "displayable" not in _field_cache:
            url = f"{_BASE_URL}/api/v3/location/list/displayableFields"
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(url, headers=self._headers())
                r.raise_for_status()
            _field_cache["displayable"] = r.json()
        return _field_cache["displayable"]

    async def list_queryable_fields(self) -> list:
        """Return the fields that can be used as filters in list_locations (q param)."""
        if "queryable" not in _field_cache:
            url = f"{_BASE_URL}/api/v3/location/list/queryableFields"
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(url, headers=self._headers())
                r.raise_for_status()
            _field_cache["queryable"] = r.json()
        return _field_cache["queryable"]

    async def list_sortable_fields(self) -> list:
        """Return the fields that can be used for sorting in list_locations (s param)."""
        if "sortable" not in _field_cache:
            url = f"{_BASE_URL}/api/v3/location/list/sortableFields"
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(url, headers=self._headers())
                r.raise_for_status()
            _field_cache["sortable"] = r.json()
        return _field_cache["sortable"]

    async def warm_field_cache(self) -> None:
        """Pre-fetch all field lists and store in the module-level cache."""
        await self.list_displayable_fields()
        await self.list_queryable_fields()
        await self.list_sortable_fields()
        await self.list_catalog_displayable_fields()
        await self.list_catalog_queryable_fields()
        await self.list_catalog_sortable_fields()
        await self.list_order_displayable_fields()
        await self.list_order_queryable_fields()
        await self.list_order_sortable_fields()
        log.info(
            "Field cache warmed: loc_displayable=%d, loc_queryable=%d, loc_sortable=%d, "
            "cat_displayable=%d, cat_queryable=%d, cat_sortable=%d, "
            "ord_displayable=%d, ord_queryable=%d, ord_sortable=%d",
            len(_field_cache["displayable"]),
            len(_field_cache["queryable"]),
            len(_field_cache["sortable"]),
            len(_field_cache["catalog_displayable"]),
            len(_field_cache["catalog_queryable"]),
            len(_field_cache["catalog_sortable"]),
            len(_field_cache["order_displayable"]),
            len(_field_cache["order_queryable"]),
            len(_field_cache["order_sortable"]),
        )

    # ------------------------------------------------------------------
    # Catalog
    # ------------------------------------------------------------------

    async def get_catalog_item(self, uid: str) -> dict:
        """Retrieve a single catalog item by its uid."""
        url = f"{_BASE_URL}/api/v3/catalog/item/{uid}"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, headers=self._headers())
            r.raise_for_status()
        return r.json()

    async def get_catalog_group(self, uid: str) -> dict:
        """Retrieve a single catalog group by its uid."""
        url = f"{_BASE_URL}/api/v3/catalog/group/{uid}"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, headers=self._headers())
            r.raise_for_status()
        return r.json()

    async def list_catalog_items(
        self,
        q: str | None = None,
        s: str | None = None,
        p: str | None = "simple",
        nextPageToken: str | None = None,
        skipResultSize: bool | None = False,
    ) -> dict:
        """Query SmartSales catalog items — raw API params passed straight through.

        q               — JSON filter string, e.g. '{"name":"contains:widget"}'
        s               — sort expression, e.g. "name:asc"
        p               — projection: "minimal", "simple", "full", "simpleWithDiscount", "fullWithDiscount"
        nextPageToken   — pagination token from previous response
        skipResultSize  — skip total count calculation (default False)
        """
        params: dict = {}
        if q is not None:
            params["q"] = q
        if s is not None:
            params["s"] = s
        if p is not None:
            params["p"] = p
        if nextPageToken is not None:
            params["nextPageToken"] = nextPageToken
        if skipResultSize is not None:
            params["skipResultSize"] = str(skipResultSize).lower()

        log.info("list_catalog_items params=%s", params)

        if _field_cache:
            if q is not None:
                try:
                    q_fields = set(json.loads(q).keys())
                    valid_fields = {f["fieldName"] for f in _field_cache.get("catalog_queryable", [])}
                    invalid = q_fields - valid_fields
                    if invalid:
                        return {"error": f"Unknown filter field(s): {sorted(invalid)}. Valid fields: {sorted(valid_fields)}"}
                except (json.JSONDecodeError, KeyError):
                    pass

            if s is not None:
                sort_field = s.split(":")[0]
                valid_sort = {f["keyName"] for f in _field_cache.get("catalog_sortable", [])}
                if sort_field not in valid_sort:
                    return {"error": f"Unknown sort field: '{sort_field}'. Valid fields: {sorted(valid_sort)}"}

        url = f"{_BASE_URL}/api/v3/catalog/list"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, params=params, headers=self._headers())
            r.raise_for_status()

        data = r.json()
        return {
            "items": data.get("entries") or [],
            "nextPageToken": data.get("nextPageToken"),
            "resultSizeEstimate": data.get("resultSizeEstimate"),
        }

    async def list_catalog_displayable_fields(self) -> list:
        """Return the fields that can be displayed in a catalog item list view."""
        if "catalog_displayable" not in _field_cache:
            url = f"{_BASE_URL}/api/v3/catalog/list/displayableFields"
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(url, headers=self._headers())
                r.raise_for_status()
            _field_cache["catalog_displayable"] = r.json()
        return _field_cache["catalog_displayable"]

    async def list_catalog_queryable_fields(self) -> list:
        """Return the fields that can be used as filters in list_catalog_items (q param)."""
        if "catalog_queryable" not in _field_cache:
            url = f"{_BASE_URL}/api/v3/catalog/list/queryableFields"
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(url, headers=self._headers())
                r.raise_for_status()
            _field_cache["catalog_queryable"] = r.json()
        return _field_cache["catalog_queryable"]

    async def list_catalog_sortable_fields(self) -> list:
        """Return the fields that can be used for sorting in list_catalog_items (s param)."""
        if "catalog_sortable" not in _field_cache:
            url = f"{_BASE_URL}/api/v3/catalog/list/sortableFields"
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(url, headers=self._headers())
                r.raise_for_status()
            _field_cache["catalog_sortable"] = r.json()
        return _field_cache["catalog_sortable"]

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    async def get_order(self, uid: str) -> dict:
        """Retrieve a single order by its uid."""
        url = f"{_BASE_URL}/api/v3/order/{uid}"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, headers=self._headers())
            r.raise_for_status()
        return r.json()

    async def list_orders(
        self,
        q: str | None = None,
        s: str | None = None,
        p: str | None = "simple",
        nextPageToken: str | None = None,
        skipResultSize: bool | None = False,
    ) -> dict:
        """Query SmartSales orders — raw API params passed straight through.

        q               — JSON filter string, e.g. '{"type":"eq:ORDER"}'
        s               — sort expression, e.g. "date:desc"
        p               — projection: "minimal", "simple", "full", "custom"
        nextPageToken   — pagination token from previous response
        skipResultSize  — skip total count calculation (default False)
        """
        params: dict = {}
        if q is not None:
            params["q"] = q
        if s is not None:
            params["s"] = s
        if p is not None:
            params["p"] = p
        if nextPageToken is not None:
            params["nextPageToken"] = nextPageToken
        if skipResultSize is not None:
            params["skipResultSize"] = str(skipResultSize).lower()

        log.info("list_orders params=%s", params)

        if _field_cache:
            if q is not None:
                try:
                    q_fields = set(json.loads(q).keys())
                    valid_fields = {f["fieldName"] for f in _field_cache.get("order_queryable", [])}
                    invalid = q_fields - valid_fields
                    if invalid:
                        return {"error": f"Unknown filter field(s): {sorted(invalid)}. Valid fields: {sorted(valid_fields)}"}
                except (json.JSONDecodeError, KeyError):
                    pass

            if s is not None:
                sort_field = s.split(":")[0]
                valid_sort = {f["keyName"] for f in _field_cache.get("order_sortable", [])}
                if sort_field not in valid_sort:
                    return {"error": f"Unknown sort field: '{sort_field}'. Valid fields: {sorted(valid_sort)}"}

        url = f"{_BASE_URL}/api/v3/order/list"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, params=params, headers=self._headers())
            r.raise_for_status()

        data = r.json()
        return {
            "orders": data.get("entries") or [],
            "nextPageToken": data.get("nextPageToken"),
            "resultSizeEstimate": data.get("resultSizeEstimate"),
        }

    async def get_order_configuration(self) -> dict:
        """Retrieve the global order configuration."""
        url = f"{_BASE_URL}/api/v3/order/configuration"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, headers=self._headers())
            r.raise_for_status()
        return r.json()

    async def list_approbation_statuses(
        self,
        q: str | None = None,
        s: str | None = None,
        p: str | None = "minimal",
        nextPageToken: str | None = None,
    ) -> dict:
        """Query SmartSales order approbation statuses."""
        params: dict = {}
        if q is not None:
            params["q"] = q
        if s is not None:
            params["s"] = s
        if p is not None:
            params["p"] = p
        if nextPageToken is not None:
            params["nextPageToken"] = nextPageToken

        log.info("list_approbation_statuses params=%s", params)

        url = f"{_BASE_URL}/api/v3/order/approbation/status/list"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, params=params, headers=self._headers())
            r.raise_for_status()

        data = r.json()
        return {
            "statuses": data.get("entries") or [],
            "nextPageToken": data.get("nextPageToken"),
            "resultSizeEstimate": data.get("resultSizeEstimate"),
        }

    async def get_approbation_status(self, uid: str) -> dict:
        """Retrieve a single approbation status by its uid."""
        url = f"{_BASE_URL}/api/v3/order/approbation/status/{uid}"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, headers=self._headers())
            r.raise_for_status()
        return r.json()

    async def list_order_displayable_fields(self) -> list:
        """Return the fields that can be displayed in an order list view."""
        if "order_displayable" not in _field_cache:
            url = f"{_BASE_URL}/api/v3/order/list/displayableFields"
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(url, headers=self._headers())
                r.raise_for_status()
            _field_cache["order_displayable"] = r.json()
        return _field_cache["order_displayable"]

    async def list_order_queryable_fields(self) -> list:
        """Return the fields that can be used as filters in list_orders (q param)."""
        if "order_queryable" not in _field_cache:
            url = f"{_BASE_URL}/api/v3/order/list/queryableFields"
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(url, headers=self._headers())
                r.raise_for_status()
            _field_cache["order_queryable"] = r.json()
        return _field_cache["order_queryable"]

    async def list_order_sortable_fields(self) -> list:
        """Return the fields that can be used for sorting in list_orders (s param)."""
        if "order_sortable" not in _field_cache:
            url = f"{_BASE_URL}/api/v3/order/list/sortableFields"
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(url, headers=self._headers())
                r.raise_for_status()
            _field_cache["order_sortable"] = r.json()
        return _field_cache["order_sortable"]
````

## File: smartsales/token_store.py
````python
"""SmartSales token persistence.

Provides:
  StoredTokens          – dataclass holding access/refresh tokens
  SmartSalesTokenStore  – ABC
  JsonFileTokenStore    – dev/local store backed by a JSON file
  build_token_store()   – factory that reads SS_TOKEN_STORE env var
"""

import asyncio
import json
import os
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


# ──────────────────────────────────────────────────────────────────────────────
# StoredTokens
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class StoredTokens:
    """All persisted credentials for a single SmartSales session."""
    access_token: str
    refresh_token: str
    expires_at: float  # Unix epoch seconds

    def is_expired(self, buffer_seconds: int = 300) -> bool:
        """True if the access token expires within *buffer_seconds*."""
        return time.time() >= (self.expires_at - buffer_seconds)


# ──────────────────────────────────────────────────────────────────────────────
# Abstract base
# ──────────────────────────────────────────────────────────────────────────────

class SmartSalesTokenStore(ABC):
    @abstractmethod
    async def get(self, session_token: str) -> Optional[StoredTokens]:
        """Return stored tokens for *session_token*, or None if not found."""

    @abstractmethod
    async def save(self, session_token: str, tokens: StoredTokens) -> None:
        """Persist *tokens* under *session_token*."""

    @abstractmethod
    async def delete(self, session_token: str) -> None:
        """Remove the entry for *session_token* (no-op if not found)."""

    def generate_session_token(self) -> str:
        return str(uuid.uuid4())


# ──────────────────────────────────────────────────────────────────────────────
# JSON file store (dev / local)
# ──────────────────────────────────────────────────────────────────────────────

class JsonFileTokenStore(SmartSalesTokenStore):
    """Stores tokens as JSON in a local file."""

    def __init__(self, path: str = ".smartsales_tokens.json") -> None:
        self._path = Path(path)
        self._lock = asyncio.Lock()

    def _read_raw(self) -> dict:
        if not self._path.exists():
            return {}
        return json.loads(self._path.read_text(encoding="utf-8"))

    def _write_raw(self, data: dict) -> None:
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    async def get(self, session_token: str) -> Optional[StoredTokens]:
        async with self._lock:
            entry = self._read_raw().get(session_token)
        if entry is None:
            return None
        return StoredTokens(**entry)

    async def save(self, session_token: str, tokens: StoredTokens) -> None:
        async with self._lock:
            data = self._read_raw()
            data[session_token] = asdict(tokens)
            self._write_raw(data)

    async def delete(self, session_token: str) -> None:
        async with self._lock:
            data = self._read_raw()
            data.pop(session_token, None)
            self._write_raw(data)


# ──────────────────────────────────────────────────────────────────────────────
# Factory
# ──────────────────────────────────────────────────────────────────────────────

def build_token_store() -> SmartSalesTokenStore:
    """Return the right token store based on the ``SS_TOKEN_STORE`` env var.

    Values:
      ``"file"`` – JsonFileTokenStore (default)
    """
    path = os.environ.get("SS_TOKEN_STORE_FILE", ".smartsales_tokens.json")
    return JsonFileTokenStore(path=path)
````

## File: smartsales/tools.yaml
````yaml
- name: get_location
  description: >
    Retrieve a single SmartSales location by its unique identifier (uid).
    Use this when the user provides a specific location uid.
  method: get_location
  params:
    - name: uid
      type: "str"
      description: The unique identifier (uid) of the location.

# -------------------------------------------------------------------------------

# - name: list_locations
#   description: >
#     Search and list SmartSales locations with optional filters.

#     Use `query` to search by name (contains match).
#     Use `city` to filter by city (contains match).
#     Use `country` to filter by country (exact match, e.g. "Belgium").
#     Use `sort` to order results, e.g. "name:asc" or "code:desc".
#     Use `projection` to control how much data is returned:
#       "minimal" (uid+code only), "simple" (default, main fields),
#       "fullWithColor", "full" (all fields including attributes/documents).
#     `limit` controls the maximum number of results (default 25).

#     Examples:
#     - Locations in Brussels → city="Brussels"
#     - Find location named "Carrefour" → query="Carrefour"
#     - All Belgian locations sorted by name → country="Belgium", sort="name:asc"
#   method: list_locations
#   params:
#     - name: query
#       type: "str | None"
#       description: Name keyword for a contains search (e.g. "Carrefour").
#     - name: city
#       type: "str | None"
#       description: Plain city name for exact match (e.g. "Knokke", "Brussels"). Do NOT include an operator prefix.
#     - name: country
#       type: "str | None"
#       description: Plain country name for exact match (e.g. "Belgium", "United Kingdom"). Do NOT include an operator prefix.
#     - name: sort
#       type: "str | None"
#       description: Sort string in format "field:asc" or "field:desc" (e.g. "name:asc").
#     - name: projection
#       type: "str | None"
#       default: "simple"
#       description: >
#         Detail level — "minimal", "simple" (default), "fullWithColor", or "full".
#     - name: limit
#       type: "int | None"
#       default: 25
#       description: Maximum number of locations to return (default 25).

- name: list_locations
  description: >
    Query SmartSales locations.

    This endpoint supports SmartSales-native query parameters.

    Query parameter behavior:
    - `q`: JSON string containing field filters.
      Each field maps to a SmartSales filter expression.
      Format: {"<fieldName>":"<operator>:<value>"} or {"<fieldName>":"empty"} / {"<fieldName>":"nempty"}.
      Examples:
      - {"name":"eq:name-v1"}
      - {"city":"contains:knokke"}
      - {"country":"eq:Belgium","deleted":"eq:false"}
      - {"vatNumber":"empty"}
      - {"lastVisitDate":"range:20260101,20260331"}

      Supported operators include:
      - eq
      - neq
      - contains
      - ncontains
      - startswith
      - range:start,end
      - gt
      - gte
      - lt
      - lte
      - empty
      - nempty

    - `s`: sorting expression in format "<field>:asc" or "<field>:desc"
      Examples: "name:asc", "code:desc"

    - `p`: projection level
      Allowed values: "minimal", "full"
      - "minimal": only uid and code
      - "full": all fields including attributes

    - `d`: comma-separated list of fields to include in the response
      Example: "code,name,street,zip,city,country,externalId,vatNumber,commented"

    - `nextPageToken`: token returned by a previous query to retrieve the next page

    - `skipResultSize`: if true, skips total result size calculation for performance

    Notes:
    - `q` must be passed as a JSON string
    - when using an HTTP client with query params, do not manually URL-encode `q`;
      let the client encode it
  method: list_locations
  params:
    - name: q
      type: "str | dict | None"
      description: >
        JSON string containing SmartSales field filters.
        Example: {"country":"eq:Belgium","city":"contains:knokke"}

    - name: s
      type: "str | None"
      description: >
        Sorting expression in format "<field>:asc" or "<field>:desc".
        Example: "name:asc"

    - name: p
      type: "str | None"
      default: "fullWithColor"
      description: >
        Projection level. Allowed values: "minimal", "simple", "fullWithColor", "full".

    - name: d
      type: "str | None"
      description: >
        Comma-separated list of fields to include in the response.
        Example: "code,name,street,zip,city,country"

    - name: nextPageToken
      type: "str | None"
      description: Token returned by a previous list query to fetch the next page.

    - name: skipResultSize
      type: "bool | None"
      default: false
      description: >
        If false (default), includes resultSizeEstimate in the response so you know the total count.
        Set to true only to skip the count for performance.

- name: list_displayable_fields
  description: >
    List all fields that can be displayed in a SmartSales location list view.
    Returns field metadata: fieldName, displayName, type, size, audiences.
    Use when the user asks which fields or columns are available to display.
  method: list_displayable_fields
  params: []

- name: list_queryable_fields
  description: >
    List all fields that can be used to filter locations via the q parameter in list_locations.
    Returns field metadata: fieldName, displayName, type, allowExpression, selector.
    Use when the user asks which fields are available to filter on.
  method: list_queryable_fields
  params: []

- name: list_sortable_fields
  description: >
    List all fields that can be used for sorting locations via the s parameter in list_locations.
    Returns field metadata: keyName, displayName, hidden, audiences.
    Use when the user asks which fields are available to sort on.
  method: list_sortable_fields
  params: []

# -------------------------------------------------------------------------------
# Catalog
# -------------------------------------------------------------------------------

- name: get_catalog_item
  description: >
    Retrieve a single SmartSales catalog item by its unique identifier (uid).
    Use this when the user provides a specific catalog item uid.
  method: get_catalog_item
  params:
    - name: uid
      type: "str"
      description: The unique identifier (uid) of the catalog item.

- name: get_catalog_group
  description: >
    Retrieve a single SmartSales catalog group by its unique identifier (uid).
    Use this when the user provides a specific catalog group uid or wants to inspect a group's details.
  method: get_catalog_group
  params:
    - name: uid
      type: "str"
      description: The unique identifier (uid) of the catalog group.

- name: list_catalog_items
  description: >
    Query SmartSales catalog items.

    This endpoint supports SmartSales-native query parameters.

    Query parameter behavior:
    - `q`: JSON string containing field filters.
      Each field maps to a SmartSales filter expression.
      Format: {"<fieldName>":"<operator>:<value>"} or {"<fieldName>":"empty"} / {"<fieldName>":"nempty"}.
      Examples:
      - {"name":"eq:Widget A"}
      - {"name":"contains:widget"}
      - {"deleted":"eq:false"}

      Supported operators include:
      - eq
      - neq
      - contains
      - ncontains
      - startswith
      - range:start,end
      - gt
      - gte
      - lt
      - lte
      - empty
      - nempty

    - `s`: sorting expression in format "<field>:asc" or "<field>:desc"
      Examples: "name:asc", "code:desc"

    - `p`: projection level
      Allowed values: "minimal", "simple", "full", "simpleWithDiscount", "fullWithDiscount"
      - "minimal": only uid and code
      - "simple": main fields
      - "full": all fields
      - "simpleWithDiscount": simple fields + discount pricing
      - "fullWithDiscount": all fields + discount pricing

    - `nextPageToken`: token returned by a previous query to retrieve the next page

    Notes:
    - `q` must be passed as a JSON string
    - when using an HTTP client with query params, do not manually URL-encode `q`;
      let the client encode it
  method: list_catalog_items
  params:
    - name: q
      type: "str | dict | None"
      description: >
        JSON string containing SmartSales field filters.
        Example: {"name":"contains:widget","deleted":"eq:false"}

    - name: s
      type: "str | None"
      description: >
        Sorting expression in format "<field>:asc" or "<field>:desc".
        Example: "name:asc"

    - name: p
      type: "str | None"
      default: "simple"
      description: >
        Projection level. Allowed values: "minimal", "simple", "full", "simpleWithDiscount", "fullWithDiscount".

    - name: nextPageToken
      type: "str | None"
      description: Token returned by a previous list query to fetch the next page.

    - name: skipResultSize
      type: "bool | None"
      default: false
      description: >
        If false (default), includes resultSizeEstimate in the response so you know the total count.
        Set to true only to skip the count for performance.

- name: list_catalog_displayable_fields
  description: >
    List all fields that can be displayed in a SmartSales catalog item list view.
    Returns field metadata: fieldName, displayName, type, size, audiences.
    Use when the user asks which fields or columns are available to display for catalog items.
  method: list_catalog_displayable_fields
  params: []

- name: list_catalog_queryable_fields
  description: >
    List all fields that can be used to filter catalog items via the q parameter in list_catalog_items.
    Returns field metadata: fieldName, displayName, type, allowExpression, selector.
    Use when the user asks which fields are available to filter on for catalog items.
  method: list_catalog_queryable_fields
  params: []

- name: list_catalog_sortable_fields
  description: >
    List all fields that can be used for sorting catalog items via the s parameter in list_catalog_items.
    Returns field metadata: keyName, displayName, hidden, audiences.
    Use when the user asks which fields are available to sort on for catalog items.
  method: list_catalog_sortable_fields
  params: []

# -------------------------------------------------------------------------------
# Orders
# -------------------------------------------------------------------------------

- name: get_order
  description: >
    Retrieve a single SmartSales order by its unique identifier (uid).
    Use this when the user provides a specific order uid.
  method: get_order
  params:
    - name: uid
      type: "str"
      description: The unique identifier (uid) of the order.

- name: list_orders
  description: >
    Query SmartSales orders.

    This endpoint supports SmartSales-native query parameters.

    Query parameter behavior:
    - `q`: JSON string containing field filters.
      Each field maps to a SmartSales filter expression.
      Format: {"<fieldName>":"<operator>:<value>"} or {"<fieldName>":"empty"} / {"<fieldName>":"nempty"}.
      Examples:
      - {"type":"eq:ORDER"}
      - {"approbationStatus":"eq:APPROVED"}
      - {"date":"range:20260101,20260331"}
      - {"total":"gt:1000"}

      Supported operators include:
      - eq
      - neq
      - contains
      - ncontains
      - startswith
      - range:start,end
      - gt
      - gte
      - lt
      - lte
      - empty
      - nempty

    - `s`: sorting expression in format "<field>:asc" or "<field>:desc"
      Examples: "date:desc", "total:asc"

    - `p`: projection level
      Allowed values: "minimal", "simple", "full", "custom"
      - "minimal": only uid
      - "simple": main header fields
      - "full": all fields including line items

    - `nextPageToken`: token returned by a previous query to retrieve the next page

    - `skipResultSize`: if true, skips total result size calculation for performance

    Notes:
    - `q` must be passed as a JSON string
    - when using an HTTP client with query params, do not manually URL-encode `q`;
      let the client encode it

    Important — filtering by customer or supplier:
    - Orders cannot be filtered by customer or supplier name directly.
      The queryable fields only expose uid-based filters for locations.
    - To find orders for a named customer or supplier, always follow this two-step pattern:
      1. Call `list_locations` with a name filter (e.g. {"name":"eq:Customer1"}) to resolve
         the name to a location uid.
      2. Use that uid as the filter value in `list_orders` (e.g. {"customerUid":"eq:<uid>"}).
    - If unsure of the exact field name, call `list_order_queryable_fields` first.
  method: list_orders
  params:
    - name: q
      type: "str | dict | None"
      description: >
        JSON string containing SmartSales field filters.
        Example: {"type":"eq:ORDER","approbationStatus":"eq:APPROVED"}

    - name: s
      type: "str | None"
      description: >
        Sorting expression in format "<field>:asc" or "<field>:desc".
        Example: "date:desc"

    - name: p
      type: "str | None"
      default: "simple"
      description: >
        Projection level. Allowed values: "minimal", "simple", "full", "custom".

    - name: nextPageToken
      type: "str | None"
      description: Token returned by a previous list query to fetch the next page.

    - name: skipResultSize
      type: "bool | None"
      default: false
      description: >
        If false (default), includes resultSizeEstimate in the response so you know the total count.
        Set to true only to skip the count for performance.

- name: get_order_configuration
  description: >
    Retrieve the SmartSales order configuration.
    Returns global settings: discount rules, signature requirements, VAT display,
    configurable form sections and their fields.
    Use when the user asks how orders are configured or what form fields/sections exist.
  method: get_order_configuration
  params: []

- name: list_approbation_statuses
  description: >
    Query SmartSales order approbation statuses (approval workflow statuses).
    Returns defined statuses with their codes, icons, colors, and workflow properties
    (terminal, secured, percent of success, notification types).
    Use when the user asks about available approval or approbation statuses for orders or offers.
  method: list_approbation_statuses
  params:
    - name: q
      type: "str | dict | None"
      description: >
        JSON string containing field filters.
        Example: {"type":"eq:ORDER","deleted":"eq:false"}

    - name: s
      type: "str | None"
      description: Sorting expression in format "<field>:asc" or "<field>:desc".

    - name: p
      type: "str | None"
      default: "minimal"
      description: >
        Projection level. Allowed values: "minimal", "simple", "full".

    - name: nextPageToken
      type: "str | None"
      description: Token returned by a previous list query to fetch the next page.

- name: get_approbation_status
  description: >
    Retrieve a single SmartSales order approbation status by its unique identifier (uid).
    Returns full details including title, description, mail templates, and notification settings.
  method: get_approbation_status
  params:
    - name: uid
      type: "str"
      description: The unique identifier (uid) of the approbation status.

- name: list_order_displayable_fields
  description: >
    List all fields that can be displayed in a SmartSales order list view.
    Returns field metadata: fieldName, displayName, type, size, audiences.
    Use when the user asks which fields or columns are available to display for orders.
  method: list_order_displayable_fields
  params: []

- name: list_order_queryable_fields
  description: >
    List all fields that can be used to filter orders via the q parameter in list_orders.
    Returns field metadata: fieldName, displayName, type, allowExpression, selector.
    Use when the user asks which fields are available to filter on for orders.
  method: list_order_queryable_fields
  params: []

- name: list_order_sortable_fields
  description: >
    List all fields that can be used for sorting orders via the s parameter in list_orders.
    Returns field metadata: keyName, displayName, hidden, audiences.
    Use when the user asks which fields are available to sort on for orders.
  method: list_order_sortable_fields
  params: []
````

## File: .gitignore
````
.env
*.cfg
*.bin
*.pyc
*.pem
*.crt
*.key
*.json
````

## File: main.py
````python
import os
import sys
import socket
import time
import logging
import configparser
import subprocess
import webbrowser
from urllib.parse import urlparse

import httpx
import msal

from agent_framework import MCPStreamableHTTPTool
from agent_framework.devui import serve
from agents.graph_agent import create_graph_agent
from agents.orchestrator_agent import create_orchestrator_agent
from agents.salesforce_agent import create_salesforce_agent
from agents.smartsales_agent import create_smartsales_agent

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("mcp").setLevel(logging.WARNING)

_TOKEN_CACHE_FILE = ".token_cache.bin"


# https://bonanipaulchaudhury.medium.com/integrating-oauth-2-0-delegation-via-azure-api-management-with-mcp-and-prm-why-it-matters-f6c993ef591f


def _build_msal_app(
    client_id: str, tenant_id: str
) -> tuple[msal.PublicClientApplication, msal.SerializableTokenCache]:
    cache = msal.SerializableTokenCache()
    if os.path.exists(_TOKEN_CACHE_FILE):
        with open(_TOKEN_CACHE_FILE, "r") as f:
            cache.deserialize(f.read())

    app = msal.PublicClientApplication(
        client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        token_cache=cache,
    )
    return app, cache


def _persist_cache(cache: msal.SerializableTokenCache) -> None:
    if cache.has_state_changed:
        with open(_TOKEN_CACHE_FILE, "w") as f:
            f.write(cache.serialize())


def authenticate(client_id: str, tenant_id: str, scopes: list[str]) -> str:
    """Acquire a delegated access token via MSAL.

    Tries the token cache first; falls back to the device code flow.
    In production (or with VS Code / Claude Desktop) the MCP client reads
    /.well-known/oauth-protected-resource and drives an auth-code + PKCE
    flow automatically — no manual token acquisition is needed.
    """
    app, cache = _build_msal_app(client_id, tenant_id)

    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(scopes, account=accounts[0])
        if result and "access_token" in result:
            _persist_cache(cache)
            return result["access_token"]

    flow = app.initiate_device_flow(scopes=scopes)

    print(f"\nAuthenticate at: {flow['verification_uri']}")
    print(f"Enter code:      {flow['user_code']}\n")

    result = app.acquire_token_by_device_flow(flow)

    if "access_token" not in result:
        raise RuntimeError(
            f"Authentication failed: {result.get('error_description', 'Unknown error')}"
        )

    _persist_cache(cache)
    return result["access_token"]


def _is_local_url(url: str) -> bool:
    # gewoon ofda local of cloud
    host = urlparse(url).hostname or ""
    return host in ("localhost", "127.0.0.1", "::1")


def _wait_for_port(host: str, port: int, timeout: float = 15.0) -> None:
    # idk waarom dis shit echt nodig is
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return
        except OSError:
            time.sleep(0.25)
    raise TimeoutError(
        f"MCP server at {host}:{port} did not become ready within {timeout}s"
    )


def _start_graph_mcp_server(env: dict, mcp_url: str) -> subprocess.Popen:
    # graph/mcp_server.py als achtergrond http server launchen

    proc = subprocess.Popen(
        [sys.executable, "-m", "graph.mcp_server"],
        env=env,
        # fouten / output naar zelfde terminal sturen
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    parsed = urlparse(mcp_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 8000
    print(f"Waiting for MCP server on {host}:{port} …")
    _wait_for_port(host, port)
    print("MCP server ready.")
    return proc


def _start_salesforce_mcp_server(env: dict, mcp_url: str) -> subprocess.Popen:
    proc = subprocess.Popen(
        [sys.executable, "-m", "salesforce.mcp_server"],
        env=env,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    parsed = urlparse(mcp_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 8001
    print(f"Waiting for Salesforce MCP server on {host}:{port} …")
    _wait_for_port(host, port)
    print("Salesforce MCP server ready.")
    return proc


def _start_smartsales_mcp_server(env: dict, mcp_url: str) -> subprocess.Popen:
    proc = subprocess.Popen(
        [sys.executable, "-m", "smartsales.mcp_server"],
        env=env,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    parsed = urlparse(mcp_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 8002
    print(f"Waiting for SmartSales MCP server on {host}:{port} …")
    _wait_for_port(host, port)
    print("SmartSales MCP server ready.")
    return proc


def _resolve_ss_session(ss_mcp_url: str) -> str:
    """Return a valid SmartSales session token.

    Calls GET /auth/smartsales/session on the running MCP server.
    The MCP server auto-authenticates using env credentials — no browser needed.
    """
    parsed = urlparse(ss_mcp_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    session_url = f"{base}/auth/smartsales/session"

    try:
        resp = httpx.get(session_url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            print(f"SmartSales: session ready.")
            return data["session_token"]
        raise RuntimeError(f"SmartSales session endpoint returned {resp.status_code}: {resp.text}")
    except httpx.RequestError as exc:
        raise RuntimeError(f"Cannot reach SmartSales MCP server at {base}: {exc}") from exc


def _resolve_sf_session(sf_mcp_url: str) -> str:
    """Return a valid Salesforce session token, triggering browser auth if needed.

    1. Calls GET /auth/salesforce/session on the running MCP server.
    2. If a session already exists (200) → returns it immediately (no browser).
    3. If no session (404) → opens the browser to /auth/salesforce/login,
       then polls the same endpoint every 2 s until the OAuth callback fires
       and the MCP server writes a new session ref (up to 120 s).

    main.py never reads or writes SF tokens directly — everything goes through
    the MCP server's HTTP API.
    """
    parsed = urlparse(sf_mcp_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    session_url = f"{base}/auth/salesforce/session" # session_url = http://localhost:8001/auth/salesforce/session
    login_url = f"{base}/auth/salesforce/login" # login_url = http://localhost:8001/auth/salesforce/login

    print("session url: ", session_url)
    print("login url :", login_url)


    # ── 1. Check for an existing session ─────────────────────────────────────
    try:
        resp = httpx.get(session_url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            logging.getLogger(__name__).info("Salesforce session restored  user=%s", data.get("username", "?"))
            print(f"Salesforce: session restored ({data.get('username', '?')}).")
            return data["session_token"]

    except httpx.RequestError as exc:
        raise RuntimeError(
            f"Cannot reach Salesforce MCP server at {base}: {exc}"
        ) from exc

    # ── 2. No session — authenticate via browser ──────────────────────────────
    print(f"\nNo active Salesforce session found.")
    print(f"Opening browser for Salesforce login: {login_url}")
    webbrowser.open(login_url)
    print("Waiting for authentication (timeout: 120 s) …\n")

    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        time.sleep(2)
        try:
            resp = httpx.get(session_url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                logging.getLogger(__name__).info("Salesforce authenticated  user=%s", data.get("username", "?"))
                print(f"Salesforce: authenticated as {data.get('username', '?')}.")
                return data["session_token"]
        except httpx.RequestError:
            pass  # server temporarily unreachable — keep polling

    raise TimeoutError(
        "Salesforce authentication timed out after 120 s. "
        f"Re-open {login_url} manually and restart."
    )


def main() -> None:
    print("Starting application...")

    config = configparser.ConfigParser()
    config.read(["config.cfg"])
    azure_settings = config["azure"]
    sf_settings = config["salesforce"]
    ss_settings = config["smartsales"] if config.has_section("smartsales") else {}

    # ── Microsoft Graph ────────────────────────────────────────────────
    client_id = azure_settings["clientId"]
    tenant_id = azure_settings["tenantId"]
    scopes = azure_settings["graphUserScopes"].split(" ")
    mcp_url = azure_settings.get("mcpServerUrl", "http://localhost:8000/mcp")

    token = authenticate(client_id, tenant_id, scopes)
    print("Authenticated with Microsoft.")

    server_env = os.environ.copy()
    parsed = urlparse(mcp_url)
    resource_base = f"{parsed.scheme}://{parsed.netloc}"
    server_env["MCP_RESOURCE_URI"] = resource_base

    graph_proc = None
    if _is_local_url(mcp_url):
        graph_proc = _start_graph_mcp_server(server_env, mcp_url)

    graph_http = httpx.AsyncClient(
        headers={"Authorization": f"Bearer {token}"},
    )
    graph_mcp = MCPStreamableHTTPTool(
        name="graph",
        url=mcp_url,
        http_client=graph_http,
    )

    # ── Salesforce ─────────────────────────────────────────────────────
    sf_mcp_url = sf_settings.get("mcpServerUrl", "http://localhost:8001/mcp")
    sf_server_env = os.environ.copy()
    sf_parsed = urlparse(sf_mcp_url)

    #fok is dit? 
    sf_resource_base = f"{sf_parsed.scheme}://{sf_parsed.netloc}"
    sf_server_env["MCP_RESOURCE_URI"] = sf_resource_base


    if _is_local_url(sf_mcp_url):
        sf_proc = _start_salesforce_mcp_server(sf_server_env, sf_mcp_url)

    # Resolve session from the MCP server (restores existing or triggers browser auth).
    sf_session_token = _resolve_sf_session(sf_mcp_url)
    sf_proc = None

    sf_http = httpx.AsyncClient(
        headers={"Authorization": f"Bearer {sf_session_token}"},
    )
    sf_mcp = MCPStreamableHTTPTool(
        name="salesforce",
        url=sf_mcp_url,
        http_client=sf_http,
    )

    # ── SmartSales ──────────────────────────────────────────────────────
    ss_mcp_url = ss_settings.get("mcpServerUrl", "http://localhost:8002/mcp")
    ss_server_env = os.environ.copy()
    ss_parsed = urlparse(ss_mcp_url)
    ss_resource_base = f"{ss_parsed.scheme}://{ss_parsed.netloc}"
    ss_server_env["MCP_RESOURCE_URI"] = ss_resource_base

    ss_proc = None
    if _is_local_url(ss_mcp_url):
        ss_proc = _start_smartsales_mcp_server(ss_server_env, ss_mcp_url)

    ss_session_token = _resolve_ss_session(ss_mcp_url)

    ss_http = httpx.AsyncClient(
        headers={"Authorization": f"Bearer {ss_session_token}"},
    )
    ss_mcp = MCPStreamableHTTPTool(
        name="smartsales",
        url=ss_mcp_url,
        http_client=ss_http,
    )

    # ── Serve agents ───────────────────────────────────────────────────
    try:
        graph_agent = create_graph_agent(graph_mcp=graph_mcp)
        sf_agent = create_salesforce_agent(salesforce_mcp=sf_mcp)
        ss_agent = create_smartsales_agent(smartsales_mcp=ss_mcp)
        orchestrator = create_orchestrator_agent(smartsales_agent=ss_agent, graph_agent=graph_agent, salesforce_agent=sf_agent)
        serve(entities=[orchestrator, ss_agent, graph_agent, sf_agent], port=8080, auto_open=True)
    finally:
        if ss_proc is not None:
            ss_proc.terminate()
            ss_proc.wait()


if __name__ == "__main__":
    main()
````

## File: README.md
````markdown
# graphxmaf

# OAuth 2.0 Delegation via Azure API Management with MCP and PRM

## Overview

This document describes the authentication architecture used in this project, based on the pattern described in ["Integrating OAuth 2.0 Delegation via Azure API Management with MCP and PRM"](https://bonanipaulchaudhury.medium.com/integrating-oauth-2-0-delegation-via-azure-api-management-with-mcp-and-prm-why-it-matters-f6c993ef591f).

The goal is to replace a hardcoded, process-scoped token (passed via environment variable to a stdio subprocess) with a proper **OAuth 2.0 delegated flow** where each HTTP request carries its own bearer token, validated at the API gateway level.

---

## Why This Change?

### The Old Approach (v1)

```
main.py
  ├── Triggers DeviceCodeCredential (azure-identity)
  ├── User visits a URL, enters a code in a browser
  ├── Token stored in GRAPH_ACCESS_TOKEN env var
  └── Spawns mcp_api_tool.py subprocess (stdio)
       └── Reads token from env var → calls Microsoft Graph
```

**Problems:**
- The token is process-scoped: every request uses the same token
- The MCP server is a subprocess — not accessible over a network
- No standard way for external clients (VS Code, Claude Desktop) to discover auth requirements
- Token is injected out-of-band (env var), not via HTTP headers
- No APIM gateway layer for policy enforcement, rate limiting, or logging

### The New Approach (v2)

```
MCP Client (main.py / VS Code / Claude Desktop)
  ├── GET /.well-known/oauth-protected-resource  ← PRM discovery
  ├── Redirected to Azure AD for login (MSAL / auth code + PKCE)
  ├── Receives access token (JWT) from Azure AD
  └── POST /mcp  (Authorization: Bearer <token>)
        │
        ▼
  Azure API Management (APIM)
  ├── validate-azure-ad-token policy checks the JWT
  ├── Rejects invalid/missing tokens with 401
  └── Forwards valid requests to the MCP server backend
        │
        ▼
  mcp_api_tool.py  (streamable-http MCP server)
  ├── Extracts Bearer token from Authorization header per-request
  ├── Creates a GraphServiceClient scoped to that token
  └── Calls Microsoft Graph on behalf of the authenticated user
        │
        ▼
  Microsoft Graph API
```

---

## Key Components

### 1. Protected Resource Metadata (PRM) — RFC 9728

The MCP server exposes a **public** endpoint:

```
GET /.well-known/oauth-protected-resource
```

Response:
```json
{
  "resource": "https://<apim-instance>.azure-api.net/<mcp-path>",
  "authorization_servers": [
    "https://login.microsoftonline.com/<tenant-id>/v2.0"
  ],
  "bearer_methods_supported": ["header"],
  "scopes_supported": ["User.Read", "Mail.Read"]
}
```

This tells any MCP-aware client:
- Which Azure AD tenant to authenticate with
- Which scopes to request
- That tokens must be passed as `Authorization: Bearer` headers

MCP clients (VS Code, Claude Desktop, custom agents) read this endpoint and automatically initiate the OAuth flow. No hardcoded auth config is needed on the client side.

### 2. OAuth 2.0 Authorization Code + PKCE Flow

Once the client reads the PRM, it performs the standard OAuth 2.0 authorization code flow with PKCE:

```
Client                    Azure AD                  MCP Server (via APIM)
  │                          │                              │
  │── GET /authorize ────────▶│                              │
  │   (response_type=code,    │                              │
  │    code_challenge=...)    │                              │
  │                          │                              │
  │◀─ Redirect (code) ────────│                              │
  │                          │                              │
  │── POST /token ───────────▶│                              │
  │   (code, code_verifier)   │                              │
  │                          │                              │
  │◀─ access_token (JWT) ─────│                              │
  │                          │                              │
  │── POST /mcp ─────────────────────────────────────────────▶│
  │   Authorization: Bearer <access_token>                   │
  │                          │                              │
  │◀─ MCP response ───────────────────────────────────────────│
```

For CLI/agent use (this project's `main.py`), a **device code flow** or **MSAL interactive** is used to acquire the token, since there is no browser callback URI.

### 3. Azure API Management — JWT Validation

APIM sits in front of the MCP server and enforces the following inbound policy:

```xml
<policies>
  <inbound>
    <base />
    <!-- Validate the Azure AD JWT token -->
    <validate-azure-ad-token
        tenant-id="<your-tenant-id>"
        header-name="Authorization"
        failed-validation-httpcode="401"
        failed-validation-error-message="Unauthorized. Access token is missing or invalid.">
      <client-application-ids>
        <application-id><your-client-app-id></application-id>
      </client-application-ids>
    </validate-azure-ad-token>
    <!-- Forward the Authorization header to the backend MCP server -->
    <set-header name="Authorization" exists-action="override">
      <value>@(context.Request.Headers.GetValueOrDefault("Authorization"))</value>
    </set-header>
  </inbound>
  <backend>
    <base />
  </backend>
  <outbound>
    <base />
  </outbound>
</policies>
```

APIM rejects any request without a valid Azure AD JWT. Valid requests are forwarded to the MCP server with the `Authorization` header intact.

### 4. MCP Server — Per-Request Token Extraction

The MCP server (`mcp_api_tool.py`) now:

- Runs as a **Streamable HTTP** server (not a stdio subprocess)
- Reads the `Authorization: Bearer <token>` header from each incoming MCP request via the FastMCP `Context` object
- Creates a `GraphServiceClient` scoped to that token **for each request**
- This enables multi-user scenarios: different users can connect simultaneously with different tokens

```python
@mcp.tool()
async def whoami(ctx: Context) -> str:
    token = _extract_token(ctx)        # reads from ctx.request_context.request.headers
    g = _make_graph_client(token)      # creates per-request GraphServiceClient
    user = await g.get_user()
    return f"Name: {user.display_name}"
```

---

## Step-by-Step Authentication Flow

```
Step 1: Client discovers auth requirements
─────────────────────────────────────────
Client → GET /.well-known/oauth-protected-resource
Server → { "authorization_servers": [...], "scopes_supported": [...] }

Step 2: Client acquires a token from Azure AD
──────────────────────────────────────────────
Client → Azure AD: Authorization Code + PKCE (or Device Code for CLI)
Azure AD → Client: access_token (JWT signed by Azure AD)

Step 3: Client calls the MCP server via APIM
─────────────────────────────────────────────
Client → APIM → POST /mcp
         Headers: { Authorization: "Bearer eyJ0eXAi..." }
         Body: { "method": "tools/call", "params": { "name": "whoami" } }

Step 4: APIM validates the JWT
──────────────────────────────
APIM checks:
  - Token is signed by Azure AD (checks JWKS endpoint)
  - Token audience matches the registered app
  - Token is not expired
  - Token issuer matches the configured tenant

If invalid → 401 Unauthorized (never reaches the MCP server)
If valid   → request forwarded to MCP server backend

Step 5: MCP server extracts the token and calls Graph
──────────────────────────────────────────────────────
MCP server reads Authorization header from the HTTP request context
Creates a GraphServiceClient with the bearer token
Calls Microsoft Graph on behalf of the authenticated user
Returns result to the MCP client
```

---

## Azure AD App Registration Requirements

For this to work, you need an Azure AD app registration configured as follows:

| Setting | Value |
|---|---|
| App type | Public client (for device code / interactive) |
| Redirect URI | `http://localhost` (for local dev) or your APIM callback URL |
| API permissions | `User.Read`, `Mail.Read` (delegated) |
| Token type | Access tokens (not ID tokens) |
| Supported account types | Accounts in this organizational directory only |

The `clientId` and `tenantId` in `config.cfg` must match this app registration.

---

## Local Development (Without APIM)

During local development, the MCP server can run without APIM. In this case:

1. Start the MCP server: `python mcp_api_tool.py`  (listens on `http://localhost:8000/mcp`)
2. Start the agent:  `python main.py`  (authenticates with MSAL, connects to the local MCP server)

The token is still validated indirectly — if the token is invalid, Microsoft Graph will return 401 when the tool tries to call it.

For production, deploy the MCP server behind APIM and update `mcpServerUrl` in `config.cfg` to the APIM endpoint.

---

## Configuration

`config.cfg`:
```ini
[azure]
clientId     = <your-azure-ad-app-client-id>
tenantId     = <your-azure-ad-tenant-id>
graphUserScopes = User.Read Mail.Read
mcpServerUrl = http://localhost:8000/mcp    ; or your APIM URL in production
```

Environment variables (optional overrides):
```bash
MCP_RESOURCE_URI=https://<apim>.azure-api.net/<path>  # used in PRM response
```

---

## Security Properties

| Property | Old (v1) | New (v2) |
|---|---|---|
| Token scope | Process-wide (shared by all requests) | Per-request (each HTTP call carries its own token) |
| Transport | stdio (local subprocess only) | Streamable HTTP (network-accessible) |
| Auth enforcement | None (token assumed valid) | APIM `validate-azure-ad-token` policy |
| Multi-user support | No | Yes |
| Auth discovery | Manual configuration | Automatic via PRM (`/.well-known/oauth-protected-resource`) |
| Token storage | Environment variable | MSAL token cache (`~/.token_cache.bin`) |
| Standard compliance | Proprietary | OAuth 2.1 + RFC 9728 (PRM) |

---

## References

- [OAuth 2.0 Protected Resource Metadata — RFC 9728](https://datatracker.ietf.org/doc/rfc9728/)
- [MCP Authorization Specification](https://modelcontextprotocol.io/specification/draft/basic/authorization)
- [Secure access to MCP servers in Azure API Management](https://learn.microsoft.com/en-us/azure/api-management/secure-mcp-servers)
- [validate-azure-ad-token APIM policy](https://learn.microsoft.com/en-us/azure/api-management/validate-azure-ad-token-policy)
- [MSAL for Python](https://learn.microsoft.com/en-us/entra/msal/python/)
````

## File: requirements.txt
````
# Microsoft Graph & Auth
azure-identity>=1.25.2
azure-keyvault-secrets>=4.8.0
msgraph-sdk>=1.54.0
msal>=1.34.0

# MCP server
mcp>=1.26.0
starlette>=0.52.1
pyyaml>=6.0

# HTTP
httpx>=0.28.1

# JWT (Salesforce bearer flow)
PyJWT[cryptography]>=2.8.0

# Document parsing
python-docx>=1.1.0

# OpenAI (used via agent_framework)
openai>=2.21.0

# Microsoft Agent Framework
# Install from: https://aka.ms/agent-framework
# pip install agent-framework --extra-index-url <private-feed-url>
agent-framework>=1.0.0b251120
````
