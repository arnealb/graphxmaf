# Analysis 11 — Koppeling aan promotorcommentaar

Dit document koppelt elk van de 15 opmerkingen uit `scriptie_comments_met_context.txt` aan concrete codebase-bevindingen en formuleert per opmerking een aanbeveling voor revisie van de thesis.

---

## Opmerking 1 — Abstract: kwantitatieve resultaten toevoegen

**Commentaar**: "probeer misschien ook een quantitatief resultaat te vermelden"
**Betrekking op**: zin over "eerste resultaten tonen potentieel" (Abstract, p. 2)

### Beschikbare kwantitatieve data in de codebase

De MLflow-evaluatiestructuur in `eval/mlflow_eval.py` genereert de volgende aggregerende metrics per benchmark-run:
- `avg_llm_score`: gemiddelde antwoordkwaliteitsscore (1–5 schaal)
- `avg_routing_score`: gemiddelde routeringsscore (1–5)
- `avg_routing_precision` / `avg_routing_recall`
- `avg_latency_s`, `p95_latency_s`
- `avg_total_tokens`

De thesis vermeldt in hoofdstuk 7 reeds concrete scores (bijv. "GraphAgent 3,82 gemiddeld over 22 queries"). In het abstract is dit nog afwezig.

### Aanbeveling

Vul de abstract-zin aan met de meest representatieve metrics uit hoofdstuk 7, bij voorkeur: de gemiddelde `llm_score` van de OrchestratorAgent, de routeringsprecision en -recall, en de gemiddelde responstijd. Voorbeeld: "De OrchestratorAgent behaalde een gemiddelde correctheidsscore van X/5 op een testset van 88 queries, met een gemiddelde responstijd van Y seconden en een routeringsprecision van Z%."

### Status

Bewijs voor kwantitatieve data: aanwezig in `mlruns/`-directory (18 MLflow-runs zichtbaar in de git-status). Scores zijn beschikbaar uit eerder uitgevoerde benchmarks.

---

## Opmerking 2 — H1: Spellingscorrectie "bedrijfsomgeving"

**Commentaar**: "splitsing: bedrijfs-omgeving"
**Betrekking op**: deelvraag in §1.3 Onderzoeksvragen (p. 10)

### Analyse

Zuivere typografische correctie in het LaTeX-bestand. Geen codebase-impact.

### Aanbeveling

In het `.tex`-bestand: vervang "bedrijf-somgeving" door "bedrijfsomgeving" (zonder koppelteken, of correct afgebroken via `\-` hyphenation hint als de regelbreuk problematisch is).

### Status

Geen code-onderbouwing vereist; tekstuele correctie.

---

## Opmerking 3 — H1: Snelheid van uitvoering als deelvraag

**Commentaar**: "ook de snelheid van uitvoering als een deelvraag vermelden?"
**Betrekking op**: §1.3 Onderzoeksvragen (p. 10)

### Codebase-onderbouwing

Performantie is reeds gemeten in de evaluatie. `eval/mlflow_eval.py` (regel 356) logt `latency_s` per testgeval. De productiecode gebruikt `step_timeout=300.0` (`planning_orchestrator.py`, regel 543) en de Graph SDK-call-timeout is 30.0 seconden (`graph/repository.py`, `_graph_call()`). `eval/mlflow_tracing.py` biedt fasegranulaire latency (plan, execute, synthesis via `phase_timings`).

De OrchestratorAgent heeft een gemiddelde responstijd van 24,3 seconden (vermeld in §7.4.1 van de thesis), wat significant is voor enterprise gebruik.

### Aanbeveling

Voeg een extra deelvraag toe aan §1.3, bijv.: "In welke mate voldoet het systeem aan realistische responstijdvereisten voor enterprise search, en welke architecturale keuzes bepalen de latency?" Dit verankert de performantie-evaluatie in hoofdstuk 7 bij de onderzoeksvragen.

### Status

Kwantitatieve basis beschikbaar; architecturale onderbouwing aanwezig in analysis_07_schaalbaarheid.md.

---

## Opmerking 4 — H2: MCP-beperkingen en governance

