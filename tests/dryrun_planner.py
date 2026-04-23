"""tests/dryrun_planner.py — test de nieuwe PLAN_SYSTEM_PROMPT zonder echte agents.

Roept alleen de PlannerAgent aan (Azure OpenAI) en print de gegenereerde plannen.

Run vanuit de project root:
    python tests/dryrun_planner.py
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from agent_framework import Agent
from agent_framework.azure import AzureOpenAIChatClient
from agents.planning_orchestrator import PLAN_SYSTEM_PROMPT

client = AzureOpenAIChatClient(
    deployment_name=os.environ["deployment"],
    endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version="2024-12-01-preview",
)
planner = Agent(
    client=client,
    name="PlannerAgent",
    description="test",
    instructions=PLAN_SYSTEM_PROMPT,
    tools=[],
)

AVAILABLE = (
    "graph (Microsoft 365: emails, calendar, OneDrive, contacts), "
    "salesforce (CRM: accounts, contacts, leads, opportunities), "
    "smartsales (locations, catalog items)"
)

# (query, verwacht_aantal_stappen, opmerking)
TEST_CASES = [
    (
        "Show me the 3 largest open Salesforce opportunities and the billing country of each related account.",
        1,
        "vroeger 2 Salesforce stappen -> nu 1 (billing country meegevraagd)",
    ),
    (
        "List Salesforce opportunities that are closing this month and check if I have any calendar events related to those account names.",
        2,
        "cross-system: SF->Graph, step 2 graceful bij lege parent",
    ),
    (
        "List all SmartSales locations.",
        1,
        "single-agent simpel -> altijd 1 stap",
    ),
    (
        "Give me an overview of my upcoming meetings and the Salesforce accounts related to the attendees.",
        2,
        "cross-system parallel: graph + salesforce",
    ),
    (
        "Take the sender of my most recent email, look them up in Salesforce, and find their nearest SmartSales location.",
        3,
        "sequentieel 3 stappen: graph->sf->ss",
    ),
]


async def run():
    sep = "-" * 65
    print(f"\n{sep}")
    print("  Planner dry-run -- nieuwe PLAN_SYSTEM_PROMPT")
    print(f"{sep}\n")

    passed = 0
    for query, expected_steps, note in TEST_CASES:
        prompt = f"Available agents: {AVAILABLE}\n\nUser query: {query}"
        resp = await planner.run(prompt)
        raw = resp.text.strip()

        # strip markdown fences indien aanwezig
        if raw.startswith("```"):
            lines = raw.split("\n")[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            raw = "\n".join(lines)

        try:
            plan = json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"PARSE ERROR: {e}\nRaw: {raw[:300]}\n")
            continue

        steps = plan.get("steps", [])
        agents_used = [s["agent"] for s in steps]
        ok = len(steps) == expected_steps
        passed += ok

        status = "OK" if ok else f"FAIL (verwacht {expected_steps})"
        print(f"[{status}] steps={len(steps)} agents={agents_used}")
        print(f"  query : {query[:70]}")
        print(f"  note  : {note}")
        for s in steps:
            print(f"  [{s['id']}] {s['agent']} dep={s['depends_on']}: {s['task'][:85]}")
        print()

    print(f"{sep}")
    print(f"  {passed}/{len(TEST_CASES)} queries correct gepland")
    print(f"{sep}\n")


if __name__ == "__main__":
    asyncio.run(run())
