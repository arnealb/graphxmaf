# Analysis 06 — Beslissingslogica en routing

## 1. Hoe het systeem beslist welke agent aangesproken wordt

De agentselectie in het systeem is uitsluitend LLM-gebaseerd. Er is geen rule-based classifier, geen keyword-router en geen statistisch model voor agentselectie. Het proces verloopt als volgt:

**Stap 1 — Agent-beschrijving samenstellen** (`_available_agents_description()`, regels 357–383 van `agents/planning_orchestrator.py`):

```python
agents.append(
    "graph (Microsoft 365: emails, calendar events, OneDrive files, "
    "personal Outlook contacts / address book — use for communication history, "
    "documents, and scheduling related to a person or company. "
    "Also use for internal company documents stored in OneDrive such as HR policies, "
    "expense rules, onboarding guides, contracts, and procedure documents — "
    "i.e. any question about internal rules, processes, or company documentation)"
)
agents.append(
    "salesforce (CRM: accounts, CRM contacts, leads, opportunities, cases — "
    "use for commercial relationship data, deal pipeline, and support history ...)"
)
agents.append(
    "smartsales (locations, catalog items — use for physical presence, "
    "store or site information, and product catalog related to a company)"
)
```

**Stap 2 — Plan genereren** (`_create_plan()`, regels 289–324): De planner ontvangt de prompt `"Available agents: <beschrijving>\n\nUser query: <vraag>"` en produceert een JSON-plan met per stap een `"agent"`-veld.

**Stap 3 — Validatie** (`_validate_plan()`, regels 326–355): Alleen structurele en naamvalidatie. Er is geen inhoudelijke controle of de geselecteerde agent ook de juiste is.

De routing-richtlijnen in de `PLAN_SYSTEM_PROMPT` bevatten uitgebreide voorbeelden en regels:
- TYPE A vs TYPE B documentqueries (regels 85–95)
- SmartSales NOOIT naar graph (regels 99–110)
- 360°-queries met alle agents (regels 112–136)
- "registered location" = SmartSales, niet Salesforce (regels 128–136)

---

## 2. Hoe betrouwbaar/voorspelbaar de beslissing is

**Gebaseerd op de evaluatiedata in de codebase** (`eval/prompts/prompts.json`):

De prompts in de testset worden geclassificeerd met `expected_agents`:
- Eenvoudige single-agent queries (bv. `"graph"` voor e-mail, `"salesforce"` voor accounts) werken betrouwbaar voor de meeste gevallen
- Cross-system queries met `["graph", "salesforce"]` of alle drie zijn gevoeliger voor mis-routing
- Harde gevallen zoals "SmartSales API-velden" werden expliciet toegevoegd aan de PLAN_SYSTEM_PROMPT nadat mis-routing werd geobserveerd (de uitgebreide SmartSales-sectie in regels 99–110 van de systemprompt)

**Risicofactoren**:

1. **Ambigue terminologie**: Woorden als "configuratie", "velden", "informatie over locatie" kunnen de planner misleiden. De systemprompt probeert dit te adresseren maar kan niet alle randgevallen dekken.
2. **LLM-variabiliteit**: Zelfs bij identieke invoer kan de planner bij verschillende runs andere agents kiezen. Er is geen temperatuurinstelling zichtbaar in de code.
3. **Promptkwetsbaarheid**: De planning is kwetsbaar voor instructies in de gebruikersvraag zelf die de planner kunnen beïnvloeden ("gebruik alleen salesforce", "doe dit in twee stappen").
4. **Taal-mismatch**: De PLAN_SYSTEM_PROMPT is in het Engels, maar gebruikersvragen kunnen in het Nederlands zijn. De LLM handelt dit doorgaans correct af, maar edge cases zijn mogelijk.

---

## 3. Logging/routing traces

`agents/routing_trace.py` implementeert de `RoutingTrace`:

```python
@dataclass
class RoutingTrace:
    user_query: str
    plan: Optional[dict] = None
    invoked_agents: list[AgentInvocation] = field(default_factory=list)
```

Per stap wordt een `AgentInvocation` opgeslagen:

```python
@dataclass
class AgentInvocation:
    agent: str          # welke agent
    order: int          # stap-ID (uit plan)
    input: str          # volledige taakstring
    started_at: str     # ISO-8601 UTC
    ended_at: str       # ISO-8601 UTC
    success: bool
    error: Optional[str]
    llm_turns: int      # LLM-iteraties in de subagent
    tool_calls: list    # namen van aangeroepen tools
```

De trace wordt:
- **Aangemaakt** via `start_trace(user_query)` in `main_ui.py` (regel 137) of `eval/mlflow_eval.py` (regel 147)
- **Bijgewerkt** door `_execute_step()` in `planning_orchestrator.py` (regels 492–506) na elke stap
- **Opgeslagen** bij MLflow evaluatie als `routing_trace.json` artifact
- **Geschreven** naar `eval/routing_traces.jsonl` in de benchmarkscripts

