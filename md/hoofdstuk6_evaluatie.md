# Hoofdstuk 6 — Evaluatie

> **Structuurgids voor de masterproef**
> Dit document geeft per sectie uitleg, methodologie, voorbeeldformuleringen en concrete suggesties.
> Het is geen definitieve thesistekst, maar een bouwplan dat je sectie per sectie zelf uitwerkt.

---

## 6.1 Evaluatie-opzet

### Wat staat er in deze sectie?

De evaluatie-opzet beschrijft het *kader* en de *methodologie* van de evaluatie voordat je de resultaten presenteert. Je beantwoordt hier de vragen: wat meet je, hoe meet je het, en waarom op die manier?

### Onderzoeksvragen die deze sectie ondersteunt

- Hoe goed presteert het multi-agent systeem op typische enterprise-gebruiksvragen?
- Is de evaluatiemethode valide en reproduceerbaar?

### Wat je hier opneemt

**a) Overzicht van de evaluatiedimensies**

Je systeem wordt beoordeeld op vier orthogonale dimensies:

| Dimensie | Vraag |
|---|---|
| **Correctheid** | Geeft de agent het juiste antwoord? |
| **Routing** | Wordt de query naar de juiste subagent gestuurd? |
| **Performantie** | Hoe snel reageert het systeem? |
| **Kost** | Hoeveel tokens en API-kosten genereert een query? |

**b) Evaluatiestrategie**

Het systeem maakt gebruik van Large Language Models (LLM's) als kern, wat twee gevolgen heeft voor de evaluatie:

1. *Niet-deterministisch gedrag*: dezelfde query kan bij herhaalde uitvoering een licht ander antwoord opleveren. Je dient dit te vermelden en bij voorkeur elke query meerdere keren uit te voeren (minstens 3 runs) en gemiddelden te rapporteren.
2. *Open antwoorden*: in tegenstelling tot klassieke IR-systemen met binaire relevantie (relevant/niet-relevant) zijn de antwoorden van een LLM-gebaseerde agent vrijgesteld tekst. Dit vereist een LLM-as-evaluator aanpak (zie §6.3).

**c) Testomgeving**

Beschrijf de infrastructuur:
- Model: Azure OpenAI (deployment: `gpt-4o` of equivalent)
- MCP-servers: lokaal gedeployed op poorten 8000 (Graph), 8001 (Salesforce), 8002 (SmartSales)
- Evaluatietool: `eval/script.py` — automatische benchmark die antwoorden opslaat en door een LLM-evaluator laat beoordelen

**d) Automatisering**

Vermeld dat je een geautomatiseerd evaluatiescript hebt ontwikkeld (`eval/script.py`) dat:
- Alle testprompts sequentieel uitvoert per agent
- Latency, tokengebruik en het ruwe antwoord registreert
- Na afloop een LLM-evaluator inschakelt die elk antwoord scoort op een schaal van 1 tot 5
- Resultaten wegschrijft naar een Excel-werkmap met aparte tabbladen per agent

**Voorbeeldformulering:**

> "De evaluatie van het voorgestelde multi-agent systeem is opgebouwd rond vier complementaire dimensies: correctheid van antwoorden, nauwkeurigheid van query-routing, responstijd en tokenkosten. Voor elke dimensie worden zowel kwantitatieve als kwalitatieve methoden gehanteerd. De volledige evaluatieprocedure is geautomatiseerd via een benchmarkscript dat voor elke testvraag de agentrespons registreert, de latency meet, het tokenverbruik logt en de kwaliteit van het antwoord beoordeelt via een afzonderlijke LLM-evaluator."

---

## 6.2 Testscenario's en querycategorieën

### Wat staat er in deze sectie?

Een beschrijving van de testset: welke vragen zijn opgesteld, waarom, en hoe zijn ze gecategoriseerd. Dit is het equivalent van een *benchmark dataset* in klassiek IR-onderzoek.

### Onderzoeksvraag die deze sectie ondersteunt

- Zijn de testscenario's representatief voor de beoogde gebruiksscenario's in een enterprise-omgeving?

### Structuur van de testset

De testset bestaat uit **vier categorieën** queries, ingedeeld per agent en op basis van complexiteit:

#### 6.2.1 Single-agent queries

Single-agent queries testen één gespecialiseerde agent in isolatie. Ze meten of de agent de juiste tools selecteert, de parameters correct construeert en een inhoudelijk correct antwoord retourneert.

