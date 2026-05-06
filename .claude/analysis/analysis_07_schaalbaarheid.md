# Analysis 07 — Schaalbaarheid en performantie

## 1. Welke componenten afzonderlijk schaalbaar zijn

Het systeem is opgebouwd uit vier fysiek scheidbare componenten, elk met eigen deployment-grenzen:

| Component | Schaalbaar? | Deployment-eenheid |
|---|---|---|
| FastAPI UI-server (`main_ui.py`, poort 8090) | Ja | Uvicorn-proces; horizontaal schaalbaar achter load balancer |
| Graph MCP-server (`graph/mcp_server.py`, poort 8000) | Ja | Eigen Dockerfile (`Dockerfile.graph`); Azure Container Apps |
| Salesforce MCP-server (`salesforce/mcp_server.py`, poort 8001) | Ja | Eigen Dockerfile (`Dockerfile.salesforce`); Azure Container Apps |
| SmartSales MCP-server (`smartsales/mcp_server.py`, poort 8002) | Ja | Eigen Dockerfile (`Dockerfile.smartsales`); Azure Container Apps |

De `config.cfg` bevat al Azure Container Apps-URLs als standaard `mcpServerUrl` voor alle drie MCP-servers:

```ini
mcpServerUrl = https://graph-mcp.whitemushroom-38caf70a.swedencentral.azurecontainerapps.io/mcp
mcpServerUrl = https://salesforce-mcp.whitemushroom-38caf70a.swedencentral.azurecontainerapps.io/mcp
mcpServerUrl = https://smartsales-mcp.whitemushroom-38caf70a.swedencentral.azurecontainerapps.io/mcp
```

De `_is_local_url()`-controle in `startup.py` (regel 133–135) schakelt automatisch over naar de externe URL zonder dat er subprocessen worden gestart, wat betekent dat de productiedeployment reeds is geanticipeerd in de code.

---

## 2. LLM-aanroepen per query: exacte telling

Elke gebruikersvraag triggert een vaste set LLM-aanroepen plus een variabele set vanuit de subagents:

**Vaste aanroepen per query (PlanningOrchestrator):**

| Aanroep | Locatie | Model |
|---|---|---|
| Planner (`_create_plan()`) | `planning_orchestrator.py:298` | Azure OpenAI (`deployment` env var) |
| Synthesizer (`_synthesize()`) | `planning_orchestrator.py:526` | Azure OpenAI (zelfde deployment) |

**Variabele aanroepen per stap (subagents):**

Elke subagent is een `Agent`-instantie die intern ReAct-stijl itereert: de `llm_turns`-teller in `_execute_step()` (regel 477) telt het aantal `assistant`-berichten per subagent-run. Op basis van de `avg_llm_turns`-metric die in MLflow wordt gelogd (regels 349–350 van `mlflow_eval.py`) geldt gemiddeld 1–3 LLM-iteraties per subagent-aanroep.

**GraphRAG extra aanroep** (`graph/graphrag_searcher.py`):
- 1 embedding-aanroep: `client.embeddings.create(model=idx.embedding_deployment, ...)` (regel 76)
- 1 completion-aanroep: `client.chat.completions.create(...)` (regel 101–119), separaat van de subagent-iteraties

**Minimale telling voor een enkelvoudige query (één agent):**
- 1 (planner) + 1–2 (subagent) + 1 (synthesizer) = 3–4 LLM-aanroepen

**Maximale telling voor een 360°-query (drie agents):**
- 1 (planner) + 3 × 1–3 (subagents parallel) + 1 (synthesizer) = 5–11 LLM-aanroepen
- Als `search_documents` wordt aangeroepen: +2 (embedding + completion)

---

## 3. Sequential vs. parallel uitvoering: de DAG-implementatie

De `_topological_waves()` methode (regels 387–422 van `planning_orchestrator.py`) groepeert stappen in waves:

```python
async def run_sse(self, query, session=None):
    waves = self._topological_waves(steps)
    for wave in waves:
        coros = [self._execute_step(s, task, session=session) for s, task in step_inputs]
        wave_results = await asyncio.gather(*coros, return_exceptions=True)
```

- **Wave 1**: Alle stappen met `depends_on == []` → parallel uitvoering via `asyncio.gather()`
- **Wave 2+**: Stappen waarvan alle afhankelijkheden zijn afgerond → ook parallel binnen de wave