---

## 4. Hoe routing geëvalueerd wordt (eval scripts, routing_precision/recall)

**`eval/score.py` — `evaluate_routing()`** (regels 149–186):

Een LLM-evaluator (`AsyncAzureOpenAI`) ontvangt:
- De gebruikersvraag
- De daadwerkelijk aangeroepen agents (uit de routing trace)
- De verwachte agents (uit `expected_agents` in `prompts.json`)
- Beschrijvingen van alle agents

De evaluator scoort op een schaal van 1–5:
- 5: Exact de verwachte agents, geen overbodige calls
- 4: Correct met kleine inefficiënties
- 3: Correct maar met overbodige of ontbrekende calls
- 2: Deels correct
- 1: Fout gerouteerd

**`eval/mlflow_eval.py` — Precision/Recall** (regels 336–342):

```python
invoked = {inv["agent"] for inv in result["routing_trace"].get("invoked_agents", [])}
expected = set(prompt.expected_agents)
routing_precision = len(invoked & expected) / len(invoked) if invoked else 0.0
routing_recall    = len(invoked & expected) / len(expected) if expected else 0.0
```

- **Precision**: Van de aangeroepen agents, welk deel was verwacht (no over-routing)
- **Recall**: Van de verwachte agents, welk deel werd daadwerkelijk aangeroepen (no under-routing)

Deze metrics worden gelogd in MLflow als `routing_precision` en `routing_recall` per testgeval.

---

## 5. Waar under-routing, over-routing en mis-routing kunnen ontstaan

### Under-routing (ontbrekende agent)
**Oorzaak**: De planner herkent niet dat een vraag meerdere systemen vereist.
**Voorbeeld**: "Welke bedrijven heb ik onlangs gemaild en hebben wij een deal mee?" → planner gebruikt alleen `graph` en slaat Salesforce over.
**Signaal in code**: In `prompts.json` zijn er meerdere "implicit-cross-system"-prompts (regels 63–100) die specifiek testen of het systeem beide agents aanroept.

### Over-routing (overbodige agent)
**Oorzaak**: De planner voegt agents toe "voor de zekerheid" of interpreteert een 360°-querypatroon te ruim.
**Voorbeeld**: "Wat zijn mijn laatste e-mails?" → planner voegt Salesforce en SmartSales toe vanwege de 360°-hint in de systemprompt.
**Gevolg**: Hogere latency, meer tokengebruik, mogelijk verwarrende syntheseoutput.

### Mis-routing (verkeerde agent)
**Oorzaak**: Semantische verwarring in de vraag.
**Voorbeeld**: "Wat zijn de beschikbare filtervelden voor SmartSales?" → planner routeert naar `graph` (zoekt in documenten) in plaats van `smartsales` (roept `list_queryable_fields` aan).
**Gevolg**: Verkeerd antwoord of leeg antwoord.
**Huidige mitigatie**: Expliciete sectie in `PLAN_SYSTEM_PROMPT` (regels 99–110) met voorbeeldvragen die naar SmartSales moeten.

---

## 6. Of een planner/classifier/rule-based laag nuttig zou zijn

Een aanvullende rule-based of fijngetunede classificatielaag zou de volgende situaties kunnen verbeteren:

1. **Deterministische single-agent queries**: Vragen die altijd naar één specifiek systeem gaan (e-mail → graph, accounts → salesforce) hoeven niet via de LLM-planner. Een keyword-pre-filter zou latency reduceren voor deze eenvoudige gevallen.
2. **SmartSales API-queries**: Aanwezigheid van het woord "SmartSales" gecombineerd met "velden", "filters", "configuratie" kan deterministisch naar SmartSales gerouteerd worden.
3. **Cross-system detectie**: Bepaalde entiteitspatronen (bedrijfsnamen in combinatie met meerdere systeemcategorieën) kunnen als heuristiek dienen voor 360°-routing.

**Alternatieven die in de literatuur worden beschreven** (geciteerd in de docstring van `planning_orchestrator.py`):
- ReAct (Yao et al., ICLR 2023): redeneertraces voor elk beslissingsmoment
- HuggingGPT (Shen et al., NeurIPS 2023): expliciet plannen + parallel uitvoeren + synthetiseren (dit is het huidige patroon)
- AOP (Zhang et al., ICLR 2025): gestructureerde decomposities met DAG-afhankelijkheden (ook het huidige patroon)

---

## 7. Hoe routing verbeterd kan worden in volgende versie

