# Analysis 09 — State, context en geheugen

## 1. Overzicht: stateful vs. stateless componenten

| Component | Stateful? | State-type | Scope | Persistentie |
|---|---|---|---|---|
| `PlanningOrchestrator` | Gedeeltelijk | `_input_tokens`, `_output_tokens` | Per run (gereset in `run_sse()`) | In-memory, vluchtig |
| `RoutingTrace` (ContextVar) | Ja | `RoutingTrace`, `AgentInvocation`s | Per asyncio-context (per run) | In-memory; optioneel als artifact |
| `AgentSession` (agent_framework) | Ja | Berichten-geschiedenis (multi-turn) | Per sessie-ID (HTTP-sessie) | In-memory (`_sessions`-dict) |
| `DocumentContextProvider` | Ja | `doc_context` in `session.state` | Per sessie-ID | In-memory (via `AgentSession`) |
| Graph MCP-server | Gedeeltelijk | `_repo_cache`, `_graphrag_index` | Server lifetime | In-memory (singleton) |
| Salesforce MCP-server | Ja | `_token_store`, `_pending_states`, `_repo_cache`, `_session_ref` | Server lifetime + disk | Disk (`.salesforce_tokens.json`, `.sf_session.json`) |
| SmartSales MCP-server | Gedeeltelijk | Session-token, field cache | Server lifetime | Disk (`.ss_session.json`), in-memory |
| MSAL-tokencache | Ja | Access + refresh tokens | Process lifetime | Disk (`.token_cache.bin`) |

---

## 2. RoutingTrace: per-run observabiliteitsstaat

**Definitie** (`agents/routing_trace.py`):

```python
@dataclass
class RoutingTrace:
    user_query: str
    plan: Optional[dict] = None
    invoked_agents: list[AgentInvocation] = field(default_factory=list)
```

```python
@dataclass
class AgentInvocation:
    agent: str          # "graph" | "salesforce" | "smartsales"
    order: int          # plan-stap-ID
    input: str          # volledige taakomschrijving
    started_at: str     # ISO-8601 UTC
    ended_at: str       # ISO-8601 UTC
    success: bool
    error: Optional[str]
    llm_turns: int = 0
    tool_calls: list = field(default_factory=list)
```

**Lifecycle**:
1. `start_trace(user_query)` (regel 71–79): aangemaakt en gebonden aan huidige asyncio-context via `_CURRENT_TRACE.set(trace)`
2. `trace.plan = plan` na planfase (regel 225 van `planning_orchestrator.py`)
3. `trace.invoked_agents.append(AgentInvocation(...))` na elke stap in `_execute_step()` (regels 492–506)
4. `get_trace()` (regel 82–88): leest de trace terug; retourneert `None` buiten een `start_trace()`-scope

**ContextVar-semantiek** (regels 57–68 van `routing_trace.py`):

```python
_CURRENT_TRACE: ContextVar[Optional[RoutingTrace]] = ContextVar("routing_trace", default=None)
```

`ContextVar.set()` in een coroutine wordt geïsoleerd in de asyncio-context van die task. Alle `await`-punten binnen dezelfde coroutine zien dezelfde trace-instantie. Als `agent_framework` intern `asyncio.create_task()` aanroept, ontvangt de nieuwe task een kopie van de context die naar hetzelfde `RoutingTrace`-object verwijst (mutaties zijn zichtbaar aan de aanroeper).

**Persistentie**:
- In `main_ui.py`: niet gepersisteerd na de run
- In `eval/mlflow_eval.py`: `trace.to_dict()` → `routing_trace.json` artifact in MLflow
- In `eval/script.py`: optioneel geschreven naar `eval/routing_traces.jsonl`

---

## 3. AgentSession: multi-turn conversatiegeheugen

**Definitie** (`agent_framework.AgentSession`): Extern gedefinieerde klasse; niet aanwezig in de projectcode. Gebaseerd op observatie in `main_ui.py`.

**Aanmaak** (`main_ui.py`, regels 110–114):
```python
@app.post("/api/sessions", status_code=201)
def create_session():
    session = AgentSession()
    _sessions[session.session_id] = session
    return {"session_id": session.session_id}
```

**Gebruik** (regel 131–138):
```python
session = _sessions.get(body.session_id)
async for event in _orchestrator.run_sse(body.message, session=session):
    ...
```

De `session` wordt doorgegeven aan alle `agent.run()` aanroepen, inclusief de planner, synthesizer en alle subagents. Het `agent_framework` slaat de berichten-geschiedenis op per sessie, zodat de context van vorige vragen beschikbaar is voor de LLM in vervolgvragen.

**Scope**: `_sessions: dict[str, AgentSession]` is een globale in-memory dictionary in `main_ui.py` (regel 52). Sessions worden niet automatisch verwijderd; er is geen TTL of sessie-expiry geïmplementeerd.