**Microsoft Graph Agent** — 11 queries, gedekt door alle 11 beschikbare tools:

| Subcategorie | Voorbeeldquery | Moeilijkheid |
|---|---|---|
| Identiteit | "Who am I in Microsoft 365?" | Eenvoudig |
| E-mail — lijst | "Show me my 5 most recent emails." | Eenvoudig |
| E-mail — zoeken op onderwerp | "Search for emails with 'meeting' in the subject." | Gemiddeld |
| E-mail — zoeken op datum | "Have I received any emails in the last 7 days?" | Gemiddeld |
| E-mail — lezen (geketend) | "What does my most recent email say?" | Moeilijk |
| Personen | "Find the email address of Dorian." | Eenvoudig |
| Kalender — lijst | "What are my upcoming calendar events this week?" | Eenvoudig |
| Kalender — zoeken | "Search my calendar for events in the next 14 days." | Gemiddeld |
| Contacten | "Show me my Microsoft 365 contacts." | Eenvoudig |
| Bestanden — zoeken | "Find any Excel or PDF files in my OneDrive." | Gemiddeld |
| Bestanden — lezen (geketend) | "Search OneDrive for a file called 'report' and read it." | Moeilijk |

**Salesforce Agent** — 10 queries, gedekt door alle 5 tools (`find_accounts`, `find_contacts`, `find_leads`, `get_opportunities`, `get_cases`):

Elke tool wordt getest met minstens één eenvoudige query (basislijst) en één query met filters of extra velden, om te verifiëren of de agent de `filters`- en `extra_fields`-parameters correct benut.

Voorbeelden:
- "List 5 Salesforce accounts." *(eenvoudig)*
- "Find Salesforce accounts in Belgium, including their billing address." *(gemiddeld, vereist `extra_fields` + `filters`)*
- "Show me Salesforce opportunities with an amount greater than 10,000. Include probability." *(gemiddeld)*

**SmartSales Agent** — 22 queries, gedekt door alle 19 tools (locaties, catalogus, orders):

De SmartSales agent beschikt over de rijkste toolset. De testset omvat:
- Basislijst-queries (projectie `simple`)
- Gefilterde queries (via de `q`-parameter met JSON-querysyntax, bv. `{"city":"eq:Brussels"}`)
- Gesorteerde queries (via de `s`-parameter)
- Geketende queries waarbij de agent eerst een lijst ophaalt en vervolgens het uid van het eerste resultaat gebruikt om de detailpagina op te vragen (test of de agent meerdere tools kan combineren)
- Metadataqueries (welke velden zijn filterbaar, sorteerbaar of weergaveerbaar)

#### 6.2.2 Cross-agent queries

Cross-agent queries vereisen dat de orchestrator meerdere subagents aanroept, de tussenresultaten interpreteert en een gecombineerd antwoord retourneert. Deze scenario's testen de coördinatiefunctie van de orchestrator.

| Voorbeeldquery | Betrokken agents |
|---|---|
| "Find contacts named 'John' in both Microsoft 365 and Salesforce." | Graph + Salesforce |
| "Show my calendar events and check if organizers are in Salesforce." | Graph + Salesforce |
| "List SmartSales locations in Brussels and matching Salesforce accounts." | SmartSales + Salesforce |
| "What are my 3 most recent emails? Are those senders in Salesforce?" | Graph + Salesforce |
| "Show open Salesforce opportunities and SmartSales locations in Belgium." | Salesforce + SmartSales |

#### 6.2.3 Moeilijkheidsindeling

Elke query krijgt een van drie moeilijkheidsniveaus:

- **Eenvoudig**: één tool, directe parameters, geen interpretatie vereist
- **Gemiddeld**: filterparameters opstellen, bewuste keuze van extra velden, of kennis van de querysyntax
- **Moeilijk**: meerdere tools achter elkaar (geketend), cross-agent samenwerking, of complexe parameterredenering

**Voorbeeldformulering:**

> "De testset omvat [N] queries verdeeld over vier categorieën: Microsoft Graph ([n1] queries), Salesforce ([n2] queries), SmartSales ([n3] queries) en cross-agent scenarios ([n4] queries). Elke query is geclassificeerd op moeilijkheidsgraad (eenvoudig, gemiddeld of moeilijk) en getagd met de betrokken tools, zodat de resultaten per tool of per moeilijkheidsniveau geaggregeerd kunnen worden. Cross-agent queries worden uitsluitend via de orchestratoragent uitgevoerd en dienen om de coördinatie- en synthesecapaciteiten van het systeem te beoordelen."

