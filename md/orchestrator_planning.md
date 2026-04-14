# Orchestrator Planning Architecture

## Overview

De orchestrator werkt in twee fasen: **Plan** en **Execute**. De LLM analyseert eerst de user query en produceert een gestructureerd plan. Daarna voert diezelfde LLM het plan uit met de beschikbare tools. Dit geeft voorspelbaarheid en debugbaarheid zonder dat we een custom execution engine hoeven te bouwen.

## Flow

```
User Query
    │
    ▼
┌──────────────┐
│  PLAN PHASE  │  LLM call #1 — geen tools, alleen analyse
│              │  Input:  user query + agent capabilities
│              │  Output: plan JSON
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   VALIDATE   │  Code — check schema, log plan, optionele guardrails
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ EXECUTE PHASE│  LLM call #2 — met tools
│              │  Input:  user query + plan + tools
│              │  Output: tool calls + final antwoord
└──────┬───────┘
       │
       ▼
   Response
```

## Plan Schema

```json
{
  "query": "get me Arne's latest emails and his open Salesforce opportunities",
  "reasoning": "User wants data from two sources: emails from Graph and opportunities from Salesforce. No dependencies between the two — can be fetched independently.",
  "steps": [
    {
      "id": 1,
      "agent": "graph",
      "task": "Find recent emails from or to Arne",
      "depends_on": []
    },
    {
      "id": 2,
      "agent": "salesforce",
      "task": "Find open opportunities linked to contact Arne",
      "depends_on": []
    }
  ],
  "synthesis": "Combine email overview with opportunity overview into a single summary for the user"
}
```

### Velden

| Veld | Type | Beschrijving |
|------|------|-------------|
| `query` | string | Originele user query, ongewijzigd |
| `reasoning` | string | Korte uitleg van de LLM over waarom dit plan gekozen is |
| `steps` | array | Geordende lijst van taken per agent |
| `steps[].id` | int | Unieke step identifier |
| `steps[].agent` | string | Welke agent: `graph`, `salesforce`, `smartsales` |
| `steps[].task` | string | Beschrijving van wat de agent moet doen, in natuurlijke taal |
| `steps[].depends_on` | int[] | IDs van steps die eerst klaar moeten zijn (lege array = geen dependencies) |
| `synthesis` | string | Instructie voor hoe de resultaten gecombineerd moeten worden |

## Voorbeeldplannen

### Eenvoudig — single agent

```json
{
  "query": "what meetings do I have tomorrow?",
  "reasoning": "Single-source query, only Graph calendar data needed.",
  "steps": [
    {
      "id": 1,
      "agent": "graph",
      "task": "Get calendar events for tomorrow",
      "depends_on": []
    }
  ],
  "synthesis": "Present the calendar events in chronological order"
}
```

### Multi-agent — geen dependencies

```json
{
  "query": "give me an overview of Contoso: emails, open deals, and support cases",
  "reasoning": "User wants a company overview from three sources. No dependencies — all can be queried with 'Contoso' as search term.",
  "steps": [
    {
      "id": 1,
      "agent": "graph",
      "task": "Find recent emails mentioning Contoso",
      "depends_on": []
    },
    {
      "id": 2,
      "agent": "salesforce",
      "task": "Find open opportunities for account Contoso",
      "depends_on": []
    },
    {
      "id": 3,
      "agent": "salesforce",
      "task": "Find open support cases for account Contoso",
      "depends_on": []
    }
  ],
  "synthesis": "Group results by category (emails, deals, cases) and present as a company overview"
}
```

### Multi-agent — met dependencies

```json
{
  "query": "find the contact info of everyone who emailed me today and check if they're in Salesforce",
  "reasoning": "Two-phase query: first get today's email senders from Graph, then look them up in Salesforce. Step 2 depends on step 1.",
  "steps": [
    {
      "id": 1,
      "agent": "graph",
      "task": "Get all emails received today, extract sender names and email addresses",
      "depends_on": []
    },
    {
      "id": 2,
      "agent": "salesforce",
      "task": "For each sender from step 1, search for matching contacts",
      "depends_on": [1]
    }
  ],
  "synthesis": "Present a table: sender name, email, and whether they exist as a Salesforce contact (with link if found)"
}
```

