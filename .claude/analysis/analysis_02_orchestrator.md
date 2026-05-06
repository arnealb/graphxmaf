# Analysis 02 — Orchestrator in detail

## 1. Doel en verantwoordelijkheid

### OrchestratorAgent (vroege versie)
Niet meer aanwezig als aparte klasse. De oorspronkelijke `OrchestratorAgent` die subagents als `FunctionTool` aanbood is vervangen door de `PlanningOrchestrator`. Er is geen `agents/orchestrator_agent.py`-bestand aanwezig in de huidige codebase; de `orchestrator/mcp_server.py` bevat een lege `__init__.py`-placeholder.

### PlanningOrchestrator
**Bestand**: `agents/planning_orchestrator.py`
**Klasse**: `PlanningOrchestrator` (regels 169–534)
**Fabriek**: `create_planning_orchestrator()` (regels 539–576)

De `PlanningOrchestrator` is verantwoordelijk voor het ontvangen van gebruikersvragen, het decomponeren in uitvoerbare stappen, het parallel uitvoeren van die stappen via gespecialiseerde subagents, en het synthetiseren van het eindantwoord. De klasse is de centrale beslissingsknoop van het systeem.

---

## 2. Alle relevante klassen en functies met regelreferenties

### `PlanningOrchestrator` klasse (`agents/planning_orchestrator.py`)

| Methode | Regels | Verantwoordelijkheid |
|---|---|---|
| `__init__()` | 177–193 | Constructor: planner, synthesizer, drie subagents, step_timeout (standaard 300s) |
| `_accumulate_usage()` | 195–199 | Telt input/output-tokens op uit agentrespons |
| `run_sse()` | 203–285 | Publieke async generator; orkestreert plan→execute→synthesize; yieldt SSE events |
| `_create_plan()` | 289–324 | Roept planner aan, parst JSON, valideert, maximaal 2 pogingen |
| `_validate_plan()` | 326–355 | Valideert schema: `steps`, `id`, `agent`, `depends_on` aanwezig; agenten bestaan |
| `_available_agents_description()` | 357–383 | Bouwt de beschrijving van beschikbare agenten voor de planner |
| `_topological_waves()` | 387–422 | Groepeert stappen in sequentiële waves van parallel-uitvoerbare stappen |
| `_enrich_task()` | 424–437 | Injecteert resultaten van afhankelijke stappen in de taakomschrijving |
| `_execute_step()` | 439–506 | Voert één stap uit; timeout; foutafhandeling; logging naar RoutingTrace |
| `_synthesize()` | 510–534 | Bouwt context van alle resultaten en roept synthesizer aan |

### `create_planning_orchestrator()` (`agents/planning_orchestrator.py`, regels 539–576)

Fabrieksfunctie die:
1. Een `AzureOpenAIChatClient` aanmaakt met de Azure OpenAI-configuratie
2. Een `PlannerAgent` instantieert (Agent met `tools=[]` en `PLAN_SYSTEM_PROMPT`)
3. Een `SynthesizerAgent` instantieert (Agent met `tools=[]` en `SYNTHESIS_SYSTEM_PROMPT`)
4. Een `PlanningOrchestrator` teruggeeft

---

## 3. Hoe de orchestrator vragen ontvangt

In `main_ui.py` (regels 127–148) wordt bij een POST `/api/chat` de methode `_orchestrator.run_sse(body.message, session=session)` aangeroepen. De methode is een async generator die `dict`-events yieldt met type `"text"`, `"done"` of `"error"`. De FastAPI-route wikkelt dit in een `StreamingResponse` met `text/event-stream`.

In `eval/mlflow_eval.py` (regels 145–182) wordt `run_and_collect(orchestrator, query)` aangeroepen, die alle SSE-events verzamelt tot een enkel resultaat-dict.

---

## 4. Hoe agentselectie werkt

Agentselectie is volledig **LLM-gebaseerd**. Er is geen rule-based classifier of keyword-filter.

De planningfase werkt als volgt:

**Stap 1**: `_available_agents_description()` (regels 357–383) bouwt een string:
```
graph (Microsoft 365: emails, calendar events, OneDrive files, ...),
salesforce (CRM: accounts, CRM contacts, leads, opportunities, cases — ...),
smartsales (locations, catalog items — ...)
| For open-ended entity queries ('tell me about X', ...) — use ALL agents.
```

