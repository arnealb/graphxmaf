# Analysis 03 — Gespecialiseerde agents

## 1. GraphAgent (Microsoft 365 / MS Graph)

### Doel en verantwoordelijkheid

De GraphAgent biedt toegang tot de Microsoft 365-omgeving van de geauthentiseerde gebruiker: e-mail, agenda, OneDrive-bestanden, contactpersonen en een GraphRAG-zoekmachine voor interne bedrijfsdocumenten.

### Bestanden en klassen

| Bestand | Inhoud |
|---|---|
| `agents/graph_agent.py` | Fabrieksfunctie `create_graph_agent(graph_mcp)` → `Agent` instantie |
| `graph/mcp_server.py` | FastMCP server op poort 8000 |
| `graph/mcp_router.py` | YAML-loader, `_DISPATCH`-dictionary, `register_graph_tools()` |
| `graph/tools.yaml` | 11 tool-definities |
| `graph/repository.py` | `GraphRepository` klasse (Microsoft Graph SDK wrapper) |
| `graph/models.py` | `Email`, `File`, `Contact`, `CalendarEvent`, `User`, `SearchResult`, `EmailAddress`, `Attendee` |
| `graph/interface.py` | `IGraphRepository` ABC (niet verder bestudeerd maar aanwezig) |
| `graph/context.py` | `DocumentContextProvider` (sessiecontextinjectie voor bestandstools) |
| `graph/graphrag_searcher.py` | `search_documents()` — vector RAG via LanceDB |
| `graph/graphrag_indexer.py` | `convert_all()`, `run_index()` — herindexering |
| `auth/token_credential.py` | `StaticTokenCredential` (wraps een Bearer token voor de Graph SDK) |

### Beschikbare tools (uit `graph/tools.yaml`)

| Tool | Methode | Beschrijving |
|---|---|---|
| `whoami` | `whoami` | Identiteit van de huidige M365-gebruiker |
| `findpeople` | `find_people` | Persoonsnaam → e-mailadressen (contacts + AD + mailbox) |
| `list_email` | `list_email` | 25 meest recente inbox-e-mails |
| `search_email` | `search_emails` | E-mails filteren op afzender, onderwerp, datumbereik |
| `read_email` | `read_email` | Volledige tekst van één e-mail (8.000 tekens max) |
| `search_files` | `search_files` | OneDrive-bestanden zoeken op trefwoord + filetype-filter |
| `read_file` | `read_file` | Tekstinhoud van één bestand (12.000 tekens max); .docx, .xlsx, plain text |
| `read_multiple_files` | `read_multiple_files` | Parallel meerdere bestanden lezen |
| `search_documents` | `search_documents` | GraphRAG vector-search over geïndexeerde OneDrive-documenten |
| `list_contacts` | `list_contacts` | Persoonlijke Outlook-contactpersonen (max 15) |
| `list_calendar` | `list_calendar` | 10 komende + 10 recente agenda-items |
| `search_calendar` | `search_events` | Agenda-items filteren op onderwerp, locatie, deelnemer, datumbereik |

### Hoe toolselectie binnen de agent werkt

De GraphAgent is een `Agent`-instantie met `tools=[graph_mcp]`. De `graph_mcp` is een `MCPStreamableHTTPTool` die alle 11 tools beschikbaar stelt. De agent (LLM) beslist welke tools te gebruiken op basis van:

1. De systemprompt in `create_graph_agent()` (regels 25–82 van `agents/graph_agent.py`):
   - **Document Workflow**: onderscheid tussen `search_documents` (beleid/procedures) en `search_files` (bestandsnamen)
   - **Strict Tool Selection Rules**: NOOIT speculatief tools aanroepen
   - **Person Resolution**: altijd `findpeople` aanroepen voor een naam
   - **Output**: altijd raw JSON teruggeven

2. De tool-beschrijvingen in `tools.yaml`: elk instrument bevat gedetailleerde gebruiksinstructies inclusief wanneer NIET te gebruiken.

### Specifieke implementatiedetails

**`find_people()`** (`graph/repository.py`, regels 249–267): Roept drie bronnen parallel aan:
- `_find_contacts()` — persoonlijke Outlook-contactpersonen (OData startswith)
- `_find_directory_users()` — Azure AD directory (ook title-case variant)
- `_find_mail_people()` — recente mailboxafzenders