**Commentaar**: "governance inclusief authenticatie/authorisatie?"
**Betrekking op**: §2.5 Model Context Protocol (p. 16) — "lost het niet automatisch alle uitdagingen rond beveiliging, toegangscontrole en governance op"

### Codebase-onderbouwing

MCP standaardiseert het transport via streamable HTTP maar niet de authenticatiemethode. Dit is aantoonbaar in de code:
- Graph MCP-server: eigen `RoutingMiddleware` (`graph/mcp_server.py`, regels 148–185) voor Bearer-tokencontrole; OBO-flow beschikbaar maar uitgecommentarieerd (regel 131–132)
- Salesforce MCP-server: eigen OAuth2-callback-routes (`/auth/salesforce/login`, `/auth/salesforce/callback`)
- SmartSales MCP-server: eigen client-credentials-stroom vanuit env-variabelen

Elke MCP-server implementeert zijn eigen authenticatie onafhankelijk. MCP zelf biedt geen unified auth-laag.

Governance-lacune: de orchestrator voert geen autorisatiecontrole uit op query-niveau. SmartSales gebruikt server-to-server auth (geen per-gebruiker toegangscontrole). Volledig geanalyseerd in `analysis_05_auth_governance.md`, §4 en §5.

### Aanbeveling

Breid de betrokken zin in §2.5 uit met: "Governance omvat in dit kader ook authenticatie en autorisatie: MCP-servers zijn zelf verantwoordelijk voor het valideren van inkomende tokens en het afdwingen van gebruikersrechten. Dit blijkt in de implementatie te leiden tot drie afzonderlijke authenticatie-implementaties, elk met eigen beveiligingsrisico's, in het bijzonder bij de server-to-server authenticatiestroom van SmartSales."

### Status

Volledig onderbouwd in code; zie ook `analysis_05_auth_governance.md`.

---

## Opmerking 5 — H3: Kwantificering van niet-functionele vereisten

**Commentaar**: "kan je deze quantitatief beschrijven? naast de qualitatieve beschrijving?"
**Betrekking op**: §3.5.2 Niet-functionele vereisten (p. 20) — vereiste betrouwbaarheid

### Codebase-onderbouwing

De evaluatiestructuur biedt kwantificeerbare proxies voor betrouwbaarheid:
- `llm_score >= 4` als maatstaf voor "correct en compleet" antwoord (1–5 schaal, `eval/score.py`)
- `routing_recall = 1.0` als maatstaf voor "geen gemist systeem" (via `mlflow_eval.py`, regels 341–342)
- `success = True` als binaire maatstaf voor foutloze uitvoering (regel 360)

De systemprompt van de synthesizer (`SYNTHESIS_SYSTEM_PROMPT`, regels 138–163 van `planning_orchestrator.py`) instrueert: "When information is unavailable, explicitly state which system was queried and that no data was found" — dit is een architecturale anti-hallucinatie-maatregel.

### Aanbeveling

Voeg bij §3.5.2 meetbare criteria toe: "Betrouwbaarheid wordt operationeel gedefinieerd als een gemiddelde antwoordkwaliteitsscore van minimaal 3,5/5 op de benchmarkset (gemeten via LLM-as-a-judge), een routeringsprecision en -recall van minimaal 0,85, en afwezigheid van hallucinaties over systeemgrenzen heen (geoperationaliseerd als: de synthesizer vermeldt expliciet het bronsysteem voor elk stuk informatie)."

### Status

Kwantificeerbare criteria beschikbaar vanuit evaluatiestructuur; see `eval/score.py` en `eval/mlflow_eval.py`.

---

## Opmerking 6 — H4: MCP-modulariteit meer in detail

**Commentaar**: "dit belangrijke aspect misschien in iets meer detail beschrijven?"
**Betrekking op**: §4.5 Verantwoording architecturale keuzes (p. 25) — MCP-based integratielaag

### Codebase-onderbouwing

Het MCP-modulariteitsmechanisme is concreet aantoonbaar in de code:

1. **Dynamische tool-registratie via YAML**: `graph/tools.yaml`, `salesforce/tools.yaml`, `smartsales/tools.yaml` zijn de enige source-of-truth voor tool-definities. Een domeinexpert kan tools toevoegen zonder agentcode te wijzigen.