**Verwijdering** (regel 117–119):
```python
@app.delete("/api/sessions/{session_id}", status_code=204)
def delete_session(session_id: str):
    _sessions.pop(session_id, None)
```

Alleen via expliciete client-aanroep; geen garbage collection.

**Risico voor schaalbaar gebruik**: Alle sessies leven in de geheugen van één proces. Bij herstart van `main_ui.py` gaan alle sessies verloren. Er is geen sessie-persistentie (bijv. Redis, database) geïmplementeerd.

---

## 4. DocumentContextProvider: bestandszoekgeheugen

**Klasse** (`graph/context.py`): `DocumentContextProvider(BaseContextProvider)`

**Doel**: Injecteert informatie over eerder gevonden bestanden in de volgende LLM-iteratie van de GraphAgent, zodat de agent bestandsnamen en IDs niet opnieuw hoeft te zoeken.

**`before_run()`** (regels 24–49): Lees `session.state.get("doc_context")` en injecteer als system-message:
```
[Session Context]
Current topic: onboarding procedure
Last search: "onboarding guide"
Files found: HR_Onboarding_Guide.docx (abc123), Welcome_Pack.pdf (def456)
```

**`after_run()`** (regels 51–103): Scan response-messages voor `function_call`-entries met naam in `_FILE_TOOLS = {"search_files", "read_file", "read_multiple_files"}`. Bij treffer: extraheer bestandsnamen en IDs uit het `function_result`-antwoord via regex:
```python
ids   = re.findall(r"^ID:\s*(.+)$",   result_text, re.MULTILINE)
names = re.findall(r"^Name:\s*(.+)$", result_text, re.MULTILINE)
```

**State-update** in `session.state["doc_context"]`:
```python
doc_ctx["topic"]      = query        # huidige zoekterm
doc_ctx["last_query"] = query        # zelfde
doc_ctx["files"].update(new_files)   # ID→naam mapping, cumulatief
```

**Beperking**: Enkel aanwezig bij de GraphAgent (regels 78–81 van `agents/graph_agent.py`); niet bij Salesforce- of SmartSalesAgent. Het bestanden-woordenboek groeit cumulatief per sessie, er is geen vervalbeleid.

---

## 5. In-memory staat in de MCP-servers

### Graph MCP-server

**`_repo_cache: dict[str, GraphRepository]`** (`graph/mcp_router.py`, regel 18):
- Sleutel: Bearer token (de eerste ~20 tekens zijn per gebruiker uniek)
- Waarde: `GraphRepository`-instantie met geconfigureerde `StaticTokenCredential`
- Scope: server lifetime (leeggelopen bij serverherstart)
- Implicatie: bij tokenvernieuwing (nieuw Bearer-token) wordt een nieuwe instantie aangemaakt; de oude blijft in de cache tot herstart → geheugenlek bij langdurig gebruik

**`_index: _GraphRAGIndex | None`** (`graph/graphrag_searcher.py`, regel 52):
- Singleton; aangemaakt bij eerste `search_documents`-aanroep of pre-load bij serverstart
- Laadt LanceDB-vectortabel en parquet-bestanden in geheugen
- Scope: server lifetime

### Salesforce MCP-server

**`_token_store = build_token_store()`** (`salesforce/mcp_server.py`, regel ~45):
- `JsonFileTokenStore` of `AzureKeyVaultTokenStore` op basis van env var `SF_TOKEN_STORE`
- Persistence: `.salesforce_tokens.json` op disk (of Key Vault)

**`_session_ref_file: str = ".sf_session.json"`** (geciteerd in `shared/mcp_utils.py`):
- Bevat de UUID van de actieve sessie
- Persist over server-herstarts

**`_pending_states: set[str]`** (regel 49 in `salesforce/mcp_server.py`):
- CSRF state-tokens voor de OAuth-callback; in-memory, vluchtig

**`_repo_cache: dict[str, tuple[SalesforceRepository, str]]`** (`salesforce/mcp_router.py`, regel 29):
- Sleutel: `session_token`
- Waarde: `(SalesforceRepository, access_token)` tuple
- Wordt vernieuwd als de access_token is vervangen na refresh

### SmartSales MCP-server

**Session-token**: Persisteert als `session_id` in `.ss_session.json`. Bij serverherstart automatisch hersteld via `_ensure_session()`.

**Field cache**: `await repo.warm_field_cache()` bij sessie-aanmaak. In-memory, server lifetime. Vermijdt herhaalde metadata-aanroepen.

---

## 6. Tokenopslag en persistentie