---

## 6.3 Evaluatie van correctheid

### Wat staat er in deze sectie?

Hoe beoordeel je of het antwoord van de agent inhoudelijk correct is? Dit is de moeilijkste dimensie omdat antwoorden vrijgesteld tekst zijn en afhankelijk van de werkelijke data in de verbonden systemen.

### Onderzoeksvraag

- Retourneert het systeem inhoudelijk correcte en volledige antwoorden op de gestelde vragen?

### Methode: LLM-as-evaluator

Omdat de antwoorden niet volledig objectief verifieerbaar zijn (de data in Microsoft 365, Salesforce en SmartSales is dynamisch), gebruiken we een *LLM-as-evaluator* aanpak. Dit is een gevestigde methode in recent onderzoek naar LLM-evaluatie (Zheng et al., 2023; Liu et al., 2023).

**Werkwijze:**

Voor elke query is een *verwacht antwoord* opgesteld — een beschrijving van wat een correct en volledig antwoord zou moeten bevatten, onafhankelijk van de specifieke datawaarden. Voorbeeld:

> Query: "Show me my 5 most recent emails."
> Verwacht antwoord: "A list of the 5 most recent inbox emails, each with at minimum the subject line, sender name or email address, and received date/time."

Na het uitvoeren van alle queries beoordeelt een afzonderlijke LLM-instantie (dezelfde Azure OpenAI deployment) elk daadwerkelijk antwoord op een schaal van **1 tot 5**:

| Score | Betekenis |
|---|---|
| 1 | Volledig fout, irrelevant of geen zinvol antwoord |
| 2 | Gedeeltelijk correct, maar met grote lacunes of fouten |
| 3 | Grotendeels correct met enkele opmerkelijke tekortkomingen |
| 4 | Correct met slechts kleine lacunes of opmaakproblemen |
| 5 | Volledig correct en compleet |

De evaluator krijgt als invoer: de oorspronkelijke query, het verwachte antwoord en het daadwerkelijke agentantwoord. Hij retourneert een JSON-object met score en rationale.

**Waarom niet handmatig scoren?**

Handmatige scoring van 50+ queries is tijdsintensief en subjectief. Een LLM-evaluator is sneller, consistent en — bij een goede promptopzet — betrouwbaar genoeg voor een eerste iteratie. Je kunt de validiteit versterken door een steekproef handmatig na te kijken en de overeenstemming te rapporteren.

**Onderscheid: objectief vs. open antwoorden**

| Type antwoord | Voorbeeld | Evaluatiestrategie |
|---|---|---|
| Objectief verifieerbaar | "Who am I?" → displayName + e-mailadres | Controleer of beide velden aanwezig zijn |
| Structureel verifieerbaar | "List locations" → JSON-array met uid-veld | Controleer structuur/formaat |
| Open antwoord | "What does this email say?" → vrije tekst | LLM-evaluator met verwacht antwoord |
| Cross-agent synthese | Gecombineerd antwoord uit twee systemen | LLM-evaluator op volledigheid en bronvermelding |

**Voorbeeldformulering:**

> "De correctheid van de agentantwoorden wordt beoordeeld via een LLM-as-evaluator methodologie. Voor elke testvraag is vooraf een referentieantwoord opgesteld dat beschrijft welke informatie een correct en volledig antwoord dient te bevatten. Een afzonderlijke LLM-instantie — geïsoleerd van de agentuitvoering — vergelijkt het daadwerkelijke agentantwoord met dit referentieantwoord en kent een score toe op een ordinale schaal van 1 tot 5. Deze aanpak is gevalideerd in recent onderzoek naar automatische evaluatie van generatieve systemen (Zheng et al., 2023). Om de betrouwbaarheid van de LLM-evaluator te staven, werd een steekproef van [n] query-antwoordparen tevens handmatig beoordeeld. De inter-rater overeenkomst tussen de LLM-evaluator en de menselijke beoordeling wordt uitgedrukt via de gewogen kappa-score."

---

## 6.4 Evaluatie van query routing

### Wat staat er in deze sectie?

Query routing is de functie van de orchestratoragent: op basis van de inhoud van de vraag beslissen welke subagent(s) worden aangeroepen. Dit is meetbaar en objectief toetsbaar.

### Onderzoeksvraag

- Routeert de orchestrator queries naar de juiste subagent(s)?

### Methode