## System Prompts

### Plan Phase

```
You are a query planner for a multi-agent system. You have access to three agents:

- **graph**: Microsoft 365 data — emails, calendar, contacts, files, OneDrive
- **salesforce**: Salesforce CRM — accounts, contacts, leads, opportunities, cases
- **smartsales**: Internal sales analytics and reporting

Your job is to analyze the user's query and produce an execution plan as JSON.

Rules:
1. Break the query into the minimum number of steps needed
2. Each step targets exactly one agent
3. Use depends_on when a step needs output from a previous step
4. Keep task descriptions specific — include search terms, filters, time ranges from the query
5. If the query only needs one agent, that's fine — still produce a plan with one step
6. If the query is ambiguous, make reasonable assumptions and note them in reasoning
7. Respond ONLY with valid JSON matching the plan schema — no markdown, no preamble
```

### Execute Phase

```
You are executing a query plan. The user asked:

"{original_query}"

The plan is:
{plan_json}

Execute each step using the available tools. Follow the plan's step order and
respect dependencies — do not start a step until its dependencies are complete.
After all steps, synthesize the results as described in the plan's synthesis field.

Be concise in your final answer. Present data clearly — use tables for structured
data, bullet points for lists.
```

## Implementatie

### Planning call

```python
async def create_plan(user_query: str, llm_client) -> dict:
    response = await llm_client.chat(
        messages=[
            {"role": "system", "content": PLAN_SYSTEM_PROMPT},
            {"role": "user", "content": user_query}
        ],
        response_format={"type": "json_object"}
    )
    
    plan = json.loads(response.content)
    
    # Validate
    assert "steps" in plan
    assert all(s["agent"] in KNOWN_AGENTS for s in plan["steps"])
    
    # Log
    logger.info(f"Plan created: {json.dumps(plan, indent=2)}")
    
    return plan
```

### Execution call

```python
async def execute_plan(user_query: str, plan: dict, agent: Agent) -> str:
    execute_prompt = EXECUTE_SYSTEM_PROMPT.format(
        original_query=user_query,
        plan_json=json.dumps(plan, indent=2)
    )
    
    # Agent heeft tools van alle sub-agents beschikbaar
    # De LLM volgt het plan en roept de juiste tools aan
    result = await agent.run(
        messages=[
            {"role": "system", "content": execute_prompt},
            {"role": "user", "content": user_query}
        ]
    )
    
    return result
```

### Volledige flow in de MCP tool

```python
@mcp.tool()
async def ask(query: str) -> str:
    """Process a user query through planning and execution."""
    
    # Phase 1: Plan
    plan = await create_plan(query, llm_client)
    
    # Phase 2: Execute
    result = await execute_plan(query, plan, orchestrator_agent)
    
    return result
```

## Logging & Debugging

Elk plan wordt gelogd met:
- Timestamp
- Originele query
- Gegenereerd plan (volledige JSON)
- Welke tools er daadwerkelijk aangeroepen werden tijdens executie
- Totale duur (plan + execute)
- Eventuele errors

Dit maakt het mogelijk om achteraf te zien:
- Werd het plan correct gegenereerd?
- Volgde de LLM het plan tijdens executie?
- Waar ging het mis bij foute antwoorden?

## Toekomstige uitbreidingen

- **Plan caching**: vergelijkbare queries hergebruiken eerder gegenereerde plannen
- **User feedback loop**: als een plan niet klopt, kan de user het bijsturen voor executie
- **Parallel execution**: als steps geen dependencies hebben, concurrent uitvoeren
- **Shared memory / context**: resultaten van eerdere queries beschikbaar maken als context voor nieuwe plannen
- **Confidence scoring**: de planner geeft per step een confidence score, lage scores triggeren clarification questions