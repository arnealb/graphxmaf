# Analysis 10 — Observability en evaluatiehaken

## 1. Overzicht van de observabiliteitslagen

Het systeem bevat vier observabiliteitslagen die op verschillende granulariteitsniveaus opereren:

| Laag | Mechanisme | Granulariteit | Persistentie |
|---|---|---|---|
| 1. RoutingTrace | ContextVar-dataclass | Per run: agents, tools, timestamps, tokens | In-memory; optioneel JSON-artifact |
| 2. Python logging | `logging.getLogger()` | Per module: INFO/ERROR berichten | Stdout (geen bestand) |
| 3. MLflow metrics | `mlflow.log_metrics()` / `mlflow.log_artifact()` | Per testcase: score, latency, tokens, routing | MLflow tracking store (`mlruns/`) |
| 4. MLflow Tracing | `mlflow.start_span()` (via `instrument_orchestrator`) | Per fase: plan, execute, synthesis | MLflow Trace store |

---

## 2. RoutingTrace: de primaire observabiliteitsinfrastructuur

**Definitie en data-elementen** (`agents/routing_trace.py`):

```python
@dataclass
class RoutingTrace:
    user_query: str
    plan: Optional[dict] = None
    invoked_agents: list[AgentInvocation] = field(default_factory=list)

    def to_dict(self) -> dict: ...
    def to_json(self, **kwargs) -> str: ...
```

```python
@dataclass
class AgentInvocation:
    agent: str          # welke agent
    order: int          # stap-ID uit plan
    input: str          # volledige taakomschrijving gestuurd naar subagent
    started_at: str     # ISO-8601 UTC
    ended_at: str       # ISO-8601 UTC
    success: bool
    error: Optional[str]
    llm_turns: int = 0
    tool_calls: list = field(default_factory=list)
```

**Wat de RoutingTrace vastlegt**:
- De originele gebruikersvraag
- Het volledige plan-JSON (inclusief `reasoning` en `synthesis`-instructie)
- Per stap: welke agent, in welke volgorde, met welke taakomschrijving, start/eindtijdstip, succes/fout, aantal LLM-iteraties en namen van aangeroepen tools

**Wat de RoutingTrace NIET vastlegt**:
- De volledige prompt-historiek van de planner of synthesizer
- De tokentellerst per subagent-stap (enkel op orchestrator-niveau globaal)
- Interne tool-aanroep-resultaten (alleen namen, niet resultaatinhoud)
- HTTP-statuscodes van de MCP-servercalls
- Intermediate LLM-output (chain-of-thought binnen agent_framework)

**Schrijven in `_execute_step()`** (`agents/planning_orchestrator.py`, regels 492–506):
```python
finally:
    ended_at = datetime.now(timezone.utc).isoformat()
    trace = get_trace()
    if trace is not None:
        trace.invoked_agents.append(AgentInvocation(
            agent=step["agent"],
            order=step["id"],
            input=task,
            started_at=started_at,
            ended_at=ended_at,
            success=success,
            error=error,
            llm_turns=llm_turns,
            tool_calls=tool_calls,
        ))
```

---

## 3. Python logging: standaard logging-infrastructuur

Het systeem gebruikt `logging.getLogger()` consequent in alle modules:

| Module | Logger naam | Niveau |
|---|---|---|
| `main_ui.py` | `"ui"` | ERROR (voor exceptions in SSE-generator) |
| `planning_orchestrator.py` | `__name__` | INFO (plan/step resultaten), ERROR |
| `graph/mcp_router.py` | `"graph"` | INFO (tool-aanroepen) |
| `graph/graphrag_searcher.py` | `"graph.graphrag"` | INFO (index laden) |
| `graph/context.py` | `__name__` | INFO/DEBUG (context injectie/update) |
| `salesforce/mcp_server.py` | n.t.b. | — |

**Relevante INFO-log statements in `_execute_step()`** (regels 482–485):
```python
log.info(
    "[step %d / %s] result length=%d llm_turns=%d tool_calls=%s preview=%r",
    step["id"], step["agent"], len(result_text), llm_turns, tool_calls, result_text[:200],
)
```