Concrete verbeteringen waarneembaar in de codebase-context:
1. **Few-shot voorbeelden in de systemprompt**: Meer labelled voorbeelden per randgeval (reeds gedeeltelijk aanwezig; uitbreidbaar).
2. **Routing-confidence logging**: Log de `"reasoning"` van de planner (aanwezig in het plan-JSON) standaard naar MLflow voor diagnose.
3. **Deterministische pre-routing**: Een rule-based filter vóór de planner voor eenvoudige single-agent queries.
4. **Feedback loop**: Gebruik de routing-traces uit de evaluatie om de plannerinstructies iteratief bij te stellen.

---

## 8. Thesis-ready paragraaf: Beslissingslogica van de orchestrator

### Beslissingslogica van de orchestrator

De beslissingslogica van de orchestrator in het ontwikkelde systeem berust volledig op het gedrag van een groot taalmodel (LLM), aangestuurd door een uitgebreide systeemprompt. Dit onderscheidt de architectuur van klassieke rule-based of statistisch gelabelde routeringsystemen, en brengt zowel voordelen als inherente beperkingen met zich mee.

Het routeringsproces verloopt in twee expliciete stappen. Eerst stelt de `_available_agents_description()`-methode (regels 357–383 van `agents/planning_orchestrator.py`) een tekstuele beschrijving samen van de drie beschikbare agents en hun domeinen. Deze beschrijving, gecombineerd met de gebruikersvraag, wordt als invoer aangeboden aan de `PlannerAgent`. Die agent — zelf een LLM-instantie zonder tools, geconfigureerd met de `PLAN_SYSTEM_PROMPT` — genereert vervolgens een gestructureerd JSON-uitvoeringsplan. In dit plan wordt per stap bepaald welke agent wordt ingezet en welke informatie die agent moet ophalen.

De `PLAN_SYSTEM_PROMPT` bevat gelaagde routeringsregels die door iteratieve evaluatie zijn opgebouwd. Zo bevat de prompt een expliciet onderscheid tussen semantische beleidsvragen (type A, naar `graph` met `search_documents`) en bestandsnaamzoekopdrachten (type B, naar `graph` met `search_files`), een sectie die SmartSales API-vragen met nadruk bij de `smartsales`-agent plaatst — inclusief expliciete tegenvoorbeelden om graf-routing te voorkomen — en een 360°-querysectie die bepaalt wanneer alle drie agents moeten worden ingeschakeld. Tevens bevat de prompt een semantische afbakening van het begrip "geregistreerde locatie" als SmartSales-entiteit, ter voorkoming van verwarring met Salesforce-accounts.

Het systeem biedt als structurele validatie enkel een schema-controle (`_validate_plan()`, regels 326–355): het controleert of de geselecteerde agenten in de lijst van beschikbare agents staan, maar voert geen inhoudelijke controle uit of de keuze semantisch correct is. Een foutieve agentselectie door de planner wordt pas zichtbaar bij de uitvoeringsfase, wanneer de subagent leeg of irrelevant resultaat retourneert.

De evaluatie in het systeem (`eval/mlflow_eval.py`) meet routeringsnauwkeurigheid via precision- en recall-berekeningen ten opzichte van gelabelde `expected_agents` per benchmarkprompt. Precision meet het aandeel van de aangeroepen agents dat verwacht werd (beschermt tegen over-routing), terwijl recall meet het aandeel van de verwachte agents dat ook daadwerkelijk werd aangesproken (beschermt tegen under-routing). Een aanvullende LLM-evaluator (`eval/score.py`) scoort de routeringskwaliteit op een schaal van 1 tot 5, rekening houdend met de volgorde en noodzakelijkheid van de aanroepen.

Uit de structuur van de benchmarkprompts in `eval/prompts/prompts.json` blijkt dat het systeem specifiek wordt getest op drie risicocategorieën: impliciete cross-systeem-queries (waarbij de verbinding tussen systemen niet expliciet in de vraag staat), entity-centric queries (waarbij alle systemen voor één entiteit worden bevraagd), en API-metadatavragen (waarbij SmartSales-spécifieke queries niet naar Graph mogen worden gerouteerd). De aanwezigheid van uitgebreide tegeninstructies in de systemprompt suggereert dat mis-routing in deze categorieën in eerdere iteraties werd geobserveerd.

Een structureel nadeel van LLM-gebaseerde routing is de inherente niet-determinisme: bij identieke invoer kunnen verschillende LLM-runs verschillende routeringsbeslissingen produceren. Dit maakt reproduceerbaarheidsgaranties moeilijk. Bovendien is de planning kwetsbaar voor prompt-engineering in de gebruikersvraag zelf. De routering is dan ook niet formeel aantoonbaar correct, maar empirisch geëvalueerd op een beperkte testset. Voor een productiesysteem suggereert dit dat aanvullende mechanismen — zoals een deterministische pre-filter voor eenvoudige single-agent queries of expliciete inter-rater evaluatie van de routeringsresultaten — wenselijk zijn om de betrouwbaarheid van de routeringsbeslissingen verder te kwantificeren.
