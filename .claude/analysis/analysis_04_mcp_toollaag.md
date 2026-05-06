# Analysis 04 — MCP-gebaseerde toollaag

## 1. Waar MCP-servers gedefinieerd worden

Elke domeinmodule heeft een eigen `mcp_server.py`:

| Bestand | FastMCP-instantie | Poort | Host |
|---|---|---|---|
| `graph/mcp_server.py` | `mcp = FastMCP("graph", port=8000, host="0.0.0.0")` | 8000 | 0.0.0.0 |
| `salesforce/mcp_server.py` | `mcp = FastMCP("salesforce", port=8001, host="0.0.0.0")` | 8001 | 0.0.0.0 |
| `smartsales/mcp_server.py` | `mcp = FastMCP("smartsales", port=8002, host="0.0.0.0")` | 8002 | 0.0.0.0 |

Alle drie servers worden als subprocessen gestart via `startup.py` (`_start_graph_mcp_server()`, `_start_salesforce_mcp_server()`, `_start_smartsales_mcp_server()`, regels 165–174 van `startup.py`). Ze draaien als `python -m graph.mcp_server`, `python -m salesforce.mcp_server` en `python -m smartsales.mcp_server`.

De productie-configuratie in `config.cfg` wijst naar Azure Container Apps:
```ini
mcpServerUrl = https://graph-mcp.whitemushroom-38caf70a.swedencentral.azurecontainerapps.io/mcp
# Salesforce
mcpServerUrl = https://salesforce-mcp.whitemushroom-38caf70a.swedencentral.azurecontainerapps.io/mcp
# SmartSales
mcpServerUrl = https://smartsales-mcp.whitemushroom-38caf70a.swedencentral.azurecontainerapps.io/mcp
```

---

## 2. Hoe tools geregistreerd worden (mcp_router.py-patroon)

Het registratiepatroon is identiek voor alle drie modules. Het kernmechanisme zit in `_register_one()` (aanwezig in `graph/mcp_router.py` regels 145–185 en `salesforce/mcp_router.py` regels 54–90).

### Stap 1: YAML-laden
```python
def _load_tools(path: str = "graph/tools.yaml") -> list[dict]:
    with open(path) as f:
        return yaml.safe_load(f)
```

### Stap 2: Dynamische handler-constructie
Voor elke tool-definitie in de YAML wordt een `async def handler(ctx: Context, **kwargs)` aangemaakt via een closure. De handler:
1. Extraheert het Bearer-token uit de `Authorization`-header via `extract_session_token(ctx)` of de OBO-flow
2. Verkrijgt een repo-instantie (met caching op token)
3. Dispatcht naar de juiste functie via `_DISPATCH`-dictionary (Graph) of via `getattr(repo, method)` (Salesforce/SmartSales)

### Stap 3: Signatuurbouw via `inspect.Signature`
```python
sig_params = [
    inspect.Parameter("ctx", ..., annotation=Context),
]
for p in params:
    py_type = _TYPE_MAP.get(p.get("type", "str"), str)
    default = p["default"] if "default" in p else (None if "None" in p.get("type","") else inspect.Parameter.empty)
    sig_params.append(inspect.Parameter(p["name"], ..., annotation=py_type, default=default))

handler.__signature__ = inspect.Signature(sig_params)
handler.__name__ = tool_def["name"]
```

FastMCP gebruikt Python-introspectie op de `__signature__` om het JSON Schema voor de tool te genereren. Door de handtekening dynamisch op te bouwen, wordt de YAML de enige bron van waarheid voor parameternamen en -types.

### Stap 4: Registratie bij FastMCP
```python
mcp.tool(name=tool_def["name"], description=tool_def.get("description", ""))(handler)
```

De `mcp.tool()`-decorator registreert de handler bij de FastMCP-instantie.

---

## 3. Tools.yaml structuur

Elke tools.yaml bevat een lijst van tool-definities. Voorbeeld uit `graph/tools.yaml`:

```yaml
- name: findpeople
  description: >
    Resolve a person's name to one or more email addresses.
    ...
    ALWAYS call this before search_email or search_calendar when the user refers
    to a person by name ...
  method: find_people
  params:
    - name: name
      type: str
```

Velden per tool-definitie:

| Veld | Verplicht | Beschrijving |
|---|---|---|
| `name` | Ja | Toolnaam zoals zichtbaar voor de LLM |
| `description` | Ja | Uitgebreide beschrijving; stelt ook wanneer NIET te gebruiken |
| `method` | Ja | Python-methode/dispatch-sleutel |
| `params` | Nee | Lijst van parameterdefinities |

Per parameter:

| Veld | Beschrijving |
|---|---|
| `name` | Parameternaam |
| `type` | Python-type als string: `"str"`, `"str \| None"`, `"int"`, `"int \| None"`, `"list[str] \| None"`, `"dict[str, str] \| None"`, `"bool \| None"` |
| `default` | Standaardwaarde (optioneel) |
| `description` | Aanvullende beschrijving (Salesforce tools.yaml gebruikt dit per parameter) |

**Type-mapping** (`_TYPE_MAP` dictionaries in elk mcp_router.py):
```python
_TYPE_MAP: dict[str, type] = {
    "str":       str,
    "str | None": str | None,
    "int":       int,
    "int | None": int | None,
    # Salesforce voegt toe:
    "list[str] | None": list[str] | None,
    "dict[str, str] | None": dict[str, str] | None,
}
```

---

## 4. Hoe agents communiceren met MCP-tools (MCPStreamableHTTPTool)

De agents communiceren via `MCPStreamableHTTPTool` (uit `agent_framework`). Dit object is de enige tool die aan elke agent wordt meegegeven:

```python
# main_ui.py, regels 68-74
graph_mcp = MCPStreamableHTTPTool(name="graph", url=d["graph_url"], http_client=graph_http)
graph_agent = create_graph_agent(graph_mcp=graph_mcp)
```

```python
# agents/graph_agent.py, regel 80
tools=[graph_mcp]
```

De `MCPStreamableHTTPTool`:
1. Verbindt bij de eerste aanroep via HTTP met de MCP-server op het opgegeven URL
2. Haalt de lijst beschikbare tools op via het MCP-protocol
3. Presenteert elke tool als een callable aan het `agent_framework`
4. Bij een toolaanroep: stuurt een MCP-request via de streamable HTTP-transport
5. Geeft het resultaat terug aan de agent

De HTTP-client wordt meegegeven bij constructie en bevat de `Authorization: Bearer <token>` header:
```python
graph_http = httpx.AsyncClient(headers={"Authorization": f"Bearer {d['graph_token']}"})
```

---

## 5. Welke MCP-server bij welke databron hoort

| MCP-server | Poort (lokaal) | Databron | Authenticatiemechanisme |
|---|---|---|---|
| `graph/mcp_server.py` | 8000 | Microsoft Graph (MS365) | MSAL auth code + OBO-token-uitwisseling |
| `salesforce/mcp_server.py` | 8001 | Salesforce CRM | OAuth2 Authorization Code Flow |
| `smartsales/mcp_server.py` | 8002 | SmartSales proxy API | Client credentials via env vars |

De orchestrator/UI-server draait op poort 8090 (`main_ui.py`). De DevUI van de oorspronkelijke opzet was poort 8080, maar is vervangen door de FastAPI-server op 8090.

---

## 6. Hoe MCP agentlogica loskoppelt van systeemintegratie

**Vóór MCP**: De agentcode zou direct API-clients instantiëren, tokens beheren en API-aanroepen doen. Dit koppelt de LLM-logica aan de implementatiedetails van elke API.

**Met MCP**: De agent ontvangt enkel een `MCPStreamableHTTPTool` met een URL. De agent weet niet:
- Welke authenticatiemethode de backend gebruikt
- Of de backend een Graph SDK, REST API of een proxy is
- Op welke server of in welke taal de tools draaien

Dit maakt het mogelijk om:
1. Een MCP-server te vervangen zonder de agentcode te wijzigen
2. De MCP-server te deployen op Azure Container Apps zonder lokale poort te openen
3. Meerdere versies van een MCP-server naast elkaar te draaien
4. De tools.yaml aan te passen (beschrijvingen bijwerken, parameters toevoegen) zonder de agent te hercompileren

**Concreet bewijs in de codebase**: `config.cfg` bevat de Azure Container Apps-URLs als standaard `mcpServerUrl`. De `main_ui.py` controleert via `_is_local_url()` of een subproces gestart moet worden of dat de externe URL direct gebruikt wordt.