**Voorbeeld plan met parallelisatie:**
```json
{
  "steps": [
    {"id": 1, "agent": "graph",       "depends_on": []},
    {"id": 2, "agent": "salesforce",  "depends_on": []},
    {"id": 3, "agent": "smartsales",  "depends_on": [1, 2]}
  ]
}
```
Hier lopen stap 1 en 2 parallel (wave 1); stap 3 wacht op beiden (wave 2). De tijdsbesparing ten opzichte van sequentieel is de maximumlatency van wave 1, niet de som.

**`compute_plan_stats()`** (`eval/mlflow_eval.py`, regels 186–225) meet:
- `parallel_ratio = max_wave_size / total_steps`: aandeel dat tegelijk kan lopen
- `critical_path_length`: aantal waves (serialisatiegraad)
- `max_parallel_steps`: maximale graad van parallellisme

---

## 4. Async-implementatie: asyncio door de hele stack

**Op orchestrator-niveau**: `run_sse()`, `_create_plan()`, `_execute_step()`, `_synthesize()` zijn alle `async def`. Interne parallelisatie via `asyncio.gather()` (regel 248).

**Op subagent-niveau**: `agent.run()` is een coroutine (uit `agent_framework`). Timeout via `asyncio.wait_for()` (regel 459):
```python
resp = await asyncio.wait_for(agent.run(task, **kwargs), timeout=self._step_timeout)
```

**Op MCP-server-niveau**: FastMCP draait op ASGI (Starlette/Uvicorn); alle handlers zijn `async def`. De repository-calls zijn async (Microsoft Graph SDK: `await`, Salesforce: `httpx.AsyncClient`, SmartSales: `httpx.AsyncClient`).

**Uitzondering — GraphRAG**: `_search_sync()` in `graph/graphrag_searcher.py` is synchroon (regel 63), omdat de synchrone `AzureOpenAI`-client en LanceDB-zoekfunctie worden gebruikt. Omzeiling via `asyncio.to_thread()` (regel 126):
```python
async def search_documents(query: str) -> dict[str, Any]:
    return await asyncio.to_thread(_search_sync, query)
```
Dit blokkeert het asyncio event loop niet, maar verbruikt wel een thread uit de thread pool voor elke `search_documents`-aanroep.

**Op repository-niveau (Graph)**: Alle Graph SDK-calls zijn verpakt in `_graph_call(coro, timeout=30.0)` (`graph/repository.py`, regel 101), die een 30-secondentimeout opzet. Salesforce en SmartSales gebruiken `httpx.AsyncClient` voor asynchroon HTTP.

---

## 5. Caching: wat gecached wordt en wat niet

| Onderdeel | Caching aanwezig | Mechanisme | Scope |
|---|---|---|---|
| Graph repository | Ja | `_repo_cache: dict[str, GraphRepository]` (in `graph/mcp_router.py`, regel 18) | Per token (in-memory, MCP server lifetime) |
| Salesforce repository | Ja | `_repo_cache: dict[str, tuple[SalesforceRepository, str]]` (in `salesforce/mcp_router.py`, regel 29) | Per session+access_token combo |
| SmartSales veldmetadata | Ja | `await repo.warm_field_cache()` bij sessie-aanmaak (`smartsales/mcp_server.py`, regel 84) | In-memory, server lifetime |
| GraphRAG index (LanceDB) | Ja | `_index: _GraphRAGIndex | None = None` (singleton, `graphrag_searcher.py`, regel 52) | In-memory, server lifetime |
| MSAL access tokens | Ja | `.token_cache.bin` + `acquire_token_silent()` | Disk-persistent, auto-refresh |
| Salesforce tokens | Ja | `.salesforce_tokens.json` (`JsonFileTokenStore`) | Disk-persistent, 300s buffer |
| LLM-responses | Nee | Niet geïmplementeerd | — |
| Query-resultaten | Nee | Niet geïmplementeerd | — |
| Tool-aanroep resultaten | Nee | Niet geïmplementeerd | — |

De afwezigheid van query-resultaatcaching betekent dat identieke vragen altijd leiden tot nieuwe LLM-aanroepen en nieuwe API-requests naar Graph/Salesforce/SmartSales. Voor hoge concurrentie of hoge frequentie van identieke queries (bijv. `whoami`) is dit een knelpunt.

---

## 6. Bottlenecks en impactanalyse

### 6.1 Bottleneck 1: Azure OpenAI rate limits