**Stap 2**: De planner ontvangt `"Available agents: <beschrijving>\n\nUser query: <vraag>"` als prompt.

**Stap 3**: De planner genereert een JSON-plan met `"agent"` velden per stap. Het model beslist zelf welke agent(en) nodig zijn op basis van de beschrijving en de vraag.

**Richting via systemprompt**: De `PLAN_SYSTEM_PROMPT` bevat uitgebreide routing-richtlijnen (regels 37–136), waaronder:
- Onderscheid TYPE A (semantische documenten) vs TYPE B (bestandsnamen) voor Graph
- Expliciete instructie dat SmartSales API-queries naar `smartsales` moeten en NIET naar `graph`
- 360°-querylogica: bij "full picture" alle agents gebruiken
- Definitie dat "registered location" SmartSales is en niet Salesforce

Dit zijn echter **instructies in een systemprompt**, niet harde code-regels. De LLM kan deze instructies niet volgen, verkeerd interpreteren, of anders reageren bij randgevallen.

**Validatie in code** (regels 326–355): `_validate_plan()` controleert achteraf of de geselecteerde agents bestaan in `valid_agents`, maar doet geen inhoudelijke controle van de agentskeuze.

---

## 5. Hoe subagents als tools worden aangeboden

De `PlanningOrchestrator` biedt subagents **niet als FunctionTool** aan (dit was het oude patroon). In de huidige architectuur zijn subagents **directe Python-objecten** (`Agent`-instanties) die via `agent.run(task)` worden aangeroepen.

```python
# agents/planning_orchestrator.py, regel 441-446
agent = {
    "graph": self._graph_agent,
    "salesforce": self._sf_agent,
    "smartsales": self._ss_agent,
}.get(step["agent"])
...
resp = await asyncio.wait_for(agent.run(task, **kwargs), timeout=self._step_timeout)
```

De agentselectie is een simpele dictionary lookup op de string-naam die de planner in het plan heeft geschreven. Er is geen dynamische tool-registratie via `FunctionTool` meer in de huidige codebase.

---

## 6. Hoe PlanningOrchestrator plan→DAG→synthesize werkt

### Fase 1: Planning (`_create_plan()`, regels 289–324)

```python
prompt = f"Available agents: {available}\n\nUser query: {query}"
resp = await self._planner.run(prompt, **kwargs)
raw = resp.text.strip()
# Markdown fences verwijderen indien aanwezig
plan = json.loads(raw)
self._validate_plan(plan)
```

Het plan-JSON heeft dit schema (uit `PLAN_SYSTEM_PROMPT`):
```json
{
  "query": "...",
  "reasoning": "...",
  "steps": [
    {"id": 1, "agent": "graph", "task": "...", "depends_on": []},
    {"id": 2, "agent": "salesforce", "task": "...", "depends_on": []}
  ],
  "synthesis": "..."
}
```

Er zijn maximaal 2 pogingen bij mislukte JSON-parsing of validatie.

### Fase 2: DAG-executie (`_topological_waves()` + `_execute_step()`)

`_topological_waves()` (regels 387–422) groepeert stappen in waves:
- Wave 1: alle stappen waarvan `depends_on` leeg is → kunnen parallel
- Wave 2: stappen waarvan alle `depends_on`-IDs in wave 1 zitten → kunnen parallel
- Enzovoort

Per wave: `asyncio.gather(*coros, return_exceptions=True)` (regel 248) voert alle stappen in de wave simultaan uit.

`_enrich_task()` (regels 424–437) injecteert resultaten van vorige stappen in de taakbeschrijving voor afhankelijke stappen:
```
[Result from step 1]:
<resultaat>

[Task]:
<originele taak>
```

`_execute_step()` (regels 439–506) voert per stap:
1. Lookup van de juiste agent (dictionary op naam)
2. `agent.run(task)` met timeout van 300 seconden
3. Extractie van `llm_turns` en `tool_calls` uit de responsmessages
4. Logging naar `RoutingTrace` via `get_trace().invoked_agents.append(...)`

### Fase 3: Synthese (`_synthesize()`, regels 510–534)

```python
context = f"User query: {query}\nSynthesis instruction: {plan['synthesis']}\nStep results:\n[Step 1 — graph]:\n{results[1]}\n..."
resp = await self._synthesizer.run(context, **kwargs)
return resp.text
```