**Relevante INFO-log in `_synthesize()`** (regels 524, 532):
```python
log.info("[synthesize] context length=%d chars, step_ids_with_results=%s", len(context), list(results.keys()))
log.info("[synthesize] response length=%d preview=%r", len(answer), answer[:300])
```

**Tekortkomingen**:
- Logging gaat naar stdout; geen structureel log-bestand of centraal log-aggregatiesysteem
- De volledige planner-prompt en planner-antwoord worden niet gelogd (enkel het gevalideerde plan-JSON)
- De HTTP-requests naar Graph/Salesforce/SmartSales worden niet gelogd op INFO-niveau (enkel fouten)

---

## 4. MLflow-integratie: experimenttracking

### 4.1 Experiment-structuur

**Bestand**: `eval/mlflow_eval.py`

Elke benchmark-run genereert:
- 1 **parent run** per `--version`/`--service` combinatie
- N **child runs** (genest) per testgeval

**Parent run metrics** (aggregaten over alle testgevallen, regels ca. 580–620):
- `avg_llm_score`, `avg_routing_score`
- `avg_latency_s`, `p95_latency_s`
- `avg_total_tokens`, `p95_total_tokens`
- `avg_routing_precision`, `avg_routing_recall`
- `pass_rate` (fractie van testgevallen met `success=True`)

**Child run metrics** (per testgeval, regels 352–368):
```python
metrics: dict[str, float] = {
    "llm_score":           float(llm_score or 0),
    "routing_score":       float(routing_score or 0),
    "latency_s":           round(result["latency_s"], 3),
    "input_tokens":        float(result["tokens"].get("input", 0) or 0),
    "output_tokens":       float(result["tokens"].get("output", 0) or 0),
    "total_tokens":        float(result["tokens"].get("total", 0) or 0),
    "success":             1.0 if result["success"] else 0.0,
    "routing_precision":   round(routing_precision, 3),
    "routing_recall":      round(routing_recall, 3),
    "n_tool_calls_total":  float(n_tool_calls_total),
    "avg_llm_turns":       float(avg_llm_turns),
    "max_llm_turns":       float(max_llm_turns),
}
metrics.update({k: float(v) for k, v in plan_stats.items()})  # plan_steps, parallel_ratio, etc.
```

**Child run artifacts** (per testgeval):
- `response.txt`: het eindantwoord van de synthesizer
- `routing_trace.json`: volledig `RoutingTrace.to_dict()` resultaat
- `plan.json`: het door de planner gegenereerde plan
- `errors.txt`: foutmeldingen (alleen bij `result["errors"]`)
- `phase_timings.json`: per-fase latency en tokens (alleen met `--trace` flag)

**Child run tags**:
- `version`, `service`, `category`, `difficulty`, `expected_agents`
- `llm_rationale`, `routing_rationale` (eerste 250 tekens van LLM-evaluatoroordeel)
- `llm_comments` (aanvullende evaluatorobservaties)

### 4.2 Routing precision/recall

**Berekening** (`eval/mlflow_eval.py`, regels 336–342):
```python
invoked  = {inv["agent"] for inv in result["routing_trace"].get("invoked_agents", [])}
expected = set(prompt.expected_agents)
routing_precision = len(invoked & expected) / len(invoked)  if invoked  else 0.0
routing_recall    = len(invoked & expected) / len(expected) if expected else 0.0
```

- **Precision**: beschermt tegen over-routing (overbodige agent-aanroepen)
- **Recall**: beschermt tegen under-routing (gemiste vereiste agents)

Deze metriek is binair per agent (aanwezig/afwezig) en houdt geen rekening met de volgorde van aanroepen.

### 4.3 Plan-efficiency metriek

**`compute_plan_stats()`** (`eval/mlflow_eval.py`, regels 186–225):
```python
return {
    "plan_steps":           n,
    "parallel_ratio":       round(max_wave / n, 3),   # fractie in maximale wave
    "critical_path_length": len(waves),                # aantal sequentiële stappen
    "max_parallel_steps":   max_wave,                  # max gelijktijdige stappen
}
```

---

## 5. MLflow Tracing: fase-niveau spans

**Bestand**: `eval/mlflow_tracing.py`