**`search_documents()`** (`graph/mcp_router.py`, regel 59–61): Delegeert naar `graphrag_searcher.search_documents(query)`. Die voert uit: embed query (AzureOpenAI `text-embedding-3-small`) → LanceDB vector search top-5 → LLM-call (`gpt-4o-mini` standaard). Dit is een synchrone functie die via `asyncio.to_thread()` wordt uitgevoerd om de event loop niet te blokkeren.

**`get_file_text()`** (`graph/repository.py`, regels 504–553): Detecteert bestandsformaat op basis van magic bytes:
- ZIP-magic `PK\x03\x04` met `xl/` → xlsx (openpyxl)
- ZIP-magic zonder `xl/` → docx (python-docx)
- Anders → UTF-8/Latin-1 tekst

**HTML-stripping** (`graph/repository.py`, regels 58–72): De `_strip_html()` functie verwijdert CSS/JS-blokken en HTML-tags bij e-mailopvraging.

**Timeout**: Alle Graph SDK-calls gaan via `_graph_call(coro, timeout=30.0)` (regel 101 van `graph/repository.py`).

### Input/output formaat

- **Input**: taakbeschrijving als string vanuit de planner
- **Output**: Raw JSON van de tool-resultaten. De systemprompt instrueert: "Return the exact JSON object or array that the tool returned. No prose, no explanation." Uitzondering: `read_file` en `read_multiple_files` retourneren plain text.

### DocumentContextProvider

`graph/context.py` — `DocumentContextProvider(BaseContextProvider)`: Injecteert sessiecontext bij elke beurt:
- `[Session Context]` blok met huidig onderwerp, laatste zoekopdracht, gevonden bestandsnamen+IDs
- Bijgewerkt na elke `search_files`-aanroep
- Maakt herverwijzing naar eerder gevonden bestanden mogelijk zonder opnieuw te zoeken

### Beperkingen

- **Paginering**: `list_email` en `search_emails` retourneren max 25 items; geen paginering geïmplementeerd.
- **Kalender-attendee filter**: `search_events()` doet attendee-filtering client-side na server-side filtering (regel 791–802 van `repository.py`), wat het resultaat kan reduceren beneden 25.
- **Bestandstekst**: `read_file` is beperkt tot 12.000 tekens. Grote bestanden worden afgekapt.
- **E-mailtekst**: `read_email` is beperkt tot 8.000 tekens.
- **GraphRAG cold-start**: De index wordt bij serverstartup geladen (`graph/mcp_server.py`, regels 136–144) om een 5-seconden vertraging bij de eerste aanroep te voorkomen.

---

## 2. SalesforceAgent (CRM)

### Doel en verantwoordelijkheid

De SalesforceAgent biedt toegang tot Salesforce CRM-data: accounts, contactpersonen, leads, opportunities en cases via SOQL-queries.

### Bestanden en klassen

| Bestand | Inhoud |
|---|---|
| `agents/salesforce_agent.py` | Fabrieksfunctie `create_salesforce_agent(salesforce_mcp)` |
| `salesforce/mcp_server.py` | FastMCP op poort 8001, OAuth routes, sessieresolutie |
| `salesforce/mcp_router.py` | `register_salesforce_tools()`, repo-caching, methode-aliassen |
| `salesforce/tools.yaml` | 5 tool-definities |
| `salesforce/repository.py` | `SalesforceRepository` klasse, SOQL-bouwer |
| `salesforce/models.py` | Pydantic-modellen: `SalesforceAccount`, `SalesforceContact`, `SalesforceOpportunity`, `SalesforceCase`, `SalesforceLead` |
| `salesforce/auth.py` | OAuth helpers: Authorization Code Flow + JWT Bearer + refresh |
| `salesforce/token_store.py` | `JsonFileTokenStore`, `AzureKeyVaultTokenStore`, `build_token_store()` |

### Beschikbare tools (uit `salesforce/tools.yaml`)

