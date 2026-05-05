# GraphRAG Implementation — Handoff Document

> Gegenereerd: 2026-05-05
> Branch: `graph-rag-implementation`

---

## Overzicht

GraphRAG is een semantische zoeklaag die intern bedrijfsdocumenten (DOCX-bestanden) indexeert
tot een kennisgraaf met vectorembeddings, en op query-tijd via vector-RAG antwoorden genereert.
Het is één van de tools van de **GraphAgent** binnen het bredere multi-agent systeem.

---

## Bestandsstructuur

```
graphxmaf/
├── startup.py                          # Startup helpers: auth, auto-index, MCP server launch
│
├── graph/
│   ├── graphrag_indexer.py             # DOCX→TXT conversie + graphrag index pipeline
│   ├── graphrag_searcher.py            # Vector RAG query engine (embed→search→LLM)
│   ├── mcp_server.py                   # FastMCP server op port 8000, laadt index bij opstart
│   ├── mcp_router.py                   # Tool-dispatch: _search_documents → graphrag_searcher
│   ├── tools.yaml                      # Tool-definities (naam, description, params)
│   ├── context.py                      # DocumentContextProvider: session-bestand tracking
│   ├── repository.py                   # MS Graph API client (emails, files, calendar)
│   ├── models.py                       # Pydantic modellen voor Graph API responses
│   │
│   └── graphrag/                       # GraphRAG root directory
│       ├── .env                        # API keys (GRAPHRAG_API_KEY, etc.)
│       ├── settings.yaml               # Pipeline config (chunking, embedding, LanceDB)
│       ├── data_untouched/             # Bronbestanden (DOCX) — nooit wijzigen
│       │   ├── contracts/              # 5 contracten (NDA, SLA, frameworks, …)
│       │   ├── HR/                     # 7 HR-policies (car, leave, remote work, …)
│       │   └── procedures/             # 8 procedures (incident, security, procurement, …)
│       ├── input/                      # Gegenereerde TXT-bestanden (door indexer aangemaakt)
│       ├── output/                     # Pipeline-artefacten (parquet + LanceDB)
│       │   ├── documents.parquet       # Document-metadata (titel, id)
│       │   ├── text_units.parquet      # Tekstchunks (id, text, document_id)
│       │   ├── entities.parquet        # Geëxtraheerde entiteiten
│       │   ├── relationships.parquet   # Relaties tussen entiteiten
│       │   ├── communities.parquet     # Cluster-groepen van entiteiten
│       │   ├── community_reports.parquet # LLM-samenvattingen per cluster
│       │   └── lancedb/               # Vectordatabase
│       │       ├── text_unit_text/    # Embeddings van tekstchunks
│       │       ├── entity_description/
│       │       └── community_full_content/
│       ├── cache/                      # Pipeline-cache (JSON)
│       └── logs/                       # Pipeline-logbestanden
│
└── agents/
    ├── graph_agent.py                  # GraphAgent: instructions + tool-selectieregels
    └── planning_orchestrator.py        # PlanningOrchestrator: plan→DAG→synthesize
```

---

## Architectuur & Communicatieflow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              Gebruiker (UI/eval)                              │
└──────────────────────────────────┬───────────────────────────────────────────┘
                                   │ user query (tekst)
                                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         PlanningOrchestrator                                  │
│                                                                               │
│  Fase 1 ── PlannerAgent (LLM, geen tools)                                    │
│    • Ontvangt: user query + beschrijving van beschikbare agents               │
│    • Geeft terug: JSON execution plan                                         │
│      {steps: [{id, agent, task, depends_on}], synthesis: "..."}              │
│    • Documentvragen:                                                          │
│      TYPE A (policy/semantisch) → graph, task: "Use search_documents to …"   │
│      TYPE B (bestandsnaam/type) → graph, task: "Find file called …"          │
│                                                                               │
│  Fase 2 ── DAG executie (parallel binnen waves)                              │
│    • Topologische sortering van steps op basis van depends_on                │
│    • Elke wave: asyncio.gather(*stappen)                                      │
│    • Timeout: 300s per step                                                   │
│    • _enrich_task: injecteert output van afhankelijke stappen in task        │
│                                                                               │
│  Fase 3 ── SynthesizerAgent (LLM, geen tools)                                │
│    • Ontvangt: query + plan + alle step-resultaten                            │
│    • Geeft terug: eindantwoord voor de gebruiker                              │
└──────────┬───────────────────────────────────────────────────────────────────┘
           │ agent.run(task)
           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              GraphAgent                                       │
