# RAG Implementatie — Hoe het werkt, wat er fout ging, hoe het opgelost is

## 1. Waarom RAG?

De graph agent had al twee tools om bestanden te zoeken:
- `search_files` — KQL keyword search op bestandsnamen in OneDrive (geeft metadata terug, geen inhoud)
- `read_file` / `read_multiple_files` — laadt de volledige tekst van een bestand

Het probleem: dit "zoek + lees"-patroon is te fragiel voor policy/procedure vragen.

**Voorbeeld:**
> "What should I do if my car gets damaged on the way to work?"

Welk keyword stuur je naar OneDrive? `arbeidsreglement`? `schade`? Het document heet zo, maar de vraag niet. KQL vindt niks. En zelfs als het het juiste document vindt: je gooit het volledige document (12.000 chars) in de context terwijl je maar één paragraaf nodig hebt.

**RAG (Retrieval-Augmented Generation) lost dit op:**

```
Offline (index fase):
  documenten → opknippen in chunks → elke chunk embedden (numerieke vector) → opslaan

Online (query fase):
  vraag → embedden → zoek meest gelijkende chunks → geef die chunks aan LLM → antwoord
```

Embeddings zijn numerieke representaties van tekst waarbij semantisch gelijkende tekst dichtbij elkaar ligt in de vector ruimte. "Schade aan wagen" en "beschadiging voertuig" liggen dicht bij elkaar, ook al delen ze geen woorden.

---

## 2. Waarom Microsoft GraphRAG?

Het initiële plan was om de officiële Microsoft GraphRAG library te gebruiken. GraphRAG doet méér dan gewone vector RAG:

**Gewone vector RAG:**
```
vraag → embed → zoek chunks → LLM antwoord
```

**GraphRAG:**
```
documenten → chunk → entiteiten extraheren (personen, concepten, regels)
           → relaties leggen tussen entiteiten
           → entiteiten groeperen in "communities"
           → community summaries genereren

vraag → embed → relevante entiteiten/communities ophalen
      → context opbouwen via kennisgraaf
      → LLM antwoord op basis van die structuur
```

**Het voordeel van GraphRAG** is dat het relaties tussen entiteiten begrijpt die verspreid zijn over meerdere documenten. "Colruyt" en "SLA 4h" staan misschien in verschillende documenten — GraphRAG linkt ze via de graaf.

**De redenering om GraphRAG te kiezen:** het prototype werkt met entiteiten (klanten, leveranciers, medewerkers) die over meerdere systemen heen voorkomen. GraphRAG zou die entiteiten kunnen disambigueren.

---

## 3. Hoe de GraphRAG index gebouwd wordt

### 3.1 Stap 1: DOCX → TXT conversie

GraphRAG werkt met plain text bestanden. De originele DOCX bestanden staan in:
```
graph/graphrag/data_untouched/
  contracts/  collaboration_agreement_easi_colruyt.docx
              framework_agreement_easi_supplier1.docx
  HR/         employment_regulations_easi_group.docx
              expense_policy_easi_group.docx
              onboarding_guide_easi.docx
  procedures/ complaint_handling_procedure_easi.docx
```

`graph/graphrag_indexer.py` converteert ze naar TXT in `graph/graphrag/input/`:

```python
def _docx_to_text(path: Path) -> str:
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
```

### 3.2 Stap 2: GraphRAG index bouwen

```bash
python -m graphrag index --root graph/graphrag
```

GraphRAG leest de TXT bestanden en:
1. Knipt ze op in **text units** (chunks)
2. Stuurt elke chunk naar GPT-4o-mini om **entiteiten** en **relaties** te extraheren
3. Groepeert entiteiten in **communities** (Leiden-algoritme op de graaf)
4. Genereert **community summaries** via LLM

Het resultaat wordt opgeslagen in `graph/graphrag/output/`:
```
output/
  entities.parquet         — alle geëxtraheerde entiteiten (89 entiteiten)
  relationships.parquet    — relaties tussen entiteiten
  communities.parquet      — gegroepeerde entiteitsgroepen
  community_reports.parquet — LLM-gegenereerde samenvattingen per community
  text_units.parquet       — de originele tekstchunks (14 text units)
  documents.parquet        — brondocumenten met metadata
  lancedb/                 — vector embeddings (LanceDB vector store)
    text_unit_text.lance   — embeddings van elke text unit
    entity_description.lance — embeddings van entiteitsbeschrijvingen
    community_full_content.lance — embeddings van community summaries
```

### 3.3 Configuratie (graph/graphrag/settings.yaml)

Twee kritieke instellingen die fout waren bij setup:

```yaml
# FOUT:
model_provider: azure_openai   # bestaat niet in graphrag 3.x

# JUIST:
model_provider: azure          # graphrag source code: if self.model_provider != "azure"

# FOUT:
deployment_name: gpt-4o-mini   # veld bestaat niet bij provider azure

# JUIST:
azure_deployment_name: gpt-4o-mini  # alleen geldig als model_provider == "azure"
```

GraphRAG construeert intern de litellm model string als `{model_provider}/{model}`. LiteLLM verwacht `azure/gpt-4o-mini`, vandaar dat `model_provider: azure` de enige juiste waarde is.

---

## 4. Hoe querying werkt — wat er fout ging

### 4.1 Het originele plan: graphrag `local_search`

GraphRAG biedt een Python API voor queries:

```python
from graphrag.api.query import local_search

response, context = await local_search(
    config=config,
    entities=entities_df,
    communities=communities_df,
    community_reports=community_reports_df,
    text_units=text_units_df,
    relationships=relationships_df,
    community_level=2,
    query="Hoe veel krijg ik terugbetaald voor treinreizen?",
)
```

`local_search` doet intern:
1. Embed de query via text-embedding-3-small
2. Zoek relevante entiteiten en text units via LanceDB
3. **LLM call 1**: bouw context op door entity descriptions en community summaries samen te vatten
4. **LLM call 2**: genereer het finale antwoord op basis van die samengevatte context

Directe Python test → werkte correct en snel genoeg.

### 4.2 Probleem 1: asyncio event loop conflict

Wanneer `local_search` aangeroepen werd via de MCP server (FastAPI/Starlette), hing de call vast. De MCP server draait al op een asyncio event loop. `local_search` is zelf ook async en maakt intern nog meer async taken aan. Dit veroorzaakte een conflict waarbij de tweede LiteLLM call nooit kon afwerken.

**Diagnose uit de logs:**
```
[graphrag] Index loaded — 89 entities, 14 text units
LiteLLM completion() model= gpt-4o-mini ← eerste call slaagt
DELETE /mcp - 404 Not Found              ← MCP sessie verbroken
Step timed out after 120.0s
```

**Geprobeerde fix: `asyncio.to_thread`**

```python
def _run_search():
    return asyncio.run(local_search(...))

response, context = await asyncio.to_thread(_run_search)
```

Dit isoleert `local_search` in een aparte thread met een eigen event loop, zodat de MCP server's event loop niet geblokkeerd wordt. De fix was technisch correct — de event loop blokkeerde niet meer.

### 4.3 Probleem 2: Azure OpenAI rate limiting → oneindige retries

Na de `asyncio.to_thread` fix werkte de eerste LiteLLM call nog steeds, maar de tweede call (de synthesis call met een grote context) hing nu **288 seconden** voordat de timeout inging.

**Diagnose:** GraphRAG gebruikt LiteLLM met `exponential_backoff` retry configuratie:
```yaml
retry:
  type: exponential_backoff
```

De tweede LLM call stuurt een grote prompt (alle entity descriptions + community summaries als context). Dit triggert waarschijnlijk een Azure OpenAI rate limit (429) of een te groot request. LiteLLM begint dan te retrien met exponentieel groeiende wachttijden: 1s → 2s → 4s → 8s → 16s → 32s → 64s → 128s → ... totdat de orchestrator timeout (300s) erin trapt.

Conclusie: `local_search` is architectureel te zwaar voor een prototype dat snel moet antwoorden.

---

## 5. De oplossing: directe vector search

In plaats van graphrag's `local_search` met meerdere LLM calls, gaan we rechtstreeks naar de LanceDB vector store en doen één LLM call.

### 5.1 Waarom dit werkt

De graphrag index bevat in LanceDB de embeddings van alle text units (`text_unit_text.lance`). We kunnen die embeddings direct bevragen zonder de graphrag entiteiten/communities te doorlopen.

### 5.2 De nieuwe pipeline (graph/graphrag_searcher.py)

```
Query
  │
  ▼
[1] Embed de query
    Azure OpenAI text-embedding-3-small → 1536-dimensionale vector
  │
  ▼
[2] LanceDB vector search
    text_unit_text.lance → top-5 meest gelijkende text chunks (op cosine similarity)
  │
  ▼
[3] Text ophalen uit text_units.parquet
    Match op ID → haal de eigenlijke tekst op
    Voeg brondocumentnaam toe via documents.parquet
  │
  ▼
[4] Eén LLM call
    System: "Beantwoord enkel op basis van de context. Antwoord in de taal van de vraag."
    User: f"Context:\n{chunks}\n\nQuestion: {query}"
    → antwoord + lijst van brondocumenten
```

### 5.3 Resultaat

| Aanpak | LLM calls | Latency |
|--------|-----------|---------|
| graphrag `local_search` | 2-3 | >300s (timeout) |
| Directe vector search | 1 | ~5-10s |