| Tool | SOQL-object | Beschrijving |
|---|---|---|
| `find_accounts` | `Account` | Zoek accounts op naam/industrie/filters; extra_fields, not_null_fields, filters, order_by |
| `find_contacts` | `Contact` | Zoek contactpersonen op naam/email; inclusief Account.Name relatie |
| `find_leads` | `Lead` | Zoek leads; IsConverted filter ondersteund |
| `get_opportunities` | `Opportunity` | Opportunities; account_id, stage, min_amount, IsClosed filter |
| `get_cases` | `Case` | Cases; account_id, status, IsClosed filter |

### SOQL-beveiligingslaag

`SalesforceRepository` (`salesforce/repository.py`) bevat velden-allowlists per object:

```python
_ACCOUNT_FILTERABLE = frozenset({"Name", "Industry", "Website", ...})
_ACCOUNT_SELECTABLE: dict[str, str] = {"Phone": "phone", "Type": "type", ...}
_ACCOUNT_SORTABLE = frozenset({"Name", "Industry", ...})
_ACCOUNT_NUMERIC = frozenset({"NumberOfEmployees", "AnnualRevenue"})
```

Niet-toegestane velden worden stilzwijgend genegeerd. String-values worden ge-escaped via `_esc()` (single quotes vervangen). Dit beperkt het risico op SOQL-injectie vanuit LLM-gegenereerde parameters.

### Methodealias

`salesforce/mcp_router.py`, regel 22–24:
```python
_SF_METHOD_ALIASES = {
    "find_accounts": "get_accounts",
}
```
De tools.yaml gebruikt `find_accounts` als naam maar de repository-methode heet `get_accounts`.

### Repository-caching

`_repo_cache` (regel 29 van `salesforce/mcp_router.py`): Dictionary `session_token → (SalesforceRepository, access_token)`. Bij tokenvernieuwing wordt de cache vernieuwd.

### Modellen

`SalesforceAccount`, `SalesforceContact`, `SalesforceOpportunity`, `SalesforceCase`, `SalesforceLead` zijn Pydantic-modellen met basisvelden altijd aanwezig en optionele velden als `None` tenzij via `extra_fields` gevraagd.

### Sessieresolutie

Per tool-call: `extract_session_token(ctx)` → `_resolve_session(session_token)` → token-refresh indien vervallen → `SalesforceCredentials(access_token, instance_url)`.

### Beperkingen

- **LIMIT 25**: Alle SOQL-queries zijn standaard `LIMIT 25`. Er is geen paginering.
- **Geen schrijftoegang**: Alle tools zijn read-only (SELECT-queries).
- **Geen subqueries**: Relaties zijn alleen via `Account.Name` dotnotatie; geen nested SOQL.
- **Salesforce API versie**: Vastgezet op `v59.0` (`salesforce/repository.py`, regel 16).

---

## 3. SmartSalesAgent (locaties, catalogus, bestellingen)

### Doel en verantwoordelijkheid

De SmartSalesAgent biedt toegang tot het SmartSales-platform: locaties, catalogusitems, bestellingen, approbatiestatussen, en metadata over beschikbare velden.

### Bestanden en klassen

| Bestand | Inhoud |
|---|---|
| `agents/smartsales_agent.py` | Fabrieksfunctie `create_smartsales_agent(smartsales_mcp)` |
| `smartsales/mcp_server.py` | FastMCP op poort 8002, auto-auth bij startup |
| `smartsales/mcp_router.py` | `register_smartsales_tools()` |
| `smartsales/tools.yaml` | 20+ tool-definities |
| `smartsales/repository.py` | SmartSales API-client |
| `smartsales/models.py` | Datamodellen |
| `smartsales/auth.py` | `authenticate_smartsales()`, `authenticate_from_env()` |
| `smartsales/token_store.py` | Analoog aan Salesforce token_store |

### Beschikbare tools (uit `smartsales/tools.yaml`)

**Locaties**:
| Tool | Beschrijving |
|---|---|
| `get_location` | Ophalen van één locatie op UID |
| `list_locations` | Query met q/s/p/d/nextPageToken/skipResultSize parameters |
| `list_displayable_fields` | Beschikbare velden voor locatielijstweergave |
| `list_queryable_fields` | Filterable velden voor `q`-parameter |
| `list_sortable_fields` | Sorteerbare velden |