│  (Agent-framework, AzureOpenAI gpt-4o / gpt-4o-mini)                         │
│                                                                               │
│  Instructions sturen tool-keuze:                                              │
│  • policy/HR/contract/procedure → search_documents eerst                     │
│  • bestandsnaam/type → search_files                                           │
│  • bestand al in session context → direct file ID gebruiken                  │
│  • DocumentContextProvider injecteert [Session Context] blok per turn        │
│                                                                               │
│  Tools: MCPStreamableHTTPTool → http://localhost:8000/mcp                    │
└──────────┬───────────────────────────────────────────────────────────────────┘
           │ MCP HTTP (Streamable HTTP / SSE)
           │ Authorization: Bearer <session_token>
           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    Graph MCP Server  (port 8000)                              │
│                    graph/mcp_server.py                                        │
│                                                                               │
│  RoutingMiddleware:                                                           │
│  • /.well-known/* → OAuth metadata endpoints                                 │
│  • /authorize → proxy naar Azure AD authorize                                │
│  • /token → proxy naar Azure AD token + inject client_secret                 │
│  • /mcp → vereist Bearer token, anders 401                                   │
│                                                                               │
│  Startup:                                                                     │
│  • register_graph_tools(mcp, azure_settings, extract_session_token)          │
│  • _get_index() → pre-load GraphRAG index (vermijdt 5s cold-start SSE drop)  │
└──────────┬───────────────────────────────────────────────────────────────────┘
           │ tool call: search_documents(query="…")
           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    mcp_router.py — _DISPATCH                                  │
│                                                                               │
│  _search_documents(repo, query) →                                            │
│      from graph.graphrag_searcher import search_documents                    │
│      return await search_documents(query)                                    │
│                                                                               │
│  (repo = GraphRepository, token via extract_session_token)                   │
│  (repo wordt NIET gebruikt door graphrag_searcher — eigen OpenAI client)     │
└──────────┬───────────────────────────────────────────────────────────────────┘
           │ async → thread
           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    graphrag_searcher.py                                       │
│                                                                               │
│  search_documents(query):                                                     │
│    asyncio.to_thread(_search_sync, query)   ← runs in thread pool            │
│                                                                               │
│  _search_sync(query):                                                         │
│    1. _get_index()  → lazy-load (of al pre-loaded bij startup)               │
│       • text_units.parquet  → pd.DataFrame                                   │
│       • documents.parquet   → pd.DataFrame                                   │
│       • LanceDB open_table("text_unit_text")                                 │
│                                                                               │
│    2. Azure OpenAI embeddings.create(model="text-embedding-3-small")         │
│       → query_vector (list[float])                                            │
│                                                                               │
│    3. lancedb.search(query_vector).limit(5).to_pandas()                      │
│       → top-5 meest gelijkende tekstchunks (op basis van chunk-id)           │
│                                                                               │
│    4. text_units[id in chunk_ids] → chunk teksten ophalen                    │
│       documents → doc_id_to_title mapping                                    │
│       context = "[DocumentTitel]\n{tekst}\n\n---\n\n…"                       │
│                                                                               │
│    5. Azure OpenAI chat.completions.create(gpt-4o-mini, temp=0)             │
│       system: "Answer using only context, same language as question"         │
│       user:   "Context:\n{context}\n\nQuestion: {query}"                     │
│                                                                               │
│    6. Return {"answer": "…", "sources": ["policy1", "contract2"]}            │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Indexing Pipeline

### Wanneer wordt er geïndexeerd?

`startup.py → auto_index_if_stale(graphrag_root)` wordt aangeroepen bij elke start van `main_ui.py` of eval-scripts.

**Logica:**
```
data_untouched/**/*.docx nieuwer dan output/documents.parquet?
├── Nee → Index is actueel, skip
└── Ja  → Re-index:
           graphrag_indexer.convert_all()   # DOCX → TXT
           graphrag_indexer.run_index()      # graphrag CLI pipeline