2. **Inspect.Signature mechanisme** (`graph/mcp_router.py`, regels 45–54):
   ```python
   handler.__signature__ = inspect.Signature(sig_params)
   mcp.tool(name=tool_def["name"], description=tool_def.get("description", ""))(handler)
   ```
   FastMCP genereert het JSON Schema voor de LLM automatisch uit de Python-functiehandtekening.

3. **URL-configuratie vs. subproces** (`startup.py`, regels 133–135; `main_ui.py`, regels 187–208):
   ```python
   if _is_local_url(mcp_url):
       _procs.append(_start_graph_mcp_server(server_env, mcp_url))
   ```
   Overschakelen van lokale naar Azure Container Apps-deployment vereist enkel een URL-wijziging in `config.cfg`.

4. **Productie-URLs al aanwezig** in `config.cfg`:
   ```ini
   mcpServerUrl = https://graph-mcp.whitemushroom-38caf70a.swedencentral.azurecontainerapps.io/mcp
   ```

### Aanbeveling

Voeg in §4.5 een concrete beschrijving toe van het YAML-gebaseerde tool-registratiepatroon (met verwijzing naar de drie `tools.yaml`-bestanden), het `inspect.Signature`-mechanisme, en het URL-gebaseerde omschakelprincipe. Benadruk dat een domeinexpert tools kan toevoegen door enkel YAML te bewerken, zonder wijzigingen aan de orchestratielaag.

### Status

Volledig geanalyseerd in `analysis_04_mcp_toollaag.md`, §2 en §7.

---

## Opmerking 7 — H5: Contextbeheer koppelen aan uitbreidingen

**Commentaar**: "misschien hier de link maken met 'mogelijke uitbreidingen' en aangeven hoe je het zou aanpakken"
**Betrekking op**: §5.7 Beperkingen (p. 30) — beperkt contextbeheer

### Codebase-onderbouwing

**Huidige staat**:
- `DocumentContextProvider` (`graph/context.py`): injecteert bestandszoekcontext per sessie in de GraphAgent, maar uitsluitend voor de GraphAgent. Salesforce- en SmartSalesagents hebben geen equivalent.
- `AgentSession` (in-memory `_sessions`-dict in `main_ui.py`, regel 52): niet persistent; verloren bij herstart.
- De `PlanningOrchestrator` heeft geen gedeeld geheugen over runs.

**Concrete uitbreidingsmogelijkheden**:
1. `DocumentContextProvider`-equivalent voor Salesforce: cumulatief bijhouden van gevonden account-IDs voor vervolgvragen over dezelfde entiteit
2. Redis-backed `AgentSession`: sessie-persistentie over herstart heen
3. Gedeeld plan-geheugen: het laatste plan bewaren als context voor de volgende vraag (bijv. "doe hetzelfde voor het volgende bedrijf")

### Aanbeveling

Voeg in §5.7 een zin toe: "Een concrete verbetering zou bestaan uit het uitbreiden van het `DocumentContextProvider`-patroon — momenteel uitsluitend aanwezig bij de GraphAgent — naar de Salesforce- en SmartSalesagent. Dit zou toelaten om gevonden entiteit-IDs (account-IDs, locatie-UIDs) te bewaren over meerdere beurten, waardoor vervolgvragen zoals 'doe hetzelfde voor het volgende bedrijf' zonder herhaalzoekopdrachten kunnen worden beantwoord. Sessie-persistentie kan worden gerealiseerd via een gedistribueerde sleutel-waarde-opslag zoals Redis, ter vervanging van de huidige in-memory `_sessions`-dictionary."

### Status

Geanalyseerd in `analysis_09_state_context.md`, §4 en §10.

---

## Opmerking 8 — H6: Validatie testset door Easi-medewerker

**Commentaar**: "is er een validatie gebeurd door een medewerker van Easi? zo ja, best vermelden hier"
**Betrekking op**: §6.2.1 Samenstelling testset (p. 32)

### Codebase-onderbouwing