**a) Grondwaarheid definiëren**

Voor elke query in de testset wordt de *verwachte routing* vooraf bepaald:

| Query | Verwachte routing |
|---|---|
| "Who am I in Microsoft 365?" | `ask_graph_agent` |
| "List 5 Salesforce accounts." | `ask_salesforce_agent` |
| "List SmartSales locations." | `ask_smartsales_agent` |
| "Find contacts in M365 and Salesforce." | `ask_graph_agent` + `ask_salesforce_agent` |

**b) Meten van de werkelijke routing**

De routeringsbeslissing van de orchestrator is observeerbaar via de tool-calls die de agent uitvoert. Het benchmarkscript kan deze loggen door de agentrespons te inspecteren of door de MCP-serverlogs te analyseren.

**c) Metrics**

- **Routing accuracy** (voor single-agent queries): percentage queries waarbij exact de verwachte tool werd aangeroepen.
- **Precision / Recall** (voor cross-agent queries): werden alle verwachte agents aangeroepen (recall) en werden er geen onnodige agents aangeroepen (precision)?

| Metric | Formule |
|---|---|
| Routing accuracy | correct gerouteerde queries / totaal aantal queries |
| Precision (cross-agent) | TP / (TP + FP) |
| Recall (cross-agent) | TP / (TP + FN) |

Waarbij TP = terecht aangeroepen agent, FP = onterecht aangeroepen agent, FN = verwachte agent niet aangeroepen.

**d) Veelvoorkomende routeringsfouten**

- **Over-routing**: de orchestrator roept meerdere agents aan terwijl één volstaat (verhoogt latency en kost)
- **Under-routing**: bij cross-agent queries wordt slechts één agent aangeroepen
- **Mis-routing**: de query wordt naar de verkeerde agent gestuurd (bv. een Salesforce-vraag naar Graph)

**Voorbeeldformulering:**

> "De nauwkeurigheid van query-routing wordt beoordeeld door voor elke testvraag de werkelijke tool-calls van de orchestratoragent te vergelijken met de vooraf bepaalde grondwaarheid. Voor single-agent queries wordt de routing accuracy gerapporteerd als het percentage correct gerouteerde queries. Voor cross-agent queries worden precision en recall berekend op basis van de aanwezigheid of afwezigheid van de verwachte subagenten in de tool-call reeks. Fouten worden gecategoriseerd als over-routing, under-routing of mis-routing."

---

## 6.5 Evaluatie van performantie

### Wat staat er in deze sectie?

Hoe snel reageert het systeem? Performantie is voor een enterprise-zoeksysteem kritisch vanuit gebruiksperspectief.

### Onderzoeksvraag

- Wat is de responstijd van het systeem voor verschillende querytypes, en wat zijn de bottlenecks?

### Gemeten variabelen

Voor elke query wordt de **end-to-end latency** gemeten: de tijd tussen het versturen van de query en het ontvangen van het volledige antwoord van de agent.

```
t_start → agent.run(query) → t_end
response_time = t_end - t_start
```

Dit omvat alle componenten: de LLM-inferentie van de agent, de tool-calls naar de MCP-servers, de externe API-calls (Graph API, Salesforce API, SmartSales API) en de synthese van het antwoord.

### Uitsplitsing per laag (indien instrumentatie beschikbaar)

| Laag | Wat het meet |
|---|---|
| Agent LLM | Tijd voor reasoning + tool-selectie |
| MCP-server | Tijd voor tool-verwerking + authenticatie |
| Externe API | Netwerklatency + API-responstijd |

In de huidige implementatie is end-to-end latency de meest praktische maatstaf, tenzij je aanvullend per-laag logging implementeert.

### Analyse

Rapporteer de volgende statistieken per agent en per moeilijkheidsniveau:

- Gemiddelde responstijd (`μ`)
- Mediaan (`p50`)
- 95e percentiel (`p95`) — relevant voor worst-case gebruikservaring
- Standaarddeviatie (`σ`)

**Hypothese om te testen:**

> *Cross-agent queries hebben een significant hogere latency dan single-agent queries, omdat de orchestrator sequentieel meerdere subagents aanroept.*

Dit is te toetsen met een eenvoudige statistische test (bv. Mann-Whitney U-test) gegeven de kleine steekproefomvang.

**Invloedsfactoren om te vermelden:**