```

### DOCX → TXT conversie (`graphrag_indexer.convert_all`)

- Leest DOCX-bestanden uit `data_untouched/` (recursief)
- Extraheert paragrafen + tabelrijen (python-docx)
- Schrijft TXT-bestanden naar `input/`

### GraphRAG Index pipeline (`graphrag_indexer.run_index`)

```
python -m graphrag index --root graph/graphrag
```

Configuratie in `settings.yaml`:

| Parameter | Waarde |
|-----------|--------|
| Chunking | 1200 tokens, 100 overlap |
| Embedding model | `text-embedding-3-small` (Azure OpenAI) |
| LLM voor extraction | `gpt-4o-mini` (Azure OpenAI) |
| Entity types | organization, person, geo, event |
| Vectordatabase | LanceDB (output/lancedb/) |
| Claims extraction | uitgeschakeld |
| Output format | Parquet + LanceDB |

**Pipeline-stappen:**
1. Chunks aanmaken (token-based, met overlap)
2. Embeddings genereren per chunk
3. Entiteiten extraheren via LLM
4. Relaties tussen entiteiten extraheren
5. Community-clustering (max 10 entiteiten/cluster)
6. Community-rapporten genereren (LLM-samenvatting)
7. Alles opslaan: parquet + LanceDB

---

## Query Engine (graphrag_searcher.py)

### GraphRAG: alleen als indexeer-tool

De splitsing is fundamenteel: **GraphRAG doet alleen het indexeren, niet het opzoeken.**

```
GraphRAG library rol:
  ✅ Indexeren  → python -m graphrag index ...
                  - Chunks aanmaken
                  - Embeddings genereren → LanceDB
                  - Entiteiten + relaties extraheren
                  - Communities bouwen + samenvatten
                  → Output: parquet-bestanden + LanceDB vectordatabase

  ❌ Opzoeken   → graphrag local_search / global_search / drift_search
                  → NIET gebruikt

Eigen implementatie rol:
  ✅ Opzoeken   → graphrag_searcher.py
                  - Laadt de door GraphRAG gebouwde LanceDB-tabel
                  - Voert zelf een vector-zoekopdracht uit
                  - Doet één LLM-call voor synthese
```

GraphRAG bouwt dus de kennisgraaf en de vectorstore — dat is het waardevolle werk dat
GraphRAG doet (entity extraction, community clustering, relaties). Die output wordt
vervolgens door **onze eigen code** direct aangesproken, zonder de GraphRAG query-laag.

### Waarom de GraphRAG query-engines niet gebruiken?

De GraphRAG library biedt drie query-modi: `local_search`, `global_search`, `drift_search`.
Elk van deze doet intern **meerdere LLM-calls** per query:

- `local_search` — haalt relevante entiteiten + communities op, stuurt die als context
  naar het LLM, soms met retry-loops bij rate limits. Typisch 3–5 LLM-calls per query.
- `global_search` — aggregeert over álle community-rapporten in meerdere waves.
  Kan tientallen LLM-calls kosten voor grote indexes.
- `drift_search` — experimentele hybride variant, nog meer calls.

**Het concrete probleem:** de Graph MCP server communiceert via **Streamable HTTP / SSE**.
Azure SSE-verbindingen vallen weg als er meer dan ~5 seconden geen bytes worden gestuurd.
Bij `local_search` (meerdere LLM-calls achter elkaar) zit er al snel een stiltepauze van
> 5s tussen het binnenkomen van de tool-call en het terugsturen van het resultaat.
Gevolg: de verbinding wordt verbroken vóór het antwoord terugkomt.

**De oplossing:** eigen vector-RAG in `graphrag_searcher.py`:
- Laad de LanceDB-tabel die GraphRAG heeft aangemaakt (`text_unit_text`)
- Embed de query zelf (1 API-call naar Azure OpenAI embeddings)
- Doe een vector-zoekopdracht in LanceDB → top-5 chunks (geen LLM nodig)
- Stuur die chunks als context naar het LLM → 1 LLM-call voor het eindantwoord

**Totaal: 2 API-calls** (embedding + chat) in plaats van 3–5+. Snel genoeg om binnen
de SSE timeout te blijven.

### Index pre-loading

In `mcp_server.py`:
```python
# Pre-load bij server-opstart
from graph.graphrag_searcher import _get_index
_get_index()
```

Hierdoor laadt de index (parquet + LanceDB) bij het opstarten van de MCP server,
zodat de eerste echte tool-call geen 5-seconde vertraging heeft.

---

## Brondata

**20 bestanden in 3 categorieën:**

| Categorie | Bestanden |
|-----------|-----------|
| Contracten (5) | Data Processing Agreement (Colruyt), Framework Agreement, Maintenance Contract, NDA Template, SLA Agreement (Easi Colruyt) |
| HR Policies (7) | Company Car Policy, Health Insurance Guide, Leave Policy, Offboarding Guide, Performance Review, Remote Work Policy, Training Policy |
| Procedures (8) | Business Continuity Plan, Change Management, Data Breach, Incident Management, Invoice Approval, IT Security, Procurement, Supplier Code of Conduct |

---

## Authenticatie & Token-flow

```
GraphAgent
  └── MCPStreamableHTTPTool
        └── Authorization: Bearer <session_token>
              ↓
        Graph MCP Server (port 8000)
              ↓ extract_session_token(ctx)
        mcp_router._DISPATCH["search_documents"](repo, query)
              ↓
        graphrag_searcher.search_documents(query)
              ↓ (eigen AzureOpenAI client met GRAPHRAG_API_KEY)
        Azure OpenAI (embedding + chat)