De testset (`eval/prompts/prompts.json`) bevat 88 queries (op basis van `BENCHMARK_PROMPTS: list[BenchmarkPrompt] = _load_prompts()` in `mlflow_eval.py`) met:
- AI-gegenereerde initiële queries, daarna handmatig geselecteerd en bijgesteld
- `expected_answer`-veld: beschrijving van wat een correct antwoord moet bevatten (domeinkennis vereist)
- `expected_agents`-veld: ground truth voor routeringsevaluatie

De `expected_answer`-velden vereisen kennis van de werkelijke data in de Easi-Microsoft 365/Salesforce/SmartSales-omgeving om te kunnen worden opgesteld. Externe validatie is inhoudelijk niet zichtbaar in de codebase.

### Aanbeveling

Verduidelijk in §6.2.1 de oorsprong van de `expected_answer`-velden: zijn deze gebaseerd op werkelijke queries die zijn uitgevoerd op de productiedata en waarvan het resultaat is gevalideerd? Vermeld indien van toepassing de betrokkenheid van een Easi-medewerker bij de inhoudelijke validatie. Zo niet, formuleer dit expliciet als beperking: de `expected_answer`-beschrijvingen zijn gebaseerd op de kennis van de onderzoeker over de datastructuren, niet op extern gevalideerde grondwaarheden.

### Status

Niet direct aantoonbaar vanuit de code; vereist aanvulling door de auteur.

---

## Opmerking 9 — H6: Wie geeft de scores (correctheid)

**Commentaar**: "wie geeft de scores: onafhankelijke testgebruikers?"
**Betrekking op**: §6.3 Evaluatie van correctheid (p. 33) — schaal 1–5

### Codebase-onderbouwing

De scores worden **volledig door een LLM-evaluator** toegekend, niet door menselijke beoordelaars. Dit staat concreet in `eval/score.py`:

```python
resp = await client.chat.completions.create(
    model=deployment,         # Azure OpenAI GPT-deployment
    messages=[
        {"role": "system", "content": _SYSTEM},
        {"role": "user",   "content": _USER_TMPL.format(...)},
    ],
    temperature=0,
    max_tokens=300,
)
```

De `_SYSTEM`-prompt instrueert: "You are a benchmark evaluator for a multi-agent AI system." Er zijn geen menselijke annotators betrokken.

### Aanbeveling

Maak dit expliciet in §6.3: "De correctheidsscores worden automatisch toegekend door een LLM-evaluator (GPT-4o via Azure OpenAI, `temperature=0`). De evaluator ontvangt per testgeval de vraag, het verwachte antwoord en het werkelijke antwoord en genereert een score (1–5) met motivatie. Menselijke validatie van een steekproef is niet uitgevoerd; dit vormt een beperking die in §7.5 verder wordt besproken."

### Status

Volledig gedocumenteerd in `eval/score.py`, `evaluate()`-functie, regels 64–94; en in `analysis_10_observability.md`, §6.

---

## Opmerking 10 — H6: Deelmetingen responstijd

**Commentaar**: "naast de volledige tijd, zijn ook de deeltijden interessant (om eventuele bottlenecks op te sporen)"
**Betrekking op**: §6.5.1 Evaluatie van de responstijd (p. 34) — end-to-end meting

### Codebase-onderbouwing

De per-fase latencymetingen zijn reeds geïmplementeerd maar optioneel:

**`eval/mlflow_tracing.py`** (regels 110, 157, 188):
```python
phase_timings["plan"]      = {"latency_s": round(elapsed, 3), ...}
phase_timings["steps"]     = [{"step_id": 1, "agent": "graph", "latency_s": 0.8, ...}]
phase_timings["synthesis"] = {"latency_s": round(elapsed, 3), ...}
```

Dit artifact (`phase_timings.json`) wordt als MLflow-artifact opgeslagen bij gebruik van de `--trace`-vlag (`eval/mlflow_eval.py`, regels 388–391).

Beschikbare deelmetingen:
- **Plan-latency**: planner LLM-aanroep
- **Per-stap latency**: per subagent (graph, salesforce, smartsales)
- **Synthese-latency**: synthesizer LLM-aanroep
- **Token-gebruik per fase**: input/output tokens per fase

De per-stap timing is beschikbaar op `started_at`/`ended_at`-niveau in de `RoutingTrace` (`AgentInvocation`-dataclass, `routing_trace.py`).