Elke query triggert 3–11 LLM-aanroepen via één Azure OpenAI-deployment. Bij meerdere gelijktijdige gebruikers cumuleren de aanroepen snel:
- 10 gelijktijdige gebruikers × 5 aanroepen = 50 gelijktijdige LLM-requests
- Azure OpenAI-limieten (Tokens Per Minute / Requests Per Minute) zijn deployment-afhankelijk en niet in de code geconfigureerd
- Er is geen retry-logica voor 429-responses in de orchestrator of subagents waarneembaar in de code

### 6.2 Bottleneck 2: MCP-server als singleton

In de huidige architectuur wordt één `PlanningOrchestrator`-instantie gedeeld door alle gebruikers (`main_ui.py`, regel 51: `_orchestrator = None` als globale singleton). De orchestrator zelf is stateless per run (tokentellerst worden gereset in `run_sse()`, regel 211–212), maar de subagents zijn gedeeld:

```python
graph_agent = create_graph_agent(graph_mcp=graph_mcp)  # één instantie
_orchestrator = create_planning_orchestrator(graph_agent=graph_agent, ...)
```

Als `agent_framework` interne state bijhoudt in de `Agent`-instantie (bijv. in `AgentSession`), kan concurrente toegang tot dezelfde instantie leiden tot race conditions. De sessie-isolatie in `main_ui.py` (regel 131–133) scheidt sessie-state per gebruiker via `AgentSession`, maar de agent-instantie zelf is gedeeld.

### 6.3 Bottleneck 3: GraphRAG synchrone thread pool

`search_documents()` voert via `asyncio.to_thread()` een synchrone operatie uit: embed (HTTP) + LanceDB-zoekactie + LLM-call. Elke oproep blokkeert één thread uit de standaard thread pool van Python (standaard `min(32, os.cpu_count() + 4)` threads). Bij hoge concurrentie is de thread pool erschöpft en worden latere aanroepen vertraagd.

### 6.4 Bottleneck 4: Step timeout = 300 seconden

De `step_timeout=300.0` (seconden, `planning_orchestrator.py`, regel 543) betekent dat een vastgelopen subagent-aanroep de event loop 5 minuten kan bezetten voor die coroutine. Bij meerdere gelijktijdige gebruikers kunnen vastgelopen stappen de beschikbare coroutines monopoliseren.

### 6.5 Bottleneck 5: Salesforce browser-authenticatie bij startup

`_resolve_sf_session()` (`startup.py`, regels 196–231) wacht tot 120 seconden op de gebruiker om via de browser in te loggen. Dit blokkeert de gehele startup-sequentie. In een multi-user productieomgeving is dit niet schaalbaar: alle gebruikers delen hetzelfde Salesforce-token, wat ook een governance-risico is (zie analysis_05).

### 6.6 Bottleneck 6: Afwezigheid van rate limiting op MCP-servers

`RoutingMiddleware` (`graph/mcp_server.py`, regels 148–185) controleert enkel de aanwezigheid van een Bearer-token. Er is geen rate limiting op de MCP-servers zelf. De Microsoft Graph API kent limieten van 10.000 requests per 10 minuten per app voor sommige endpoints; Salesforce kent governor limits op SOQL-queries. Wanneer meerdere gebruikers tegelijkertijd queries uitvoeren, kunnen deze limieten worden bereikt.

---

## 7. Impact van externe API-latency

De end-to-end latency van een query is de som van:
1. LLM-planneraanroep (Azure OpenAI): typisch 1–3 seconden
2. Per wave: `max(latency van agents in wave)` — dankzij parallellisatie is dit de langzaamste stap in de wave
3. Per subagent: meerdere LLM-iteraties + API-calls
4. Synthesizer-aanroep: typisch 2–5 seconden

De `mlflow_eval.py` meet `latency_s` als wall-clock tijd van `run_and_collect()`. De `phase_timings`-dict in `mlflow_tracing.py` biedt per-fase breakdown (plan, execute, synthesis). Zonder MLflow-tracing is er geen granulaire latency-logging beschikbaar in de productiecode.

Externe API-timeouts:
- Graph SDK-calls: 30 seconden (`_graph_call()`)
- Subagent-stap: 300 seconden (`step_timeout`)
- SmartSales-sessie: 30 seconden polling
- Salesforce-sessie: 120 seconden

---

## 8. Ontbrekende load/concurrency-tests