```

> **Let op:** `graphrag_searcher` gebruikt NIET de token van de gebruiker.
> Het gebruikt zijn eigen `GRAPHRAG_API_KEY` uit `graph/graphrag/.env`.
> Dit is een service-level API key voor het doorzoeken van de gedeelde kennisgraaf.

De `repo` (GraphRepository + gebruikerstoken) wordt wél meegegeven aan `_search_documents`
maar niet doorgegeven aan de searcher — alleen voor consistentie met het dispatch-patroon.

---

## Omgevingsvariabelen

### `graph/graphrag/.env`
```
GRAPHRAG_API_KEY=<Azure OpenAI key>
GRAPHRAG_API_BASE=https://global-search-agent.cognitiveservices.azure.com/
GRAPHRAG_CHAT_DEPLOYMENT=gpt-4o-mini
GRAPHRAG_EMBEDDING_DEPLOYMENT=text-embedding-3-small
```

> Op Azure Container Apps worden deze variabelen op containerniveau gezet.
> `load_dotenv(..., override=False)` zorgt dat .env dan wordt genegeerd.

### `config.cfg` — `[azure]`
- `tenantId`, `clientId`, `clientSecret`, `graphUserScopes`
- Gebruikt door mcp_server.py voor OAuth2 + OBO token-uitwisseling

---

## Planning Orchestrator — document query routing

In `PLAN_SYSTEM_PROMPT` staan expliciete regels voor documentvragen:

### TYPE A — Semantische/policy query
> Gebruiker vraagt WAT iets is, wat een regel is, of hoe iets werkt.

Voorbeelden:
- "Wat is de onkostenpolicy?"
- "Hoe vraag ik verlof aan?"
- "Wat zijn de supportvoorwaarden bij client X?"

**Routing:** → `graph` agent, task: `"Use search_documents to find the answer."`

### TYPE B — Bestand-op-naam query
> Gebruiker zoekt een specifiek bestand op naam of type.

Voorbeelden:
- "Zoek een document genaamd 'agenda'"
- "Toon mijn Excel-bestanden"

**Routing:** → `graph` agent, task zonder expliciete vermelding van `search_documents`
(agent kiest zelf `search_files`)

### Kritieke uitzondering
SmartSales API-vragen (filters, catalog, orders) gaan NOOIT naar graph/search_documents,
ook al bevatten ze woorden als "configuratie" of "procedure". → altijd naar `smartsales` agent.

---

## DocumentContextProvider (`graph/context.py`)

Injecteert een `[Session Context]` blok in elke GraphAgent turn:

```
[Session Context]
Current topic: onkostenpolicy
Last search: expense reimbursement
Files found:
  - company_car_policy_easi (id: abc123)
  - leave_policy_easi (id: def456)
```

- Houdt bij welke bestanden in de sessie zijn gevonden
- Laat de agent vage follow-up vragen oplossen zonder opnieuw te zoeken
- Geen hergebruik van file-IDs nodig voor `search_documents` (werkt op tekst)

---

## Voorbeeld: volledig query-lifecycle

**Vraag:** *"Wat zijn de vereisten voor een bedrijfswagen?"*

```
1. PlannerAgent
   • Herkent TYPE A (policy-vraag)
   • Plan: 1 stap, agent=graph
   • task: "Use search_documents to find company car requirements."