### Aanbeveling

Vermeld in §6.5.1: "Naast de end-to-end responstijd worden via het MLflow-tracing-mechanisme (`eval/mlflow_tracing.py`) ook per-fase tijden geregistreerd: de plannerlatency, de uitvoeringslatency per subagent, en de synthese-latency. Deze deelmetingen maken het mogelijk bottlenecks per fase te identificeren." Voeg in §7.4 een analyse toe van de faseverdeling.

### Status

Geïmplementeerd maar als optionele `--trace`-vlag; fase-timings zijn beschikbaar in MLflow artifacts.

---

## Opmerking 11 — H6: Schaalbaarheid bij simultane gebruikers

**Commentaar**: "ook rekening houden met simultane gebruikers: bij 100+ gelijktijdige gebruikers kan het trager worden, ook schaalbaarheid vermelden?"
**Betrekking op**: §6.5 Evaluatie van performantie en kost (p. 34)

### Codebase-onderbouwing

De huidige evaluatie (`eval/mlflow_eval.py`) is uitsluitend sequentieel (`asyncio.run(main())` met één query tegelijk). Er zijn geen concurrency-tests.

Architecturale beperkingen voor concurrente gebruikers (gedocumenteerd in `analysis_07_schaalbaarheid.md`):
1. `PlanningOrchestrator`-singleton gedeeld door alle HTTP-requests (`main_ui.py`, `_orchestrator = None`)
2. Azure OpenAI rate limits (TPM/RPM) cumuleren bij meerdere gelijktijdige queries
3. `_input_tokens`/`_output_tokens`-instantie-attributen niet thread-safe bij concurrentie
4. GraphRAG thread pool (`asyncio.to_thread()`) is begrensd
5. MCP-servers zijn horizontaal schaalbaar via Azure Container Apps (config reeds aanwezig)

### Aanbeveling

Voeg in §6.5 een paragraaf toe over schaalbaarheid: "De performantiemetingen zijn uitgevoerd voor één gelijktijdige gebruiker. Bij hogere concurrentie (10+ gelijktijdige gebruikers) spelen Azure OpenAI rate limits en de shared orchestrator-singleton een beperkende rol. Een concurrentiebenchmark — waarbij meerdere coroutines gelijktijdig `run_sse()` aanroepen — ontbreekt in de huidige evaluatieopzet en vormt een aanbeveling voor vervolgonderzoek." Koppel dit aan de schaalbaarheidsaanbevelingen in hoofdstuk 8.

### Status

Geanalyseerd in `analysis_07_schaalbaarheid.md`, §6 en §8.

---

## Opmerking 12 — H6: Dynamische databronnen koppelen aan verbeteringen

**Commentaar**: "idem, hier ook de link leggen naar 'mogelijke uitbreidingen' en vermelden hoe je zou aanpakken?"
**Betrekking op**: §6.6 Beperkingen van de evaluatie (p. 35) — dynamische databronnen

### Codebase-onderbouwing

De testset gebruikt live databronnen (Microsoft 365, Salesforce, SmartSales) die veranderen in de tijd. De `expected_answer`-velden in `eval/prompts/prompts.json` beschrijven wat het antwoord moet bevatten, maar de werkelijke data kan afwijken van het moment van opstellen.

Concrete aanpak beschikbaar in de code: de `auto_index_if_stale()`-functie (`startup.py`, regels 101–130) toont een mtime-gebaseerd patroon voor detectie van gewijzigde brondata.

### Aanbeveling

Voeg in §6.6 toe: "Een concrete mitigatie bestaat uit het gebruik van een vaste data-snapshot als testbron. Technisch is dit realiseerbaar via een separate Microsoft 365-testaccount met vaste testdata, een Salesforce sandbox-omgeving, en geseedde SmartSales-data. De `auto_index_if_stale()`-functie in de implementatie toont een bestaand patroon voor data-versioning op basis van bestandswijzigingstijden. Dit patroon kan worden uitgebreid naar een volledige benchmark-seed-procedure die de testdata op een deterministisch tijdstip bevriest."

### Status

Gedeeltelijk onderbouwd via `startup.py` `auto_index_if_stale()`; volledige seed-aanpak is architecturele aanbeveling.