**Mechanisme**: Monkey-patching van drie `PlanningOrchestrator`-methoden (`_create_plan`, `_execute_step`, `_synthesize`) met wrappers die MLflow-spans aanmaken.

**Span-structuur** (regels 99–196):

| Span naam | SpanType | Inputs | Outputs |
|---|---|---|---|
| `plan_generation` | `SpanType.LLM` | `query` (500 tekens) | `n_steps`, `reasoning` (300 tekens), `agents`, `usage` |
| `step_{n}_{agent}` | `SpanType.AGENT` | `agent`, `depends_on`, `task` (400 tekens) | `result` (400 tekens), `llm_turns`, `n_tool_calls`, `tool_calls`, `usage` |
| `synthesis` | `SpanType.LLM` | `query` (300 tekens), `n_results` | `response` (500 tekens), `usage` |

**Token usage per span** (`_usage()`, regels 61–65):
```python
def _usage(orch, before: tuple[int, int]) -> dict:
    inp  = max(0, orch._input_tokens  - before[0])
    out  = max(0, orch._output_tokens - before[1])
    return {"input_tokens": inp, "output_tokens": out, "total_tokens": inp + out}
```
Dit berekent de delta van de cumulatieve orchestrator-tokentellerst vóór en na de fase. De MLflow Traces UI gebruikt dit om de "Token usage" en "Cost breakdown"-panelen te vullen.

**Activatie**: Uitsluitend via de `--trace`-vlag van `mlflow_eval.py` en enkel als `mlflow>=2.13` beschikbaar is (met fallback naar `nullcontext()`).

**Fase-timings** worden teruggegeven via `yield phase_timings`:
```python
{
    "plan":     {"latency_s": 1.2,  "steps": 2, "input_tokens": 320, "output_tokens": 180},
    "steps":    [{"step_id": 1, "agent": "graph", "latency_s": 0.8, ...}],
    "synthesis":{"latency_s": 0.9, "input_tokens": 410, "output_tokens": 220},
}
```

---

## 6. LLM-als-beoordelaar (LLM-as-a-Judge)

**Bestand**: `eval/score.py`

### Antwoordkwaliteits-beoordelaar (`evaluate()`, regels 64–94)

**Systemprompt**: Beoordeelt of het antwoord overeenkomt met het verwachte antwoord. Specifieke instructie: "lege-resultaten"-antwoord telt als correct geconsulteerd systeem.

**Gebruikersprompt**: Bevat vraag, verwacht antwoord, werkelijk antwoord (getrunceerd op 4000 tekens).

**Schaal 1–5**:
- 5: volledig correct en compleet
- 4: correct met kleine gaps
- 3: grotendeels correct met noemenswaardige hiaten
- 2: gedeeltelijk correct met grote gaps
- 1: volledig fout of leeg

**Retourneert**: `(score: int|None, rationale: str, comments: str)`

**Implementatiedetails**: `temperature=0`, `max_tokens=300`; JSON-output geparseerd. Bij parsefout of exception: `(None, "Evaluator error: ...", "")`.

### Routing-beoordelaar (`evaluate_routing()`, regels 149–186)

**Systemprompt**: Beoordeelt of de orchestrator de juiste subagents heeft ingezet.

**Inputs**: Vraag, geformatteerde agent-invocaties (agent, volgorde, status, taakinput tot 200 tekens), verwachte agents.

**Schaal 1–5**:
- 5: exact de verwachte agents, geen overbodige
- 4: correct met kleine inefficiënties
- 3: correct maar met ontbrekende/overbodige agents
- 2: deels correct
- 1: fout gerouteerd

**Retourneert**: `(score: int|None, rationale: str)`

**Implementatiedetails**: `temperature=0`, `max_tokens=200`.

### Combinatie met precision/recall

De LLM-routeringsbeoordelaar beoordeelt op semantische correctheid (houdt rekening met volgorde, irrelevante calls, context van de vraag). De precision/recall-metriek is puur structureel (set-overlap). Beide worden gelogd als MLflow-metrics en geven complementaire informatie.

---

## 7. Evaluatieprompts: `eval/prompts/prompts.json`