Voorbeeldoutput:
```
Query:  "Hoe veel krijg ik terugbetaald als ik met de trein naar een klant reis?"
Answer: "Verplaatsingen per trein worden terugbetaald ten belope van 100% van de
         werkelijke kosten, op basis van een geldig ticket, e-ticket of factuur."
Sources: ["expense_policy_easi_group", "employment_regulations_easi_group"]
Tijd: 5.1s
```

### 5.4 Wat we verliezen vs. graphrag local_search

GraphRAG local_search is slimmer bij:
- Vragen die meerdere entiteiten overspannen via de kennisgraaf
- "Globale" vragen over een heel corpus ("wat zijn de hoofdthema's?")
- Cross-document entity linking

Voor onze use case (policy/procedure vragen uit gekende documenten) is dit niet nodig. De relevante informatie zit altijd rechtstreeks in de text chunks.

---

## 6. Hoe de volledige pipeline nu werkt (end-to-end)

```
Gebruiker vraagt: "How do I request access to Salesforce as a new employee?"
        │
        ▼
[PlanningOrchestrator — planning fase]
  LLM bepaalt: dit is een interne procedure vraag → graph agent → search_documents
        │
        ▼
[Graph Agent]
  Roept search_documents tool aan via MCPStreamableHTTPTool → port 8000
        │
        ▼
[Graph MCP Server — port 8000]
  mcp_router._search_documents()
  → graph.graphrag_searcher.search_documents(query)
        │
        ▼
[graphrag_searcher.search_documents]
  asyncio.to_thread(_search_sync, query)   ← aparte thread, eigen event loop
        │
        ▼
[_search_sync — in thread]
  1. AzureOpenAI.embeddings.create(model="text-embedding-3-small", input=query)
  2. lancedb_table.search(query_vector).limit(5).to_pandas()
  3. text_units[text_units.id.isin(chunk_ids)]
  4. AzureOpenAI.chat.completions.create(model="gpt-4o-mini", messages=[...])
        │
        ▼
[Resultaat]
  {"answer": "...", "sources": ["onboarding_guide_easi", ...]}
        │
        ▼
[Graph Agent]
  Geeft antwoord terug aan orchestrator
        │
        ▼
[PlanningOrchestrator — synthesis fase]
  LLM formuleert finale antwoord op basis van agent resultaten
        │
        ▼
[Gebruiker]
  "Een nieuwe werknemer kan toegang tot Salesforce aanvragen door naar
   servicedesk.easi.net te surfen en een IT-ticket in te dienen..."
```

Totale latency: ~8-12s voor een RAG vraag.

---

## 7. Relevante bestanden

| Bestand | Rol |
|---------|-----|
| `graph/graphrag_indexer.py` | DOCX → TXT conversie + `graphrag index` uitvoeren |
| `graph/graphrag_searcher.py` | Vector search + LLM call (de online query logica) |
| `graph/graphrag/data_untouched/` | Originele DOCX bestanden |
| `graph/graphrag/input/` | Geconverteerde TXT bestanden (input voor graphrag index) |
| `graph/graphrag/output/` | Index output: parquet bestanden + LanceDB vector store |
| `graph/graphrag/settings.yaml` | GraphRAG configuratie (model_provider, deployments) |
| `graph/graphrag/.env` | Azure OpenAI credentials voor graphrag |
| `graph/tools.yaml` | Tool definitie van `search_documents` |
| `graph/mcp_router.py` | Handler: `_search_documents` → roept graphrag_searcher aan |
| `agents/graph_agent.py` | Instructions: policy vragen → gebruik `search_documents` |
| `agents/planning_orchestrator.py` | Planner prompt: document vragen → graph agent |

---

## 8. Index updaten (na nieuwe/gewijzigde DOCX bestanden)

```powershell
# Wis oude index
Remove-Item -Recurse -Force graph/graphrag/output
Remove-Item -Recurse -Force graph/graphrag/cache

# Herindexeer (converteert DOCX + runt graphrag index)
python -m graph.graphrag_indexer
```

De MCP server laadt de index lazy (bij de eerste query). Na een herindexering moet de server herstart worden zodat de nieuwe index ingeladen wordt (`_index = None` reset).

---

## 9. Deployment naar Azure

De index (`graph/graphrag/output/`) moet ingebakken worden in de Docker image. De query code leest enkel lokale bestanden — er is geen runtime verbinding met graphrag nodig.

**Nog te doen:**
- Dockerfile aanpassen: `COPY graph/graphrag/output/ graph/graphrag/output/`
- Graph MCP Container App redeployen

De vector search zelf maakt wél runtime calls naar Azure OpenAI (voor embedding + LLM), maar die endpoint is al geconfigureerd via de bestaande Azure OpenAI resource.