**Catalogus**:
| Tool | Beschrijving |
|---|---|
| `get_catalog_item` | Ophalen van één catalogusitem op UID |
| `get_catalog_group` | Ophalen van één catalogusgroep op UID |
| `list_catalog_items` | Query catalogusitems |
| `list_catalog_displayable_fields` | Beschikbare velden voor catalogusweergave |
| `list_catalog_queryable_fields` | Filterable velden |
| `list_catalog_sortable_fields` | Sorteerbare velden |

**Bestellingen**:
| Tool | Beschrijving |
|---|---|
| `get_order` | Ophalen van één bestelling op UID |
| `list_orders` | Query bestellingen met q/s/p/nextPageToken |
| `get_order_configuration` | Globale bestelconfiguratie (kortingsregels, handtekening, enz.) |
| `list_approbation_statuses` | Approbatiestatussen (goedkeuringsworkflow) |
| `get_approbation_status` | Één approbatiestatus op UID |
| `list_order_displayable_fields` | Displaybare velden voor bestellingen |
| `list_order_queryable_fields` | Filterable velden voor bestellingen |
| `list_order_sortable_fields` | Sorteerbare velden voor bestellingen |

### Queryformaat

Het SmartSales-specifieke `q`-parameter is een JSON-string:
```json
{"name":"contains:Carrefour","country":"eq:Belgium"}
```
Ondersteunde operators: `eq`, `neq`, `contains`, `ncontains`, `startswith`, `range:start,end`, `gt`, `gte`, `lt`, `lte`, `empty`, `nempty`.

De `p`-parameter (projectie) bepaalt het detailniveau: `"simple"` (standaard) geeft hoofdvelden, `"full"` geeft alle velden inclusief attributen.

### Authenticatie

SmartSales gebruikt geen browser-OAuth. Bij serverstart (of bij verlopen token) roept `_ensure_session()` (`smartsales/mcp_server.py`, regels 46–67) de `authenticate_from_env()` functie aan die een client credentials-achtige stroom uitvoert met env-variabelen `GRANT_TYPE`, `CODE_SMARTSALES`, `CLIENT_ID_SMARTSALES`, `CLIENT_SECRET_SMARTSALES`.

### Field cache

`smartsales/mcp_server.py`, regel 84: `await repo.warm_field_cache()` wordt bij sessie-aanmaak aangeroepen. De SmartSales repository laadt beschikbare veldmetadata in het geheugen om herhaalde metadata-aanroepen te vermijden.

### Beperkingen

- **Geen directe orderfiltering op naam**: Bestellingen kunnen niet direct op klantnaam worden gefilterd. Er is een twee-staps patroon vereist: eerst locatie-UID ophalen via `list_locations`, dan gebruiken in `list_orders` met `customerUid`-filter. De tools.yaml beschrijft dit expliciet (regel 357–359).
- **Paginering**: Expliciet via `nextPageToken`; de agent is geïnstrueerd niet automatisch te pagineren.
- **Beperkt resultaatformaat**: De `p`-parameter bepaalt hoeveel data terugkomt; de standaard `"simple"` kan onvoldoende zijn voor gedetailleerde queries.

---

## 4. Vergelijking van de drie agents

| Eigenschap | GraphAgent | SalesforceAgent | SmartSalesAgent |
|---|---|---|---|
| Aantal tools | 11 | 5 | ~20 |
| Authenticatie | MSAL auth code flow + OBO | OAuth2 Auth Code Flow | Client credentials (env vars) |
| Zoekparadigma | SDK + GraphRAG vector | SOQL-queries | SmartSales-native q/s/p |
| Schrijftoegang | Nee | Nee | Nee |
| Sessiestatus | Via Bearer token | Via sessieFUID + token_store | Via sessieFUID + token_store |
| Contextprovider | DocumentContextProvider | Geen | Geen |
| Max resultaten | 25 (email/bestanden) | 25 (LIMIT) | Paginering via nextPageToken |
| Stateful | DocumentContextProvider per sessie | Nee | Nee (veldcache per serverstart) |
| Domeinspecifieke beveiliging | Veldtruncatie (8K/12K chars) | Velden-allowlist, SOQL-escape | Projection levels |