De synthesizer krijgt alle ruwe resultaten als tekst en produceert een eindantwoord op basis van `SYNTHESIS_SYSTEM_PROMPT`.

---

## 7. Hoe resultaten worden teruggegeven

`run_sse()` yieldt `dict`-events:
- `{"type": "text", "chunk": "Planning query...\n"}` — tussenstatus
- `{"type": "text", "chunk": f"Plan: {len(steps)} stap(pen)\n"}` — plansamenvatting
- `{"type": "text", "chunk": f"Executing ({agents_label})...\n"}` — per wave
- `{"type": "text", "chunk": answer}` — het eindantwoord
- `{"type": "done", "tokens": {"input": N, "output": N, "total": N}}` — tokengebruik
- `{"type": "error", "message": str}` — bij fouten

---

## 8. Gedeelde state/context (RoutingTrace, ContextVar)

**`RoutingTrace`** (`agents/routing_trace.py`):

```python
@dataclass
class RoutingTrace:
    user_query: str
    plan: Optional[dict] = None         # het gegenereerde plan
    invoked_agents: list[AgentInvocation] = field(default_factory=list)

@dataclass
class AgentInvocation:
    agent: str          # "graph" | "salesforce" | "smartsales"
    order: int          # stapvolgorde
    input: str          # taakbeschrijving gestuurd naar subagent
    started_at: str     # ISO-8601 UTC
    ended_at: str       # ISO-8601 UTC
    success: bool
    error: Optional[str]
    llm_turns: int      # aantal LLM-iteraties
    tool_calls: list    # namen van aangeroepen tools
```

De `RoutingTrace` wordt opgeslagen in een `ContextVar` (`_CURRENT_TRACE`). Dit garandeert dat elke asyncio-taak (inclusief child-coroutines) dezelfde trace-instantie ziet, zonder dat die doorgegeven hoeft te worden als parameter.

`start_trace(user_query)` (regel 71) maakt een nieuwe trace en bindt die aan de huidige asyncio-context. `get_trace()` (regel 82) leest die terug. De `_execute_step()` methode (regels 492–506) schrijft na elke stap een `AgentInvocation` naar de trace.

De `AgentSession` (uit `agent_framework`) biedt ook multi-turn geheugen, maar dit is een externe klasse en niet in de projectcode gedefinieerd.

---

## 9. Beslissingslogica expliciet in code

De volgende routing-beslissingen staan **hard-coded** in Python:

1. **Agentlookup** (`_execute_step()`, regel 441): Mapping van string-naam naar Python-object. Een niet-herkende agentnaam gooit een `ValueError`.
2. **Validatie van agenten** (`_validate_plan()`, regel 330–349): Controleert dat alleen beschikbare agenten worden gebruikt.
3. **DAG-berekening** (`_topological_waves()`, regels 387–422): Cyclische afhankelijkheid gooit `ValueError`.
4. **Timeoutbeheer** (`_execute_step()`, regel 459): Stap time-out na 300 seconden.
5. **Azure content-filterafhandeling** (regels 465–468): Bij `content_filter`-fout wordt een vaste tekst teruggegeven zonder te crashen.

---

## 10. Beslissingslogica impliciet in prompts/modelgedrag

De volgende beslissingen zijn **volledig LLM-afhankelijk** en niet in code afdwingbaar:

1. **Agentselectie**: Welke agent(en) voor een vraag? Dit staat beschreven in `PLAN_SYSTEM_PROMPT` (regels 37–136) maar wordt beslist door het LLM.
2. **Parallellisatie**: Wanneer een stap afhankelijk is van een andere? De planner beslist dit via `depends_on`.
3. **Granulariteit**: Één stap of meerdere? De planner kan te veel of te weinig stappen genereren.
4. **Taakinstructie per stap**: De `task`-string die naar de subagent gaat, wordt volledig door de planner geformuleerd.
5. **Toolselectie binnen subagents**: Welk tool (`search_documents` vs `search_files`, `list_calendar` vs `search_calendar`) een subagent gebruikt, wordt door zijn eigen LLM-instelling beslist op basis van de systemprompt-instructies.
6. **Synthesekwaliteit**: Of de synthesizer een gestructureerd, volledig antwoord geeft of samenvatting oplevert.