2. GraphAgent.run(task)
   • Herkent policy-instructie in task
   • Roept tool aan: search_documents(query="company car requirements")

3. MCP Server (port 8000)
   • Valideert Bearer token
   • Dispatcht naar _search_documents(repo, query="company car requirements")

4. graphrag_searcher._search_sync("company car requirements")
   • Index al geladen (pre-load bij startup)
   • Embed query → Azure OpenAI text-embedding-3-small
   • LanceDB search → top-5 chunks
   • Beste chunks: uit company_car_policy_easi.txt
   • Context opgebouwd: "[company_car_policy_easi]\n{chunk1}\n\n---\n\n{chunk2}"
   • LLM call: gpt-4o-mini, temperature=0
   • Return: {
       "answer": "De vereisten voor een bedrijfswagen zijn...",
       "sources": ["company_car_policy_easi"]
     }

5. GraphAgent
   • Geeft tool-resultaat terug als JSON

6. SynthesizerAgent
   • Eén stap, combineert resultaat
   • Eindantwoord naar gebruiker
```

---

## Bekende beperkingen & designbeslissingen

| Aspect | Keuze | Reden |
|--------|-------|-------|
| GraphRAG gebruik | Alleen voor indexeren (CLI pipeline) | Levert chunks, embeddings, entities, LanceDB — het dure kennisgraaf-werk |
| Query-modus | Eigen vector-RAG op GraphRAG's LanceDB-output | GraphRAG query-engines doen 3–5+ LLM-calls; SSE-verbinding valt weg na ~5s stilte |
| Top-K chunks | 5 | Balans tussen context en LLM-kosten |
| Pre-loading | Ja, bij MCP server startup | Eerste tool-call mag geen 5s duren (SSE drop) |
| Auto-indexing | Timestamp-vergelijking bij startup | Simpel, robuust, geen aparte watcher nodig |
| Index scope | Gedeelde kennisgraaf (service-level key) | Documenten zijn bedrijfsbreed, niet per-gebruiker |
| Graph-artefacten (entities, relations, communities) | Aangemaakt maar NIET gebruikt bij query | Worden wel opgeslagen voor mogelijke toekomstige graph-traversal |

---

## Schaalbaarheid & toekomstige richting: Azure AI Search

### Het fundamentele probleem met de huidige aanpak op schaal

De huidige GraphRAG-aanpak werkt goed voor een **kleine, stabiele, handmatig geselecteerde** documentcollectie (de 20 DOCX-bestanden in `data_untouched/`). Maar hij heeft twee structurele beperkingen:

**1. Handmatig beheer verplicht**
Bestanden moeten manueel gedownload en in `data_untouched/` geplaatst worden. Er is geen automatische synchronisatie met OneDrive of SharePoint. Nieuwe bestanden worden niet opgepikt tenzij iemand ze toevoegt.

**2. Geen incrementele indexering**
GraphRAG's pipeline is een globale batch-operatie. Community detection en entity relationship mapping herberekenen hoe alle entiteiten over *alle* documenten samenhangen. Voeg je 1 nieuw document toe, dan moet de hele index opnieuw gebouwd worden — ook de bestaande 100 documenten. Dat schaalt niet voor een volledige OneDrive.

### Wanneer is Azure AI Search de betere keuze?

Als het doel is **de volledige OneDrive doorzoekbaar maken** (honderden tot duizenden bestanden, constant wijzigend), dan is Azure AI Search de logische volgende stap.

```
OneDrive (volledig — alle bestanden, alle mappen)
      ↓ (Azure AI Search SharePoint/OneDrive indexer connector)
      ↓  - crawlt via Microsoft Graph API (zelfde API die al gebruikt wordt)
      ↓  - delta-check elke X uur: alleen nieuwe/gewijzigde bestanden herindexeren
      ↓  - ingebouwde text extraction: DOCX, PDF, XLSX, PPTX, TXT
Azure AI Search index
      ↓ (vector search + semantic ranking — L2 reranking)
search_documents(query) → Azure AI Search SDK
      ↓