---

## Opmerking 13 — H7: Correctheidsvalidatie door menselijke gebruikers

**Commentaar**: "correctheid valideren door onafhankelijke menselijke gebruikers?"
**Betrekking op**: §7.2 Evaluatie van correctheid (p. 38) — score GraphAgent 3,82

### Codebase-onderbouwing

Zelfde codebase-onderbouwing als opmerking 9. De `evaluate()`-functie (`eval/score.py`) is de enige evaluator; er is geen inter-rater agreement of menselijke validatie in de code aanwezig.

Bijkomend relevant: de scoring-prompt bevat een specifieke instructie ter voorkoming van vals-negatieve scores:
```python
"Important: if the response states 'no results found' or 'no recent email found' for a system, "
"that counts as the system being queried — do NOT treat it as missing coverage."
```
Dit is een bewuste keuze om de LLM-evaluator te sturen, maar introduceert ook evaluator-bias.

### Aanbeveling

Voeg in §7.2 een disclaimerparagraaf toe: "De correctheidsscores zijn uitsluitend bepaald door een LLM-evaluator (GPT-4o, `temperature=0`) zonder menselijke controle. Hoewel LLM-as-a-judge een schaalbare en nuanceerde evaluatiemethode is, is de betrouwbaarheid ervan afhankelijk van de kwaliteit van de evaluatorprompt en de capaciteiten van het gebruikte model. Een steekproefsgewijze validatie door onafhankelijke domeinexperts — bij voorkeur medewerkers van Easi die bekend zijn met de werkelijke data — zou de betrouwbaarheid van de scores significant versterken."

### Status

Geanalyseerd in `analysis_10_observability.md`, §6.

---

## Opmerking 14 — H7: Hoge responstijden, optimalisatie en grafiek

**Commentaar**: "vrij hoge waarden, is optimalisatie mogelijk? grafiek toevoegen en schaalbaarheid bespreken?"
**Betrekking op**: §7.4.1 Responstijden (p. 41) — OrchestratorAgent 24,3 seconden gemiddeld

### Codebase-onderbouwing

De hoge responstijden hebben meerdere aantoonbare oorzaken in de code:

1. **Serieel plan → execute → synthesize**: De drie fasen zijn sequentieel. De planner en synthesizer zijn extra LLM-aanroepen bovenop de subagent-calls.

2. **GraphRAG synchrone thread**: `asyncio.to_thread(_search_sync, query)` voert een synchrone HTTP-embedding + LanceDB-zoekactie + synchrone HTTP-completion uit, wat de subagent-latency significant verhoogt.

3. **Step timeout = 300 seconden**: Geen vroegtijdige timeout-instelling voor productiegebruik.

4. **Geen LLM-response caching**: Identieke vragen leiden tot nieuwe aanroepen.

**Concrete optimalisatiemogelijkheden (aantoonbaar in code)**:
- `temperature=0` in GraphRAG (`graphrag_searcher.py`, regel 118) → deterministische output → cacheable
- Azure OpenAI streaming kan worden ingezet voor snellere eerste-byte-latency
- De `parallel_ratio`-metriek (uit `compute_plan_stats()`) toont al hoeveel stappen parallel lopen; verbetering is mogelijk via betere planningsprompts die meer parallellisme stimuleren

### Aanbeveling

Voeg in §7.4.1 toe:
1. Een grafiek van responstijden per fase (plan/execute/synthesize) op basis van `phase_timings.json`
2. Een analyse van de hoofd-oorzaken: sequentiële planning + LLM-iteraties + GraphRAG thread-overhead
3. Een optimisatieparagraaf: "Potentiële verbeteringen zijn LLM-response caching voor deterministische queries, vervanging van de synchrone GraphRAG-client door `AsyncAzureOpenAI`, en verlaging van de step-timeout voor productiegebruik. De parallellisatiegraad (gemiddelde `parallel_ratio` uit de MLflow-evaluatie) geeft aan in welke mate het planningsgedrag van de orchestrator al gebruik maakt van parallelle uitvoering."

### Status

Architecturale analyse in `analysis_07_schaalbaarheid.md`, §6 en §9.

---