- Geketende tool-calls (bv. `list_locations` → `get_location`) verhogen de latency lineair
- Externe API's (Graph, Salesforce, SmartSales) introduceren variabele netwerkvertraging
- LLM-inferentie is afhankelijk van de outputlengte (meer tokens = trager)

**Voorbeeldformulering:**

> "De performantie van het systeem wordt uitgedrukt in end-to-end responstijd, gemeten als het tijdsinterval tussen het indienen van de query en het ontvangen van het volledige agentantwoord. Per query worden gemiddelde, mediaan en 95e percentiel gerapporteerd. De verwachting is dat cross-agent queries — waarbij de orchestratoragent meerdere subagents sequentieel aanroept — een significant hogere latency vertonen dan single-agent queries. Dit patroon wordt empirisch getoetst op basis van de benchmarkresultaten."

---

## 6.6 Evaluatie van kost

### Wat staat er in deze sectie?

Hoeveel tokens verbruikt het systeem per query, en wat zijn de geschatte API-kosten? Dit is relevant voor schaalbaarheid en bedrijfsmatige inzetbaarheid.

### Onderzoeksvraag

- Wat is het tokenverbruik per querykategorie, en welke cost drivers zijn het meest impactvol?

### Gemeten variabelen

Voor elke query wordt geregistreerd:

| Variabele | Definitie |
|---|---|
| `input_tokens` | Tokens in de prompt (systeemprompt + gebruikersvraag + tool-beschrijvingen + tool-resultaten) |
| `output_tokens` | Tokens in het antwoord van de agent |
| `total_tokens` | `input_tokens` + `output_tokens` |

Deze waarden zijn beschikbaar via de `usage`-velden in de Azure OpenAI API-respons.

### Kost berekening

De kosten per query worden berekend als:

```
kost (USD) = (input_tokens / 1000) × prijs_input + (output_tokens / 1000) × prijs_output
```

De prijzen zijn afhankelijk van het gebruikte model (bv. voor GPT-4o: $2.50 / 1M input tokens, $10.00 / 1M output tokens — controleer actuele Azure-prijzen).

### Analyse

Rapporteer per agent en per querykategorie:

- Gemiddeld totaal tokenverbruik
- Verhouding input/output tokens (hoge input-tokens wijzen op grote tool-resultaten of lange systeemprompts)
- Geschatte kosten per query en geëxtrapoleerde maandkost bij typisch gebruik

**Cost drivers identificeren:**

Bij LLM-gebaseerde agenten zijn de grootste cost drivers:
1. **Systeemprompt**: de instructies voor elke agent worden bij elke aanroep meegestuurd
2. **Tool-beschrijvingen**: de MCP-tools worden als JSON-schema aan de LLM doorgegeven
3. **Tool-resultaten**: de ruwe API-respons (bv. een lijst van 50 locaties) kan groot zijn
4. **Geketende calls**: bij meerdere tool-calls worden de tussenresultaten accumulatief meegestuurd in de context

**Hypothese:**

> *Cross-agent queries genereren significant meer tokens dan single-agent queries, omdat de orchestrator de volledige subagent-respons opneemt in zijn context voordat hij het eindantwoord formuleert.*

**Voorbeeldformulering:**

> "Het tokenverbruik per query wordt gerapporteerd op basis van de `usage`-metadata die door de Azure OpenAI API wordt teruggegeven. Onderscheid wordt gemaakt tussen input- en outputtokens, waarbij inputtokens de systeemprompt, gebruikersvraag, tool-schemabeschrijvingen en eventuele tool-resultaten omvatten. Op basis van de actuele Azure OpenAI-prijslijst wordt de kostprijs per query en per querycategorie berekend. De resultaten illustreren de trade-off tussen querycomplexiteit en operationele kost."

---

## 6.7 Beperkingen van de evaluatie

### Wat staat er in deze sectie?

Elke evaluatie heeft limieten. Het is academisch belangrijk om deze eerlijk te benoemen — het versterkt de geloofwaardigheid van je werk.

### Beperkingen en hoe ze te formuleren

**a) Kleine testset**

De testset bestaat uit [N] queries. Dit is voldoende om de functionaliteit te demonstreren, maar te klein voor statistische generalisering. De resultaten zijn indicatief, niet exhaustief.

> "De testset omvat [N] queries en is derhalve niet representatief voor alle mogelijke enterprise-gebruiksvragen. De gepresenteerde resultaten dienen als indicatieve benchmark en laten geen veralgemenende statistische uitspraken toe."

**b) Dynamische data — geen reproduceerbare grondwaarheid**