---

## 11. Risico's voor voorspelbaarheid, reproduceerbaarheid en debugging

**Voorspelbaarheid**: Bij identieke vragen kan de planner andere agenten kiezen of een andere planstructuur genereren. Dit is inherent aan LLM-niet-determinisme. De temperatuur-instelling is niet zichtbaar in de code (standaard van `agent_framework` wordt gebruikt).

**Reproduceerbaarheid**: Twee runs op dezelfde vraag kunnen verschillende resultaten geven doordat:
- De planner andere stappen genereert
- Subagents andere tools kiezen
- De synthesizer anders samenvoegt

**Debugging**: De `RoutingTrace` biedt zichtbaarheid in welke agents werden aangeroepen met welke taak en welke tools ze riepen, maar er is geen logging van de volledige LLM-prompt-historiek van de planner of synthesizer. Fouten in planninglogica zijn moeilijk te lokaliseren zonder de ruwe LLM-output te loggen.

**Mis-routing**: Als de planner `smartsales` kiest voor een HR-vraag of `graph` voor een locatievraag, is er geen correctiemechanisme in de uitvoeringsfase. De systemprompt probeert dit te voorkomen via expliciete voorbeelden (regels 99–136 van `PLAN_SYSTEM_PROMPT`), maar dit is geen garantie.

---

## 12. Concrete prompts/system messages

### PLAN_SYSTEM_PROMPT (volledig geciteerd, regels 37–136 van `agents/planning_orchestrator.py`)

```
You are a planning agent. Given a user query and a list of available agents,
produce a structured execution plan.

Respond ONLY with valid JSON — no markdown, no code fences, no explanation.

Output schema:
{
  "query": "<original user query>",
  "reasoning": "<brief explanation of why you chose these steps>",
  "steps": [
    {
      "id": 1,
      "agent": "<graph|salesforce|smartsales>",
      "task": "<self-contained description of what the agent must do>",
      "depends_on": []
    }
  ],
  "synthesis": "<instruction for combining the step results into a final answer>"
}

Rules:
- Use the MINIMUM number of steps necessary to answer the query.
- Only use agents listed as available.
- Set depends_on to [] unless a step genuinely requires the OUTPUT of a previous step.
[... zie volledige prompt in agents/planning_orchestrator.py regels 37-136]
```

Cruciale secties zijn:
- **Over-planning voorkomen** (regels 67–72): Vereis slechts één stap per systeem tenzij een tweede call echt de output van de eerste nodig heeft.
- **SmartSales vs Graph** (regels 99–110): Expliciete instructie dat SmartSales API-queries NOOIT naar graph mogen.
- **360°-view queries** (regels 112–136): Bij open vragen over een entiteit alle agents gebruiken.

### SYNTHESIS_SYSTEM_PROMPT (regels 138–163 van `agents/planning_orchestrator.py`)

```
You are a synthesis agent. Given a user query, an execution plan, and
the results from each step, produce a clear and helpful final answer.

Style rules:
- Be concise and factual.
- Use bullet points or sections when presenting data from multiple sources.
- Clearly indicate which system each piece of information comes from
  (e.g. "From Microsoft 365: ..." / "From Salesforce: ..." / "From SmartSales: ...").
[...]
Gap detection (missing location / no record):
- When asked which companies do NOT have a location or record, compare the full list
  from one system against the other using fuzzy name matching ...
```

### GraphAgent systemprompt (regels 25–82 van `agents/graph_agent.py`)

Bevat gedetailleerde toolselectieregels (strict tool selection rules), persoonresolutie-instructies, en outputformaatspecificaties. Injecteert ook het huidige UTC-datum voor tijdsbewust redeneren.

### SalesforceAgent systemprompt (regels 22–43 van `agents/salesforce_agent.py`)

Bevat instructies voor gelinkte queries (zoek eerst account-ID op, gebruik dat dan voor opportunities/cases) en strikt toolgebruik.

### SmartSalesAgent systemprompt (regels 24–56 van `agents/smartsales_agent.py`)

Bevat specifieke instructies voor het `q`-parameter JSON-formaat, de `p`-projectieregel (standaard `"simple"`), en het twee-staps patroon voor order-zoeken (eerst locatie-UID ophalen).