---

## 7. Waarom MCP belangrijk is voor modulariteit, onderhoudbaarheid en source-of-truth

**Modulariteit**: Elk domein heeft zijn eigen Dockerfile (`Dockerfile.graph`, `Dockerfile.salesforce`, `Dockerfile.smartsales`) en kan onafhankelijk worden gebuild en geschaald. De `docker-compose.yml` definieert de services als losse containers.

**Source-of-truth in tools.yaml**:
- Toolnamen en beschrijvingen voor de LLM
- Parameternames en -types voor FastMCP's JSON Schema-generatie
- Alles op één plek: een domain expert kan tools toevoegen/aanpassen door enkel YAML te bewerken

**Onderhoudbaarheid**: Wanneer de Salesforce API een nieuw endpoint krijgt, hoeft enkel `salesforce/tools.yaml` en `salesforce/repository.py` te worden bijgewerkt; de orchestrator- en agentcode blijft onveranderd.

---

## 8. Wat MCP NIET oplost

### Authenticatie en autorisatie
MCP standaardiseert het transport maar niet de authenticatiemethode. Elke MCP-server implementeert zijn eigen auth:
- Graph: OAuth2 PKCE/Authorization Code Flow + On-Behalf-Of token-uitwisseling (eigen implementatie in `graph/mcp_server.py`)
- Salesforce: OAuth2 Authorization Code Flow (eigen implementatie in `salesforce/mcp_server.py`)
- SmartSales: Client credentials (eigen implementatie in `smartsales/mcp_server.py`)

De `extract_session_token()` functie (`shared/mcp_utils.py`) extraheert het Bearer-token uit de `Authorization`-header, maar de semantiek van dat token (welke gebruiker, welke rechten) verschilt per MCP-server.

### Rate limits
Er is geen rate limiting geïmplementeerd op de MCP-servers of in de repositories. Als meerdere gelijktijdige gebruikers dezelfde agent aanroepen, kunnen API-rate limits van Microsoft Graph of Salesforce worden bereikt. Niet waarneembaar in de code.

### Datamodellen en validatie
MCP garandeert geen consistent datamodel. Elke MCP-server geeft zijn eigen formaat terug (Pydantic-modellen omgezet naar dict/JSON). De synthesizer moet omgaan met structurele verschillen tussen Graph-resultaten (JSON-arrays), Salesforce-resultaten (Pydantic-dict) en SmartSales-resultaten.

### Foutafhandeling
MCP-protocolfouten worden door `agent_framework` afgehandeld, maar domeinspecifieke fouten (API-timeout, lege resultaten, authenticatiefout) worden per MCP-server afzonderlijk behandeld. Er is geen centraal foutbehandelingsmechanisme.

### Governance en audittrail
MCP biedt geen ingebouwd audittrail van tool-aanroepen. De `RoutingTrace` in de projectcode is een eigen implementatie die tool-aanroepen logt na de uitvoering.

---

## 9. FastMCP specifics: dynamische handler-generatie

FastMCP (`mcp.server.fastmcp`) is een Python-library die een MCP-server bouwt boven op een ASGI-framework (Starlette/Uvicorn). De key insight in de implementatie is dat FastMCP introspectie gebruikt op de Python-functie-signatuur om het JSON Schema voor de tool te genereren.

Door `handler.__signature__` expliciet in te stellen via `inspect.Signature()` met de juiste parameterannotaties, "gelooft" FastMCP dat de handler die parameters accepteert en genereert het juiste schema:

```python
handler.__signature__ = inspect.Signature(sig_params)
handler.__name__ = tool_def["name"]
mcp.tool(name=tool_def["name"], description=tool_def.get("description", ""))(handler)
```

Dit mechanisme maakt het mogelijk om 11 (Graph), 5 (Salesforce) en ~20 (SmartSales) tools te registreren via een generieke lus in plaats van hardcoded functies per tool. Het vermijdt ook dat er code gegenereerd moet worden.

De `RoutingMiddleware` (`graph/mcp_server.py`, regels 148–185) voegt authenticatiecontrole toe vóór het `/mcp`-pad: requests zonder `Authorization: Bearer`-header ontvangen een `401 Unauthorized`.