Op basis van de codebase zijn er **geen** load- of concurrency-tests aanwezig:
- Geen `pytest` load tests
- Geen `locust`- of `k6`-configuraties
- Geen benchmark voor gelijktijdige gebruikers
- `eval/mlflow_eval.py` is een sequentiële benchmark (één query tegelijk via `asyncio.run(main())`)

De MLflow-metrics (`latency_s`, `total_tokens`, `n_tool_calls_total`) geven inzicht in per-query performantie maar niet in gedrag onder gelijktijdige belasting.

---

## 9. Schaalbaarheidsverbetering in volgende versie

Op basis van de codebase-structuur zijn de volgende verbeteringen aantoonbaar haalbaar zonder ingrijpende herarchitectuur:

1. **LLM-response caching**: Toevoegen van een `TTLCache` (bijv. `cachetools`) op de planner voor identieke query-texts reduceert Azure OpenAI-aanroepen voor herhaalde vragen.
2. **Aparte authenticatie per gebruiker (Salesforce/SmartSales)**: Verplaatsen van sessie-initialisatie naar het `/api/sessions`-endpoint; elke sessie krijgt eigen tokens.
3. **Rate-limiting middleware op MCP-servers**: Toevoegen van een Starlette-middleware analoog aan `RoutingMiddleware` die per-IP of per-token aanroepen beperkt.
4. **GraphRAG async client**: Vervangen van synchrone `AzureOpenAI` door `AsyncAzureOpenAI` in `graphrag_searcher.py`; elimineren van `asyncio.to_thread()` overhead.
5. **Horizontale schaling van MCP-servers**: De productie-URLs (`config.cfg`) wijzen al naar Azure Container Apps, die automatisch schalen op basis van HTTP-requests. Geen code-aanpassing vereist.
6. **Step timeout verlaging**: Verlagen van 300 naar 60–90 seconden voor productiegebruik om event loop stagnatie te voorkomen.

---

## 10. Thesis-ready paragraaf: Schaalbaarheid en performantie-overwegingen

### Schaalbaarheid en performantie-overwegingen in de multi-agent enterprise search architectuur

De schaalbaarheid van een multi-agent systeem voor enterprise search wordt bepaald door de samenstelling van de verwerkingsketen: elke gebruikersvraag doorloopt meerdere opeenvolgende en parallelle bewerkingsstappen, elk met eigen latency, resource-consumptie en externe afhankelijkheden. In de besproken implementatie zijn de voornaamste componenten voor schaalbaarheid de drie FastMCP-servers (Graph, Salesforce, SmartSales op respectievelijk poorten 8000, 8001 en 8002), de FastAPI UI-server (poort 8090), en de Azure OpenAI-instantie die alle LLM-aanroepen bedient. Elk van de MCP-servers beschikt over een eigen Dockerfile en is reeds geconfigureerd voor deployment op Azure Container Apps, zoals blijkt uit de Azure Container Apps-URLs in `config.cfg`. Dit maakt onafhankelijke horizontale schaling van de domeinspecifieke backends mogelijk, zonder dat de orchestratielaag hoeft te worden aangepast.

Het aantal LLM-aanroepen per gebruikersvraag is een centrale maatstaf voor de schaalbaarheid ten opzichte van de Azure OpenAI rate limits. De `PlanningOrchestrator` genereert per query minimaal twee vaste aanroepen — één voor de planner (`_create_plan()`) en één voor de synthesizer (`_synthesize()`) — aangevuld met een variabel aantal aanroepen vanuit de subagents. Subagents itereren intern via een ReAct-stijl lus waarbij elke LLM-iteratie een `assistant`-bericht genereert; de `llm_turns`-teller in `_execute_step()` (regels 473–480 van `agents/planning_orchestrator.py`) registreert dit aantal. Voor een enkelvoudige single-agent query bedraagt het totaal 3–4 LLM-aanroepen; voor een 360°-query met drie gelijktijdige agents loopt dit op tot 5–11 aanroepen. Wanneer de `search_documents`-tool in de Graph-agent wordt aangeroepen, komen hier twee extra aanroepen bij: een embedding-aanroep en een completion-aanroep in `graph/graphrag_searcher.py` (regels 76 en 101). Onder hoge belasting — bij tien gelijktijdige gebruikers en vijf aanroepen gemiddeld — genereert het systeem 50 gelijktijdige LLM-requests naar dezelfde Azure OpenAI-deployment. Er is in de huidige code geen retry-logica voor 429-responsen (rate-limit overschrijding) geïmplementeerd in de orchestrator.