| Bestand | Inhoud | Encryptie | Risico |
|---|---|---|---|
| `.token_cache.bin` | MSAL access + refresh tokens (JSON) | Geen | Plaintext op disk; hergebruikbaar bij ongeautoriseerde toegang |
| `.salesforce_tokens.json` | access_token, refresh_token, instance_url, expires_at | Optioneel (Fernet) | Standaard plaintext; `AzureKeyVaultTokenStore` als productie-alternatief |
| `.sf_session.json` | Actieve Salesforce sessie-UUID | Geen | Alleen een pointer; laag risico op zichzelf |
| `.ss_session.json` | SmartSales sessie-UUID | Geen | Idem |

---

## 7. Globale singletons en gedeelde staat in `main_ui.py`

```python
_orchestrator = None                   # PlanningOrchestrator-singleton
_sessions: dict[str, AgentSession] = {} # In-memory sessie-registry
_procs: list = []                      # Subproces-handles voor MCP-servers
_setup_result: dict = {}               # Tokens/URLs van sync setup
```

De `_orchestrator`-singleton deelt de drie subagent-instanties met alle gelijktijdige HTTP-requests. Dit is alleen veilig als `agent_framework`'s `Agent.run()` geen mutatieve state deelt buiten de `AgentSession`. De tokentellerst (`_input_tokens`, `_output_tokens`) op het `PlanningOrchestrator`-object worden gereset aan het begin van `run_sse()` maar zijn niet thread-safe bij gelijktijdige aanroepen — als twee coroutines gelijktijdig `run_sse()` uitvoeren, kunnen hun tokentellers mengen.

---

## 8. Geheugenlekkages en lifecycle-beheer

**Potentiële geheugenlekkages**:

1. **`_sessions`-dict**: Sessies worden nooit automatisch verwijderd. Bij langdurig gebruik groeien `AgentSession`-objecten (met volledige berichten-historiek) in het geheugen.

2. **`_repo_cache` (Graph)**: Elke unieke Bearer-token creëert een nieuwe `GraphRepository`-instantie. Tokens verlopen maar worden niet uit de cache verwijderd.

3. **`DocumentContextProvider` file cache**: `session.state["doc_context"]["files"]`-dictionary groeit cumulatief per sessie zonder vervalbeleid.

**Lifecycle-beheer voor MCP-serversubprocessen** (`main_ui.py`, regels 86–89):
```python
async with lifespan(app):
    yield
for proc in _procs:
    proc.terminate()
    proc.wait()
```
Subprocessen worden proper beëindigd bij afsluiting van de FastAPI-applicatie.

---

## 9. Context-propagatie in asyncio

De ContextVar-mechanisme is bijzonder relevant voor de RoutingTrace in een asyncio-context. In Python's asyncio erft elke coroutine de context van zijn aanroeper. `ContextVar.set()` creëert een kopie van de context in de huidige task. Mutaties op het object dat door de ContextVar wordt vastgehouden (de `RoutingTrace`-instantie zelf) zijn echter zichtbaar door alle coroutines die naar dezelfde instantie verwijzen, ongeacht context-kopieën.

Dit staat gedocumenteerd in de docstring van `routing_trace.py` (regels 58–64):
```
ContextVar.set() in a coroutine affects the current task's context copy.
All coroutines awaited (not spawned as new tasks) share that context, so
the tool closures called by agent_framework see the same RoutingTrace object.
If agent_framework internally uses asyncio.create_task(), the spawned tasks
still receive a copy that points to the SAME RoutingTrace instance, so
mutations from inside closures are always visible to the caller.
```

Dit is een correcte analyse: `ContextVar.set()` is per-task isolerend, maar mutaties op het object (via `.append()`) zijn object-level mutaties, niet context-level. Twee gelijktijdige `run_sse()`-aanroepen op dezelfde event loop zullen elk een aparte `RoutingTrace`-instantie aanmaken via `start_trace()`, waardoor ze geïsoleerd blijven.

---

## 10. Ontbrekende state-mechanismen

Op basis van de codebase ontbreken:

1. **Sessie-persistentie**: Herstarten van `main_ui.py` wist alle `AgentSession`-objecten en hun berichten-historiek. Er is geen Redis- of database-backed sessie-store.

2. **Sessieverval (TTL)**: Sessies groeien in geheugen zonder automatische opruiming.

3. **Cross-run geheugen voor de orchestrator**: De `PlanningOrchestrator` heeft geen geheugen over meerdere runs heen. Als een gebruiker vraagt "doe hetzelfde voor het volgende bedrijf", moet de planner de context opnieuw interpreteren uit de conversatiehistoriek in de `AgentSession`.

4. **Distributed state**: De `_sessions`-dict, `_repo_cache`s en singletons bestaan uitsluitend in het geheugen van één processen-instantie. Horizontale schaling van `main_ui.py` over meerdere instanties zonder gedeelde state is niet ondersteund.

5. **Auditrail voor state-wijzigingen**: Er is geen logging van sessie-aanmaak, sessie-verwijdering, of wijzigingen in `DocumentContextProvider`-state op INFO-niveau in de productiecode (enkel DEBUG-logging in `context.py`).