**Structuur per prompt** (gebaseerd op `BenchmarkPrompt` dataclass in `mlflow_eval.py`, regels 122–129):
```json
{
    "text": "Welke bedrijven heb ik onlangs gemaild...",
    "category": "implicit-cross-system",
    "difficulty": "hard",
    "expected_answer": "Een lijst van bedrijven + hun opportunities...",
    "tags": ["email", "crm", "cross-system"],
    "expected_agents": ["graph", "salesforce"]
}
```

**Categorieën** (zichtbaar in `mlflow_eval.py`, regel 125):
- `email`, `calendar`, `identity`, `locations`, `crm`, `cross-system`
- Aanvullend (uit de promptstructuur): `entity-centric1`, `entity-centric2`, `graph-extra`, `implicit-cross-system`, `smartsales`

**Gebruik**:
- `--category` filter in `mlflow_eval.py` om specifieke subsets te testen
- `expected_agents`-veld voor precision/recall en routing-evaluator

---

## 8. Ontbrekende observabiliteit

Op basis van de codebase zijn de volgende observabiliteits-hiaten identificeerbaar:

### 8.1 Ontbrekende productielogging

De `RoutingTrace` wordt **niet** opgeslagen in productiegebruik (`main_ui.py`). Er is geen productie-equivalent van de MLflow-logging. Elke productie-query gaat verloren zonder tracering.

```python
# main_ui.py, regel 137
start_trace(body.message)
# ... run_sse() ...
# Na afloop: geen trace-persistentie
```

### 8.2 Planner-prompt niet gelogd

De volledige prompt van de planner (met de complete `PLAN_SYSTEM_PROMPT` + gebruikersvraag) wordt nergens gelogd. Bij planningsfouten is de LLM-invoer niet reconstrueerbaar.

### 8.3 GraphRAG-aanroepen buiten tokenaccumulatie

De `_search_sync()` gebruikt een synchrone `AzureOpenAI`-client waarvan de tokenconsumptie NIET via `_accumulate_usage()` wordt gevangen. De embedding-aanroep en de completion-aanroep in GraphRAG zijn dus niet zichtbaar in de MLflow `input_tokens`/`output_tokens`-metrics.

### 8.4 Geen latency-logging per tool-aanroep

De `RoutingTrace` registreert `started_at`/`ended_at` per subagent-stap maar niet per individuele tool-aanroep. De latency van `list_email` versus `search_documents` is niet onderscheidbaar.

### 8.5 Geen HTTP-niveau logging

MCP-server-requests (poort 8000/8001/8002) genereren geen structured logs voor response-tijden, HTTP-statuscodes of request-payloads.

### 8.6 Geen productie-health checks

Er zijn geen `/health`- of `/metrics`-endpoints op de MCP-servers of de FastAPI UI-server. Azure Container Apps-health probes zijn niet geconfigureerd in de codebase.

### 8.7 Tokenteller niet thread-safe

`_input_tokens` en `_output_tokens` zijn instantie-attributen van `PlanningOrchestrator`. Bij twee gelijktijdige `run_sse()`-aanroepen kunnen de cumulatieve tellerst van verschillende runs samenvloeien.

---

## 9. Suggesties voor observabiliteitsverbetering

Concrete verbeteringen die aansluiten bij de bestaande architectuur:

1. **RoutingTrace persistentie in productie**: Schrijven naar een append-only JSONL-bestand (analoog aan `eval/routing_traces.jsonl`) na elke `run_sse()`-aanroep in `main_ui.py`.

2. **GraphRAG-token tracking**: Vervangen van synchrone `AzureOpenAI` door `AsyncAzureOpenAI` in `graphrag_searcher.py` en terugsturen van tokengebruik als onderdeel van het result-dict.

3. **Tool-latency in RoutingTrace**: Toevoegen van een `tool_timings`-veld aan `AgentInvocation` door de timestamps vóór en na elke tool-aanroep te registreren.

4. **Health endpoints**: Toevoegen van `GET /health` op alle MCP-servers (retourneert auth-status, veld-cache status) en op `main_ui.py`.

5. **Planner-output logging**: Loggen van het `plan["reasoning"]`-veld en de gegenereerde plan-stappen op INFO-niveau in productie (reeds aanwezig in `mlflow_eval.py`, ontbreekt in `main_ui.py`).