GraphAgent — zelfde interface, andere backend
```

De rest van de architectuur (GraphAgent, MCP server, planning orchestrator) hoeft niet te veranderen. Alleen `graphrag_searcher.py` wordt vervangen door een Azure AI Search client.

### Vergelijking

| | GraphRAG (huidig) | Azure AI Search |
|---|---|---|
| Bronconnector | Lokale bestanden (handmatig) | Native SharePoint/OneDrive connector |
| Indexering | Batch, alles opnieuw | Incrementeel (delta via Graph API) |
| Nieuwe bestanden | Handmatig kopiëren + volledige herindexering | Automatisch opgepikt |
| Ondersteunde formaten | DOCX (eigen conversie) | DOCX, PDF, XLSX, PPTX, TXT, … ingebouwd |
| Vector search | LanceDB (zelfgebouwd) | Ingebouwd (HNSW) |
| Semantische ranking | Nee | Ja |
| Knowledge graph | Ja (entities, relaties, communities) | Nee |
| Cross-document relaties | Ja (GraphRAG's sterkste punt) | Nee (per-chunk similarity) |
| Schaalbaarheid | Klein, stabiel corpus | Volledige OneDrive / SharePoint tenant |
| Kosten | Azure OpenAI calls bij indexeren | Azure AI Search resource (SKU-based) |

### Wat je verliest bij de overstap

De kennisgraaf-features van GraphRAG verdwijnen: cross-document entity relaties en community summaries. GraphRAG kan verbanden leggen die niet letterlijk in één chunk staan — "wat is de relatie tussen clausule X in contract A en policy Y in het HR-handboek" — puur op basis van geëxtraheerde entiteiten en hun relaties. Azure AI Search zoekt per chunk op vector-gelijkenis, niet op semantische grafiekstructuur.

**Maar:** voor de meeste praktische use cases — "wat zegt ons beleid over X?", "zoek iets op in mijn OneDrive" — is vector similarity + semantic ranking voldoende, en weegt de automatische OneDrive-synchronisatie zwaarder dan de graph-features.

### Conclusie

| Use case | Aanbevolen aanpak |
|---|---|
| Klein, stabiel corpus (< 50 docs), diepere relaties tussen docs | GraphRAG (huidig) |
| Volledige OneDrive doorzoekbaar maken, dynamisch groeiend | Azure AI Search + SharePoint connector |

---

## Document update workflow (productie)

De gebouwde index (`graph/graphrag/output/`) wordt bij Docker build ingebakken in het image.
Er is geen mechanisme om de index in een draaiende container te vernieuwen.

**Workflow bij documentwijzigingen:**

```
1. Voeg/wijzig DOCX-bestanden in graph/graphrag/data_untouched/

2. Herindexeer lokaal:
   python -c "from graph.graphrag_indexer import convert_all, run_index; convert_all(); run_index()"

3. Rebuild Docker image (pikt nieuwe output/ automatisch op):
   docker build -f Dockerfile.graph -t graph-mcp .

4. Herdeploy naar Azure Container Apps (of docker-compose up --build)
```

**Waarom dit geen probleem is voor de huidige use case:**

Het corpus (20 HR/contract/procedure-documenten) is stabiel en wijzigt zelden.
Een image rebuild + redeploy kost ~5 minuten en is een volkomen acceptabele operationele handeling.

**Wanneer dit wél een probleem wordt:**

- Documenten wijzigen wekelijks of vaker
- Niet-developers moeten documenten kunnen toevoegen zonder engineer-interventie
- Het corpus groeit naar honderden bestanden

In dat geval is de oplossing: de index uit het image halen en in **Azure Blob Storage** plaatsen.
De container downloadt de index bij startup via de Blob URI. Herindexeren = nieuwe `output/` uploaden
naar Blob + container restart, zonder image rebuild. Zie ook de sectie *Schaalbaarheid & toekomstige richting*.

---

## Starten / debuggen

```bash
# Start alles (indexeert auto als stale)
python main_ui.py

# Handmatig indexeren
python -c "from graph.graphrag_indexer import convert_all, run_index; convert_all(); run_index()"

# MCP server los draaien (voor debugging)
python -m graph.mcp_server

# MLflow evaluatie
python eval/mlflow_eval.py --version v1
mlflow ui   # → http://localhost:5000
```

---

## MCP Ports overzicht

| Service | Port | Module |
|---------|------|--------|
| Graph (incl. GraphRAG) | 8000 | `graph.mcp_server` |
| Salesforce | 8001 | `salesforce.mcp_server` |
| SmartSales | 8002 | `smartsales.mcp_server` |
| Dev UI | 8080 | `main_ui.py` |