De sequentiële versus parallelle uitvoeringsstrategie van de orchestrator is een expliciete schaalbaarheidsoptimalisatie. De `_topological_waves()`-methode (regels 387–422 van `agents/planning_orchestrator.py`) groepeert onafhankelijke planstappen in parallelle waves, die vervolgens via `asyncio.gather()` gelijktijdig worden uitgevoerd. Dit reduceert de wall-clock latency ten opzichte van puur sequentiële uitvoering: voor een plan met drie onafhankelijke stappen is de totale uitvoeringstijd gelijk aan de maximumlatency van de langzaamste stap, niet aan de som. De `compute_plan_stats()`-functie in `eval/mlflow_eval.py` (regels 186–225) kwantificeert dit via `parallel_ratio` (verhouding van maximale wave-grootte tot totale stapcount) en `critical_path_length` (aantal waves). Deze metriek is beschikbaar in de MLflow-benchmark maar wordt niet in productiemonitoring gelogd.

De algehele asyncio-implementatie van het systeem draagt bij aan de schaalbaarheid voor I/O-bound werklasten. Alle orchestratorfuncties (`run_sse()`, `_create_plan()`, `_execute_step()`, `_synthesize()`), alle MCP-server-handlers en alle repository-aanroepen (Microsoft Graph SDK, Salesforce en SmartSales via `httpx.AsyncClient`) zijn asynchroon geïmplementeerd. Een structurele uitzondering vormt de `_search_sync()`-functie in `graph/graphrag_searcher.py` (regel 63), die synchroon is en via `asyncio.to_thread()` (regel 126) in de thread pool van Python wordt uitgevoerd. Bij hoge gelijktijdigheid kan de standaard thread pool (begrensd op `min(32, os.cpu_count() + 4)` threads) een bottleneck worden voor `search_documents`-aanroepen.

Op het vlak van caching zijn twee categorieën te onderscheiden: token- en sessiecaching en repository-caching. MSAL beheert de Graph-accesstokens via `.token_cache.bin` en `acquire_token_silent()` (`startup.py`, regels 52–62), waardoor browser-authenticatie slechts eenmalig nodig is. De Salesforce-tokencache (`JsonFileTokenStore`, `.salesforce_tokens.json`) herbouwt de sessie na herstart. Op repository-niveau cachen zowel de Graph MCP-server (`_repo_cache` in `graph/mcp_router.py`, regel 18) als de Salesforce MCP-server (`_repo_cache` in `salesforce/mcp_router.py`, regel 29) de repository-instanties per accesstoken in geheugen. De SmartSales-server laadt de veldmetadata eenmalig bij sessie-aanmaak via `warm_field_cache()` (`smartsales/mcp_server.py`, regel 84). LLM-responsen en query-resultaten worden echter niet gecached: identieke gebruikersvragen leiden altijd tot nieuwe API-aanroepen en LLM-aanroepen.

Twee structurele beperkingen zijn relevant voor productiegebruik. Ten eerste is de `PlanningOrchestrator`-instantie in `main_ui.py` een globale singleton die gedeeld wordt door alle gelijktijdige gebruikers. Hoewel de tokentellerst per run worden gereset (`run_sse()`, regels 211–212) en sessie-isolatie via `AgentSession` per gebruiker is geïmplementeerd, zijn de subagent-instanties zelf gedeeld. Ten tweede is de startup-authenticatieprocedure voor Salesforce gebonden aan een blocking wachttijd van maximaal 120 seconden voor browser-authenticatie (`_resolve_sf_session()`, `startup.py`, regels 196–231), wat in een multi-user productiescenario onschaalbaar is. SmartSales authentiseert server-to-server (30 seconden polling), wat beter schaalbaar is maar geen gebruikersspecifieke toegangscontrole biedt.

De ontbrekende load- en concurrency-tests zijn een significante lacune in het huidige evaluatiekader. De MLflow-benchmark (`eval/mlflow_eval.py`) is uitsluitend sequentieel: prompts worden één voor één verwerkt via `asyncio.run(main())`. Er zijn geen gelijktijdige-gebruiker-simulaties, geen load tests en geen tests voor gedrag bij rate-limit overschrijding van de externe APIs. Voor een volgende evaluatieronde zou een concurrentiebenchmark — waarbij meerdere coroutines `run_sse()` gelijktijdig aanroepen — inzicht kunnen geven in de werkelijke schaalbaarheidsgrens van het systeem bij gedeelde Azure OpenAI-resources en gedeelde MCP-server-instanties.

---