## Opmerking 15 — H7: Beperkingen LLM-evaluator uitwerken

**Commentaar**: "idem, ook bespreken hoe je beperkingen zou aanpakken"
**Betrekking op**: §7.5 Beperkingen evaluatie (p. 43) — subjectiviteit LLM-as-a-judge

### Codebase-onderbouwing

De LLM-evaluator-beperking is structureel. De `evaluate()`-functie (`eval/score.py`, regels 64–94):
- Gebruikt dezelfde Azure OpenAI-deployment als het te evalueren systeem (potentieel zelfevaluatiesituatie)
- `temperature=0` reduceert variabiliteit maar elimineert die niet volledig
- `max_tokens=300` begrenst de motivatie
- Antwoord getrunceerd op 4000 tekens (regel 84): lange antwoorden worden niet volledig geëvalueerd

Aanvullend: de routing-evaluator (`evaluate_routing()`, regels 149–186) en de antwoordkwaliteits-evaluator gebruiken dezelfde deployment, waardoor systemische biases identiek zijn voor beide metrics.

**Concrete aanpakken zichtbaar in literatuur/code**:
1. Inter-rater agreement: twee onafhankelijke LLM-instanties met gemiddelde score
2. Menselijke steekproef (zie opmerking 13)
3. Multiple evaluator models: bijv. GPT-4o + Claude 3.5 Sonnet

### Aanbeveling

Voeg in §7.5 toe: "De subjectiviteit van de LLM-evaluator kan worden gemitigeerd via drie complementaire maatregelen: (1) inter-rater reliability door twee onafhankelijke evaluatoraanroepen per testgeval te combineren via gemiddelde score; (2) steekproefsgewijze menselijke controle door domeinexperts om de kalibratie van de evaluatorprompt te valideren; en (3) gebruik van een evaluator-model van een andere leverancier (bijv. Anthropic Claude) om leverancier-specifieke biases te neutraliseren. Technisch is aanpak (1) direct implementeerbaar via een aanpassing van `eval/score.py` door de `evaluate()`-functie twee keer aan te roepen met verschillende random seeds en het gemiddelde te nemen."

### Status

Geanalyseerd in `analysis_10_observability.md`, §6; aanvullende evaluatorstructuur in `eval/score.py`.

---

## Samenvattingstabel

| Nr. | Hoofdstuk | Type | Code-onderbouwing | Urgentie |
|---|---|---|---|---|
| 1 | Abstract | Kwantitatief resultaat | MLflow-metrics beschikbaar in `mlruns/` | Hoog |
| 2 | §1.3 | Typografie | Geen | Laag |
| 3 | §1.3 | Extra deelvraag | `latency_s` in `mlflow_eval.py`; thesis §7.4 | Medium |
| 4 | §2.5 | MCP-governance uitbreiden | Drie onafhankelijke auth-implementaties in code | Hoog |
| 5 | §3.5.2 | Kwantificering NFR | `llm_score`, `routing_recall`, `success` metrics | Medium |
| 6 | §4.5 | MCP-modulariteit detail | YAML + `inspect.Signature` + URL-omschakelpatroon | Hoog |
| 7 | §5.7 | Contextbeheer uitbreidingen | `DocumentContextProvider` + `_sessions`-dict | Medium |
| 8 | §6.2.1 | Testset-validatie | `expected_answer` in `prompts.json` | Medium |
| 9 | §6.3 | Wie scoort | `eval/score.py` `evaluate()` = LLM-only | Hoog |
| 10 | §6.5.1 | Deelmetingen | `mlflow_tracing.py` `phase_timings` | Medium |
| 11 | §6.5 | Schaalbaarheid evaluatie | Sequentiële benchmark; singleton-architect | Hoog |
| 12 | §6.6 | Dynamische databronnen | `auto_index_if_stale()` als patroon | Medium |
| 13 | §7.2 | Menselijke validatie | Geen inter-rater agreement in code | Hoog |
| 14 | §7.4.1 | Optimalisatie + grafiek | GraphRAG thread; `parallel_ratio`; `phase_timings` | Hoog |
| 15 | §7.5 | LLM-evaluator beperkingen | Zelfde deployment; truncatie; geen inter-rater | Medium |