De onderliggende data in Microsoft 365, Salesforce en SmartSales is dynamisch: e-mails, agenda-items en CRM-records wijzigen continu. Hierdoor zijn de antwoorden van het systeem niet exact reproduceerbaar tussen twee opeenvolgende testmomenten.

> "Omdat de onderliggende bedrijfssystemen dynamische data bevatten, zijn de agentantwoorden afhankelijk van de toestand van die systemen op het moment van testuitvoering. Dit maakt exacte reproduceerbaarheid onmogelijk en vereist de LLM-as-evaluator aanpak waarbij correctheid structureel — en niet datawaarde-specifiek — wordt beoordeeld."

**c) LLM-evaluator bias**

De LLM-evaluator is zelf een LLM en kan systematisch bepaalde antwoordstijlen prefereren (bv. uitgebreidere antwoorden hoger scoren). Bovendien gebruikt de evaluator hetzelfde basismodel als de geëvalueerde agent, wat een potentieel zelfbeoordelingseffect introduceert.

> "De LLM-evaluator is niet vrij van bias: er bestaat een risico op zelfbeoordelingseffecten wanneer dezelfde modelarchitectuur zowel de antwoorden genereert als beoordeelt. Toekomstig onderzoek zou een externe evaluator (bv. een ander model of menselijke beoordelaars) kunnen inzetten om dit risico te mitigeren."

**d) Niet-deterministisch gedrag**

LLM's produceren bij herhaalde uitvoering licht afwijkende antwoorden (temperature > 0). Zelfs bij temperature = 0 kunnen kleine variaties optreden door tokensampling. Dit introduceert variantie in de correctheids- en latentymetingen.

> "Het niet-deterministische karakter van LLM-inferentie impliceert dat de gemeten latency en correctheidsscores variëren bij herhaalde uitvoering van dezelfde query. Om dit effect te beperken worden gemiddelden over meerdere runs gerapporteerd."

**e) Geen gebruikersstudie**

De evaluatie is volledig geautomatiseerd. Er is geen gebruikersstudie uitgevoerd om te meten of de antwoorden ook als nuttig worden ervaren door echte eindgebruikers. Gepercipieerde bruikbaarheid (usability) is een andere dimensie dan technische correctheid.

> "De evaluatie beperkt zich tot technische correctheid en performantie. Gebruikerstevredenheid en gepercipieerde bruikbaarheid — dimensies die relevant zijn vanuit een HCI-perspectief — vallen buiten het bestek van dit onderzoek en bieden aanknopingspunten voor vervolgonderzoek."

**f) Beperkte dekking van randgevallen**

De testset bevat geen adversariale queries (queries die het systeem bewust proberen te misleiden), ambigue queries (waarbij meerdere routeringsbeslissingen verdedigbaar zijn) of queries over niet-bestaande data. Deze randgevallen zijn relevant voor productie-inzet maar vallen buiten de scope van deze evaluatie.

---

## Referenties (suggesties)

Voeg in je bibliografie minstens de volgende types bronnen toe voor het evaluatiehoofdstuk:

- **LLM-as-evaluator**: Zheng, L. et al. (2023). *Judging LLM-as-a-judge with MT-Bench and Chatbot Arena.* NeurIPS.
- **RAG-evaluatie**: Es, S. et al. (2023). *RAGAS: Automated Evaluation of Retrieval Augmented Generation.* arXiv.
- **Agent-evaluatie**: Liu, X. et al. (2023). *AgentBench: Evaluating LLMs as Agents.* arXiv.
- **Multi-agent systemen**: Wang, L. et al. (2024). *A Survey on Large Language Model based Autonomous Agents.* Frontiers of Computer Science.

---

## Overzichtstabel: evaluatiedimensies

| Dimensie | Sectie | Metric | Methode |
|---|---|---|---|
| Correctheid | 6.3 | LLM-score 1–5 | LLM-as-evaluator met referentieantwoord |
| Routing | 6.4 | Routing accuracy, Precision, Recall | Vergelijking tool-calls met grondwaarheid |
| Performantie | 6.5 | Latency (μ, p50, p95, σ) | Tijdmeting per query (end-to-end) |
| Kost | 6.6 | Input/output tokens, USD/query | Azure OpenAI `usage`-metadata |

---

*Gegenereerd als schrijfhulp voor masterproef, sectie 6 — Evaluatie.*
*Pas de formulering en de concrete getallen aan op basis van je werkelijke resultaten.*
