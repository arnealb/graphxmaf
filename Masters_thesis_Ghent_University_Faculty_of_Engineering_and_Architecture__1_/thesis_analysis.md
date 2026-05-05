# Kritische analyse van de masterproef
## "Een Schaalbare Multi-Agentarchitectuur voor Enterprise Search"
**Datum analyse:** 31 maart 2026
**Beoordelingscontext:** Eerste versie — beoordeling van richting, fundament en prioriteiten

---

## 1. Algemene beoordeling

### Hoe sterk is deze scriptie op dit moment inhoudelijk?

Dit is een **redelijk gefundeerde eerste versie** van een masterproef die duidelijk maakt dat de student een werkend systeem heeft gebouwd en begrijpt wat er technisch gemaakt werd. De structuurkeuze is logisch, het prototype lijkt echt te werken (de resultaten zijn concreet en geloofwaardig), en de evaluatie is verrassend goed onderbouwd voor een eerste draft.

Tegelijk zijn er **enkele fundamentele problemen** die ver voorbij "kleine verbeteringen" gaan. Het meest kritische: de bibliografie is vrijwel volledig die van het sjabloon (over VM-placement en OpenStack) en heeft nauwelijks iets met de thesis te maken. Het literatuurhoofdstuk citeert bijna niets. Dit alleen al is een dealbreaker voor indiening.

### Voelt dit als een degelijke eerste versie of een ruwe draft?

**Tussenin.** De inhoudelijke uitwerking van architectuur, implementatie en evaluatie is **beter dan gemiddeld voor een eerste versie** — er zijn echte getallen, echte trade-offs en eerlijke beperkingen. Maar de academische omkadering (bronverwijzingen, gerelateerd werk, formele onderbouwing van keuzes) is zo dun dat de scriptie op dit moment eerder aanvoelt als een technisch projectverslag dan als een masterproef.

### Laat deze versie zien dat de student in de juiste richting werkt?

**Ja, overtuigend.** De kernboodschap — dat een multi-agentarchitectuur met MCP technisch haalbaar is voor enterprise search — wordt afdoende aangetoond. De promotor kan er zeker mee leven dat dit de juiste richting is.

### Grootste sterktes

- Het **evaluatiehoofdstuk (Resultaten)** is inhoudelijk het sterkste deel: concrete tabellen, per-agent analyse, routingtrace-methodiek, eerlijke bespreking van zwakke punten. Dit is verdienstelijk voor een eerste versie.
- De **architectuurkeuze is helder uitgelegd** en de opsplitsing orchestrator/subagent/MCP-laag is goed gemotiveerd.
- De **beperkingensecties** (implementatie en evaluatie) zijn eerlijk en niet verdoezeld — dit toont academische integriteit.
- De **probleemanalyse** is functioneel en leidt logisch naar de vereisten.
- Het **future work-hoofdstuk** is concreet en toont inzicht in wat de volgende versie nodig heeft.

### Grootste zwaktes

1. **Bibliografie is leeg qua relevante inhoud** — het gaat bijna uitsluitend om templateverwijzingen over cloud resource allocation.
2. **Geen literatuurcitaties** door de hele scriptie — claims worden gemaakt zonder enige bronvermelding.
3. **Conclusie is uitgecommentarieerd** in `main.tex` en de stub-tekst volstaat hoe dan ook niet.
4. **Geen figuren/diagrammen** in het architectuur- en implementatiehoofdstuk.
5. **Sterke herhaling** van de kernproblematiek over drie hoofdstukken (inleiding, literatuurstudie, probleemanalyse).
6. **Geen gerelateerd werk**: er is geen vergelijking met bestaande enterprise search-oplossingen.

---

## 2. Inhoudelijke hiaten

### Volledig afwezig

- **Gerelateerd werk**: Er is nergens een vergelijking met bestaande enterprise search-oplossingen zoals Microsoft Copilot/M365 Copilot, Elastic Enterprise Search, Coveo, Glean of Google Workspace Search. Een jury zal onmiddellijk vragen: "Waarom geen bestaand platform?" Dit ontbreekt volledig.
- **Formal evaluation baseline**: Er is geen vergelijking met een eenvoudigere aanpak (bijv. één centrale agent zonder subagents, of een pure RAG-aanpak). Zonder baseline is het onmogelijk te zeggen of de multi-agentaanpak echt beter is.
- **Concurrerende agent frameworks**: LangGraph en Semantic Kernel worden zeer oppervlakkig behandeld. Er zijn geen bronnen, geen benchmarks, geen kwantitatieve vergelijking. De keuze voor Microsoft Agent Framework is onvoldoende wetenschappelijk onderbouwd.
- **RAG**: RAG wordt in de literatuurstudie nauwelijks besproken, terwijl het een centrale relevante techniek is voor enterprise search. Het verschil tussen retrieval-augmented generation en de tool-calling aanpak zou centraal moeten staan in hoofdstuk 1.
- **MCP in de literatuur**: MCP is een nieuw protocol (Anthropic, november 2024). De academische positie ervan ten opzichte van alternatieve integratieprotocollen (bijv. OpenAPI, function calling) ontbreekt.
- **Schaalbaarheidsevaluatie**: De titel van de scriptie belooft "schaalbaarheid", maar schaalbaarheid wordt nergens geëvalueerd. Hoeveel databronnen kan het systeem aan? Wat is de impact op latency bij meerdere subagents? Schaalbaarheid als begrip wordt enkel architecturaal besproken, nooit empirisch onderbouwd.

### Te oppervlakkig

- **De governance-sectie** (1.6 in de literatuurstudie) eindigt plots na één paragraaf. Dit onderwerp is cruciaal voor enterprise AI maar wordt nauwelijks uitgewerkt (GDPR, AI Act, audittrails, data residency worden niet besproken).
- **Prompt injection** wordt in één zin vermeld maar nooit uitgewerkt als bedreiging. Voor een enterprise search-systeem is dit een serieuze beveiligingsvector.
- **Authenticatiestromen** worden beschreven maar niet vergeleken. Waarom JWT voor SmartSales en OAuth Authorization Code voor Salesforce? Deze keuzes zijn technisch interessant maar academisch onverantwoord.
- **Semantische zoekfunctionaliteit** voor de Graph-agent (vector embeddings) wordt terloops vermeld (één zin) maar niet uitgewerkt, niet geëvalueerd, en niet vergeleken met de klassieke aanpak. Dit is een veelbelovend aspect dat meer aandacht verdient.

### Claims zonder onderbouwing

- "LLMs zijn in staat om natuurlijke taal te begrijpen en genereren" — `% todo: bronnen?` staat er zelf bij. Elementaire claim zonder citaat.
- "LangGraph is in de eerste plaats sterk in scenario's waarin de logica expliciet gemodelleerd moet worden als een graaf" — geen bron, geen vergelijkend onderzoek geciteerd.
- "Microsoft Agent Framework legt meer nadruk op structuur en controle" — eigen bewering zonder documentatie of externe bron.
- De volledige vereistenlijst (sectie 2.5) is niet afgeleid van een systematische analyse (gebruikersonderzoek, interviews bij Easi, literatuur). De vereisten zijn correct maar lijken subjectief opgesteld.

### Concepten die strakker gedefinieerd moeten worden

- **"Global search agent"**: wordt in de inleiding geïntroduceerd als term maar nooit formeel gedefinieerd, niet in literatuur verankerd, en wordt daarna nauwelijks nog consequent gebruikt. Is dit een eigen term? Een industriestandaard? Dit moet verduidelijkt worden.
- **"Schaalbaarheid"**: de titel belooft schaalbaarheid maar de term wordt nooit formeel gedefinieerd in het kader van dit systeem (horizontaal? verticaal? meer databronnen? hogere load?).
- **"Enterprise search"**: wordt in sectie 1.1 gedefinieerd maar uitsluitend op basis van eigen beschrijving, zonder academische definitie of referentie.

---

## 3. Structuur en logische opbouw

### Globale structuur

De hoofdstukvolgorde (Inleiding → Literatuur → Probleemanalyse → Architectuur → Implementatie → Evaluatie) is **correct en logisch**. Dit is een sterkte.

### Wat is misplaatst of herhaalt zich?

**Herhalingsprobleem — kritisch:**
De beschrijving van het probleem (data verspreid over meerdere systemen, moeilijk terugvinden, klassieke methoden schieten tekort) wordt op **drie verschillende plaatsen** gezegd:
- Inleiding §1 (context en motivatie)
- Literatuurstudie §1.1 (Enterprise search)
- Probleemanalyse §2.1 en §2.3

Dit is een structureel probleem. De inleiding moet de motivatie geven, de literatuurstudie moet de wetenschappelijke achtergrond situeren, en de probleemanalyse moet het probleem **in de specifieke context van de opdracht** analyseren. Nu zeggen alle drie hetzelfde in andere woorden.

**LLM-beperkingen dubbel:**
LLM-beperkingen staan zowel in §1.2 (literatuurstudie) als in §2.4 (probleemanalyse, risico's). Er is overlap maar ook inhoudelijk onderscheid. De risico's in hoofdstuk 2 hadden beter verder kunnen bouwen op hoofdstuk 1 in plaats van te herhalen.

**Het architectuurhoofdstuk mist figuren:**
Een architectuurhoofdstuk zonder enig diagram is zwak. De beschrijving is goed, maar een figuur met de gelaagde architectuur (gebruiker → orchestrator → subagents → MCP-servers → databronnen) is essentieel en lijkt volledig afwezig. Dit is een serieus presentatieprobleem.

**Evaluatie gesplitst over twee hoofdstukken:**
De evaluatie-opzet (hoofdstuk 5) en de resultaten (hoofdstuk 6) zijn apart. Dit is enigszins onconventioneel. Het werkt als de scheiding helder is, maar momenteel overlappen de sectietitels (beide hebben "Evaluatie van correctheid", "Evaluatie van routing", etc.). Dit is verwarrend en zal leiden tot een rommelig inhoudsopgave.

---

## 4. Kritiek per hoofdstuk

### Abstract

**Wat werkt:** Beknopt, bevat de kern van het onderwerp, prototype, technologieën en bevindingen.
**Wat ontbreekt:** Trefwoorden zijn onafgewerkt (`% todo` staat letterlijk in de broncode). De evaluatieresultaten worden niet concreet benoemd (geen gemiddelde scores, geen kernbevinding). Één zin voor de conclusie ("potentieel heeft") is te zwak voor een abstract.
**Academische volwassenheid:** Acceptabel voor eerste versie.

---

### Inleiding (Hfdst. 7)

**Wat werkt:** Duidelijke context, probleemstelling en onderzoeksvragen. De opbouw van de scriptie is correct beschreven met `\ref{}`-verwijzingen.
**Wat is zwak:** "global search agent" wordt geïntroduceerd maar nooit formeel gedefinieerd. De onderzoeksvragen zijn correct maar vrij breed — ze zouden scherper kunnen worden geformuleerd als falsifieerbare of meetbare vragen.
**Wat ontbreekt:** Geen aanduiding van de methodologische aanpak (hoe wordt deze onderzocht?). Geen begrenzing van scope.
**Academische volwassenheid:** Voldoende voor een eerste versie.

---

### Literatuurstudie (Hfdst. 1 = 8_chapter_1.tex)

**Wat werkt:** De structurering van LLM-beperkingen, agent-begrip en MCP is helder. De onderlinge relaties worden goed uitgelegd.
**Wat is fundamenteel zwak:**
- **Bijna geen citaties.** "% todo: bronnen?" staat er letterlijk bij. Dit is onaanvaardbaar voor een literatuurhoofdstuk.
- Geen bespreking van gerelateerd werk: bestaande enterprise search-oplossingen, multi-agent research, evaluatiemethoden voor LLM-systemen worden niet besproken.
- De vergelijking tussen LangGraph, Semantic Kernel en Microsoft Agent Framework is uitsluitend gebaseerd op eigen beschrijving zonder primaire bronnen. Dit is circulaire redenering: het is niet meer dan de eigen voorkeur onderbouwen met zelfgeschreven argumenten.
- Typo: "in dzee context" (regel 43 van 8_chapter_1.tex).
- De governance-sectie (1.6) eindigt na drie zinnen — dit is een paragraaf, geen sectie.

**Wat ontbreekt:** RAG (slechts vermeld in future work), bestaande enterprise AI-platforms, academische evaluatiekaders voor multi-agent systemen (bijv. AgentBench, HumanEval for agents).
**Academische volwassenheid:** Onvoldoende — het is meer een beschrijvende tekst dan een literatuurstudie met kritische verwerking van bronnen.

---

### Probleemanalyse (Hfdst. 2 = 8_chapter_2.tex)

**Wat werkt:** De opbouw is logisch. De functionele en niet-functionele vereisten zijn helder opgesomd.
**Wat is zwak:**
- De vereisten zijn niet traceerbaar afgeleid: geen interviews, geen use-case-analyse, geen referentie naar literatuur of bedrijfscontext van Easi. Ze lijken zelf opgesteld zonder systematische grondslag.
- `% todo: check deze shit in prototype pls` staat in de broncode. Dit is een interne notitie die absoluut niet in een document mag blijven, ook niet in een eerste versie die gedeeld wordt met de promotor.
- Herhaling van problemen die al in de inleiding en literatuurstudie staan.
- De vereisten zijn in proza geschreven. Een tabel of genummerde lijst zou betere traceerbaarheid bieden (bijv. FR1, FR2, NFR1, ...) zodat later in evaluatie en architectuur naar terug verwezen kan worden.

**Wat ontbreekt:** Er is geen verificatie of de vereisten in de evaluatie ook effectief getest worden. Een traceerbaarheidsmatrix (vereiste → architecturaal besluit → evaluatiecriterium) ontbreekt.
**Academische volwassenheid:** Matig — functioneel maar niet academisch sterk.

---

### Architectuurontwerp (Hfdst. 3 = 8_chapter_3.tex)

**Wat werkt:** De gelaagde opbouw (orchestrator → subagents → MCP-servers → databronnen) is goed beschreven. De motivatie voor subagents per databron is helder.
**Wat is fundamenteel zwak:**
- **Geen enkel architectuurdiagram.** Dit is een architectuurhoofdstuk. Zonder visuele representatie is het onvolledig. Alle beschrijvingen zijn zuiver tekstueel.
- Een groot blok design goals is uitgecommentarieerd. Ofwel verwerk je dit in de tekst, ofwel verwijder je de commentaar. Nu ziet het er uit als half afgewerkt.
- Er staat een expliciete TODO in de tekst: `% TODO: uitwerken --- waarom gespecialiseerde subagents in plaats van de orchestrator rechtstreeks verbinden met de MCP-servers?` — Dit is precies de vraag die een jury zal stellen! De auteur weet dat het een openstaand punt is maar heeft het nog niet beantwoord.
- De beveiligingssectie (§3.5) is oppervlakkig. "Toegang verloopt via OAuth 2.0, access tokens" — dit is beschrijvend, niet analytisch. Wat zijn de concrete beveiligingsbeslissingen gemaakt in het ontwerp?
- De verantwoording van de architectuurkeuzes (§3.6) is kort en herhaalt grotendeels wat al eerder gezegd werd. Er is geen alternatieve architectuur gepresenteerd die dan werd verworpen.

**Wat ontbreekt:** Alternatieve architecturen (bijv. orchestrator die rechtstreeks MCP-tools aanroept zonder subagents), kwantitatieve schaalbaarheidsamse, een sequentiediagram van de queryflow.
**Academische volwassenheid:** Matig — goed voor een interne technische beschrijving, onvoldoende als academische architectuurverantwoording.

---

### Implementatie (Hfdst. 4 = 8_chapter_4.tex)

**Wat werkt:** De technologiekeuzes zijn uitgelegd, per agent wordt de implementatieaanpak beschreven, en de beperkingen worden eerlijk aangehaald.
**Wat is zwak:**
- **Geen codevoorbeelden of -fragmenten.** Een implementatiehoofdstuk zonder één codefragment is zeldzaam en zwak. Hoe ziet een MCP-toolaanroep eruit? Hoe is de orchestrator-systeemprompt gestructureerd? Hoe werkt de YAML-toolconfiguratie?
- `%dis shit extra:` staat letterlijk als commentaar in de broncode (regel 104). Dit is inacceptabel in een document.
- De semantische zoekaanpak voor de Graph-agent wordt in één zin vermeld en vervolgens niet meer besproken, niet geëvalueerd en niet verantwoord. Dit is een architecturaal relevante beslissing die meer uitleg verdient.
- De sectie over integratie tussen agents (§4.5) herhaalt grotendeels wat al in het architectuurhoofdstuk staat.
- Authenticatiekeuzes (JWT vs. OAuth AC flow) worden beschreven maar niet gemotiveerd.

**Wat ontbreekt:** Codefragmenten, een deployment-diagram, discussie over de technische schuld ("technical debt") die bewust werd gemaakt, testing-aanpak (unit tests? integratietests?).
**Academische volwassenheid:** Matig — meer technisch verslag dan academische implementatiebeschrijving.

---

### Evaluatie-opzet (Hfdst. 5 = 8_eval_theo_5.tex)

**Wat werkt:** De vier evaluatiedimensies (correctheid, routing, responstijd, tokenverbruik) sluiten aan bij de onderzoeksvragen. De keuze voor LLM-als-evaluator wordt kort gemotiveerd.
**Wat is zwak:**
- Welk LLM werd als evaluator gebruikt? Dit wordt nergens vermeld. Dit is een cruciaal methodologisch detail.
- Er is geen beschrijving van de evaluatorprompt. Welke instructies kreeg de evaluator-LLM?
- De 1-5 scoreschaal is goed beschreven, maar er is geen kalibratie of inter-rater validation (bijv. 10% handmatig nakijken door mens).
- Hoe werden de testqueries gekozen? Er staat: "een vooraf samengestelde set testqueries" maar er is geen beschrijving van het selectieproces (stratified sampling? scenario-gebaseerd? willekeurig?).
- Sectie 5.2 is beschrijvend ("de testset bestaat uit vier soorten vragen") maar bevat geen motivatie voor de verdeling (waarom 22 per agent?).

**Wat ontbreekt:** Baseline-vergelijking (enkelvoudige agent vs. multi-agent; keyword search vs. LLM), validatie van het evaluatieprotocol, uitleg van de benchmarkscriptimplementatie.
**Academische volwassenheid:** Matig — de opzet is er, maar mist methodologische verantwoording.

---

### Evaluatieresultaten (Hfdst. 6 = 8_eval_practical_6.tex)

**Wat werkt:**
- Concrete, geloofwaardige resultaten met tabellen en cijfers.
- De per-agent analyse is goed: SmartSalesAgent sterk (4,18), SalesforceAgent zwak (2,59) met goede oorzaakanalyse.
- De routing-analyse (100% correcte enkelvoudige routing) is een sterke bevinding.
- De tokenverbruik-analyse is nuttig en goed gecorreleerd met kwaliteitsresultaten.
- Eerlijke erkenning van de piekwaarde (102,8 seconden voor e-mailbodyquery) als architecturaal probleem.

**Wat is zwak:**
- **Geen baseline.** Er wordt geen vergelijking gemaakt met een eenvoudigere aanpak. Alle conclusies zijn daarmee relatief en niet absoluut.
- **Geen statistische significantie.** Met 22 queries per agent zijn er geen statistische tests mogelijk, maar dit zou expliciet erkend moeten worden.
- **De "tweede beperking" ontbreekt.** In §6.5 (Beperkingen) gaat het van "Een eerste beperking" direct naar "Ten derde beperking" — er is een paragraaf verdwenen.
- **Geen voorbeeldqueries getoond.** Er worden scores en analyses gegeven maar nooit een concrete goede vs. slechte query met werkelijk antwoord getoond. Dit is een gemiste kans voor illustratie.
- De evaluatorcalibratie is niet beschreven. Zijn de LLM-scores betrouwbaar?
- De absolute kosten (€/query) worden niet vermeld, terwijl tokenverbruik besproken wordt. Dit is relevante praktische informatie.

**Wat een jury zal aanvallen:**
- "Waarom 22 queries? Waarom niet meer?"
- "Welk LLM evalueerde de antwoorden?"
- "Hoe zou een basislijnmethode presteren op dezelfde dataset?"
- "88 queries is dit representatief voor real-world enterprise gebruik?"
- "Hoe reproduceerbaar zijn deze resultaten gegeven dynamische databronnen?"

**Academische volwassenheid:** De sterkste sectie van de scriptie. Maar zonder baseline en met ontbrekende methodologische details is het niet voldoende voor een eindversie.

---

### Conclusie (9_conclusion.tex — uitgecommentarieerd in main.tex)

**Status:** Commentaar: `% TODO: uitwerken na afronding evaluatie`. De huidige stub-tekst is drie alinea's lang en volledig generiek. De evaluatieresultaten worden niet concreet verwerkt. De onderzoeksvragen worden niet beantwoord.
**Actie vereist:** Volledig herschrijven na afronding van de evaluatie. Elke onderzoeksvraag moet expliciet worden beantwoord met verwijzing naar de resultaten.

---

### Toekomstig werk (10_future-work.tex — uitgecommentarieerd in main.tex)

**Wat werkt:** Concreet en goed gestructureerd per component. Toont inzicht.
**Wat ontbreekt:** Prioritering ontbreekt. Welke uitbreidingen zijn het meest impactvol? Wat is de verwachte moeite vs. impact? RAG-vergelijking wordt terecht vermeld maar is geen "toekomstig werk" — dit had al deel moeten uitmaken van de eerste versie.

---

### Ethische reflectie (11_ethical-reflection.tex — uitgecommentarieerd in main.tex)

**Status:** Volledig sjabloontekst met instructies. Geen enkele inhoudelijke bijdrage. Dit is een verplicht onderdeel voor industrieel ingenieurs en moet ingevuld worden. Relevant: GDPR, AI Act, privacy van enterprise data, prompt injection risico's voor gebruikersdata, vendor lock-in bij Azure/Microsoft.

---

### Bijlagen (13_appendices.tex)

**Status:** Lege sjablonen ("Attachment A - Attachment description"). Wat zou hier nuttig staan: de volledige testquerylijst met verwachte antwoorden, de systeemprompts van de agents, de YAML-toolconfiguraties, de evaluatorprompt.

---

## 5. Academische kwaliteit

### Nauwkeurigheid van formuleringen

Over het algemeen acceptabel maar soms te vaag. Voorbeelden:
- "Dit maakt het moeilijker dan in een meer monolithische architectuur" — moeilijker voor wie? in welk opzicht?
- "Microsoft Agent Framework legt meer nadruk op structuur en controle" — dit is een claim die bewijs vereist.
- "Enterprise search-oplossingen zijn in veel gevallen nog sterk gebaseerd op trefwoorden" — bronvermelding?

### Mate van nuance

De evaluatieresultaten worden genuanceerd besproken, maar de literatuurstudie en architectuurverantwoording missen nuance. De keuze voor Microsoft Agent Framework wordt gepresenteerd als de beste keuze zonder diepgaande vergelijking.

### Sterkte van argumentatie

**Zwak in de literatuurstudie**, **redelijk in de architectuur**, **sterk in de evaluatieresultaten**. De scriptie is ongelijk: de technische delen zijn beter onderbouwd dan de academische delen.

### Academische schrijfstijl

De toon is overwegend correct. Echter:
- Commentaren zoals `% dis shit extra:` en `% todo: check deze shit in prototype pls` zijn pijnlijk informeel en mogen absoluut niet aanwezig zijn in een document dat gedeeld wordt.
- "dzee context" is een typefout.
- De conclusie-stub is te informeel ("Dit hoofdstuk evalueert...").

### Consistentie van terminologie

**Probleem**: "multi-agentarchitectuur" (samengesteld woord, correct in het Nederlands) vs. "multi-agent architectuur" (twee woorden) komen beide voor. In de inleiding (§1.3) staat "multi-agent architectuur", terwijl de rest van de scriptie "multi-agentarchitectuur" gebruikt en ook de titel. Dit moet consequent zijn.

"global search agent": geïntroduceerd in §1.3 van de inleiding, daarna nauwelijks nog gebruikt. Is dit synoniem met "orchestrator"? Met het systeem als geheel? Onduidelijk.

### Risico op te beschrijvend

**Hoog risico** in de literatuurstudie (hoofdstuk 1), die meer beschrijft dan analyseert. Wat zijn de implicaties van elk besproken concept voor de eigen aanpak? Dit wordt bijna nooit expliciet gemaakt.

### Risico op te veel algemene theorie

**Aanwezig** in hoofdstuk 1. De secties over LLMs, AI-agents en MCP zijn grotendeels algemeen en worden pas op het einde van elke sectie kort gekoppeld aan de eigen context. Dit patroon ("algemene uitleg → één zin koppeling") is te zwak. De koppeling met het eigen systeem moet doorheen de hele tekst aanwezig zijn.

---

## 6. Evaluatiehoofdstuk — extra kritische analyse

### Is de evaluatie-opzet voldoende verantwoord?

**Gedeeltelijk.** De vier dimensies zijn goed gekozen maar de opzet wordt onvoldoende methodologisch onderbouwd. Cruciale ontbrekende informatie:
- Naam van de evaluator-LLM
- De exacte prompt aan de evaluator
- Beschrijving van de querysampling-strategie
- Geen baseline

### Zijn de gekozen metrics sterk genoeg?

De metrics (correctheid 1-5, routing accuracy, responstijd, tokenverbruik) zijn **relevant maar onvolledig**. Ontbrekend:
- **Precision/Recall** voor zoekresultaten (klassiek voor search systemen)
- **Hallucination rate**: hoe vaak geeft het systeem foutieve informatie die niet uit de databron komt?
- **Context faithfulness**: sluit het antwoord aan bij de opgehaalde gegevens? (vergelijkbaar met RAG-evaluatiemetrics)
- **Kostprijs per query in euro** (tokenverbruik is een proxy maar niet direct bruikbaar)

### Zwakke plekken in de evaluatiemethodologie

1. **LLM-als-evaluator zonder validatie**: de LLM-evaluatormethode (LLM-as-judge) is in de literatuur known voor positieve bias, inconsistentie bij gelijke scores, en sensitivity aan vraagformulering. Geen van deze beperkingen wordt serieus besproken.
2. **Dynamische databronnen**: erkend als beperking, maar dit betekent dat de resultaten in principe niet reproduceerbaar zijn. Hoe kan een jury het systeem narekijken?
3. **De tweede beperking ontbreekt** (§6.5: gaat van "Een eerste" naar "Ten derde" — de tussenliggende paragraaf is verdwenen).
4. **22 queries per agent** is een kleine set. Er is geen power analysis of motivatie voor dit getal.

### Zijn resultaten voldoende geanalyseerd of enkel beschreven?

**Beter dan gemiddeld.** De oorzaakanalyse voor Salesforce (onvolledige SOQL-veldselectie) en SmartSales (chaining-probleem) toont dat de student begrijpt wat er misgaat. De correlatie tussen tokenverbruik en kwaliteit is interessant. Maar:
- Er is geen expliciete terugkoppeling naar de onderzoeksvragen.
- De routing-resultaten (100% correcte enkelvoudige routing) worden niet in perspectief geplaatst: is dit verwacht? Is dit moeilijk? Hoe verhoudt dit zich tot de literatuur?
- De over-routing case (SmartSalesAgent driemaal aangesproken) is interessant maar niet diep geanalyseerd.

### Wat zou een jury aanvallen?

- "Welk model gebruikte je als evaluator? Hoe objectief is dat?"
- "Hoe reproduceerbaar zijn jouw resultaten?"
- "Waarom geen baseline?"
- "Hoe verhoudt 24 seconden voor de orchestrator zich tot bestaande enterprise search tools?"
- "Schaalbaarheid staat in de titel — waar is de schaalbaarheidsevaluatie?"
- "Is 88 queries representatief?"

### Wat is al voldoende voor een eerste versie?

- De evaluatiedimensies en hun motivatie: ✓
- De tabellenstructuur en per-agent analyse: ✓
- De routingtrace-methodiek: ✓ (innovatief en goed)
- Erkenning van beperkingen: ✓

---

## 7. Architectuur en implementatie

### Is duidelijk waarom voor deze architectuur gekozen werd?

**Deels.** De motivatie voor de multi-agentaanpak is aanwezig (heterogeniteit, modulariteit, uitbreidbaarheid). Maar de specifieke keuze voor een aparte subagent-laag boven een directe MCP-verbinding van de orchestrator wordt niet uitgewerkt — er staat letterlijk een TODO: `% TODO: uitwerken --- waarom gespecialiseerde subagents in plaats van de orchestrator rechtstreeks verbinden met de MCP-servers?`

Dit is een fundamentele architectuurvraag die beantwoord moet worden. Het antwoord (specialisatie, isolatie, domain-specifieke prompt engineering per agent) is verdedigbaar, maar moet uitgeschreven worden.

### Is het verschil tussen ontwerp en implementatie voldoende duidelijk?

**Onvoldoende.** De architectuurhoofdstukken en het implementatiehoofdstuk overlappen sterk. Sectie 4.5 ("Integratie tussen agents") herhaalt veel van wat in hoofdstuk 3 staat. Het onderscheid tussen *hoe het ontworpen is* (Chapter 3) en *hoe het concreet geïmplementeerd is* (Chapter 4) is niet scherp genoeg.

### Zijn beperkingen eerlijk geformuleerd?

**Ja**, dit is een sterkte. De beperkingen van de implementatie worden expliciet, eerlijk en niet-verdoezelend beschreven. Dit is goed academisch gedrag.

### Waar lijkt het te vaag of technisch verslag?

- De sectie "Gebruikte technologieën en stack" (§4.1) is een technologielijst zonder architecturale motivatie.
- De beschrijving van de YAML-toolconfiguratie wordt vermeld maar niet getoond.
- De keuze voor FastMCP wordt niet gemotiveerd.
- "Beperkte vorm van sessiecontext" (Graph-agent) — hoe beperkt precies? Wat wordt bijgehouden?

---

## 8. Taal en stijl

### Informele uitdrukkingen en interne notities in de broncode

Deze mogen absoluut niet aanwezig zijn in een gedeeld document, zelfs een eerste versie:
- `% todo: check deze shit in prototype pls` (8_chapter_2.tex, regel 42)
- `%dis shit extra:` (8_chapter_4.tex, regel 104)
- `% todo: source of truth cursief laten staan` (8_chapter_3.tex, regel 67)
- `% todo: v2` (meerdere plaatsen)
- `% hier nog niets over smartsales` (8_chapter_4.tex)

### Typische herhalende zinconstructies (te doorbreken)

De structuur "X vormt Y. Daardoor Z. Dit maakt W." herhaalt zich te vaak. Voorbeeld uit probleemanalyse: bijna elke paragraaf eindigt met een variatie op "daardoor ontstaat de nood aan een oplossing die...". Dit is een stilistisch patroon dat de tekst eentonig maakt.

### Terminologie-inconsistenties

| Inconsistentie | Voorkomen |
|---|---|
| "multi-agentarchitectuur" vs "multi-agent architectuur" | Inleiding §1.3 vs. rest van de scriptie |
| "global search agent" | Geïntroduceerd in Inleiding, nauwelijks meer gebruikt |
| "GraphAgent" vs "Microsoft Graph-agent" vs "Graph-agent" | Variabel doorheen evaluatieresultaten en implementatie |
| "SalesforceAgent" vs "Salesforce-Agent" | Door elkaar in evaluatiehoofdstuk |

### Typfout

- "in dzee context" (8_chapter_1.tex, regel 43) — moet "in deze context" zijn.

### Andere taalopservaties

- De scriptie is in het Nederlands geschreven maar `main.tex` stelt `\setmainlanguage{english}`. Dit is geen fout (polyglossia behandelt dit) maar het is verwarrend.
- Trefwoorden in de abstract zijn onvolledig: `\textbf{Trefwoorden:} multi-agentarchitectuur, enterprise search, Agentic AI, Model Context Protocol, %todo` — het `%todo` mag absoluut niet zichtbaar zijn.

---

## 9. Prioriteitenlijst

### Must fix before next version

1. **Bibliografie vervangen**: alle huidige referenties (VM-placement, OpenStack) zijn templatemateriaal. Relevante bronnen toevoegen voor: enterprise search, LLMs en tool calling, MCP (Anthropic documentatie), agent frameworks (LangGraph, Semantic Kernel, MAF), multi-agent systemen, LLM-as-judge evaluatie.
2. **Citaties doorheen de hele tekst toevoegen**, te beginnen bij de literatuurstudie.
3. **Conclusie uitschrijven** en opnemen in `main.tex` (uitcommentariëren ongedaan maken). De onderzoeksvragen moeten punt voor punt beantwoord worden.
4. **Alle informele opmerkingen uit de broncode verwijderen** (`% dis shit extra:`, `% todo: check deze shit in prototype pls`, etc.).
5. **Architectuurdiagram(men) toevoegen** — minstens één gelaagd diagram van het volledige systeem.
6. **Evaluatormethodologie uitwerken**: welk LLM, welke prompt, eventuele kalibratie.
7. **De ontbrekende beperking in §6.5** herstellen (gaat van "eerste" naar "derde").
8. **Abstract trefwoorden afwerken** — het `%todo` is zichtbaar.

### Should improve

9. Herhaling elimineren tussen inleiding, literatuurstudie (§1.1) en probleemanalyse (§2.1, §2.3). Elke sectie moet andere inhoud bevatten.
10. Gerelateerd werk toevoegen: vergelijking met Microsoft 365 Copilot, Elastic/Coveo/Glean — waarom wel/niet vergelijkbaar?
11. Baseline-vergelijking aan de evaluatie toevoegen (enkelvoudige agent vs. multi-agent).
12. Architectuurverantwoording versterken: beantwoord de TODO over waarom subagents in plaats van directe MCP-verbinding.
13. Vereisten traceerbaarder maken (nummering FR1/FR2/NFR1/... en terugverwijzing in evaluatie).
14. RAG meer uitwerken in de literatuurstudie (nu te weinig aanwezig voor een enterprise search-context).
15. Codefragmenten toevoegen in het implementatiehoofdstuk.
16. De ethische reflectie schrijven (verplicht onderdeel).
17. Terminologie-inconsistenties rechtzetten ("multi-agentarchitectuur" consequent, agent-namen consistent).

### Nice to improve

18. Schaalbaarheid empirisch onderbouwen of de titel aanpassen.
19. Qualitatieve voorbeelden toevoegen in het evaluatiehoofdstuk (goede vs. slechte response).
20. Kostprijs in euro per query berekenen op basis van Azure OpenAI pricing.
21. Bijlagen invullen met zinvolle inhoud (testqueries, systeemprompts, toolconfiguraties).
22. De twee evaluatiehoofdstukken (opzet + resultaten) eventueel samenvoegen of de sectietitel-overlap wegnemen.
23. Future work voorzien van prioritering (impact vs. inspanning).
24. Semantische zoekfunctionaliteit (Graph-agent) uitwerken of evalueren als apart experiment.

---

## 10. Eindconclusie

### Toont deze versie dat de student in de juiste richting werkt?

**Ja.** Het systeem werkt, de architectuurkeuze is verdedigbaar, de evaluatie is concreet en de student begrijpt de zwakke punten van zijn eigen prototype. Een promotor kan hier voldoende in zien om de richting te bevestigen.

### Wat verhindert dat dit een sterke eindversie is?

De scriptie mist op dit moment twee dingen tegelijk: **academische omkadering** (citaties, literatuur, gerelateerd werk) en **figuren**. Zonder die twee elementen ziet het er academisch onafgewerkt uit, ongeacht hoe goed het prototype is.

### De 5 grootste tekortkomingen

1. **Bibliografie is sjabloonmateriaal** — dit is de meest kritische tekortkoming. Een literatuurhoofdstuk zonder relevante bronnen is geen literatuurhoofdstuk.
2. **Geen architectuurdiagram** — een architectuurhoofdstuk dat enkel uit tekst bestaat is fundamenteel onvolledig voor een ingenieursmasterproef.
3. **Conclusie ontbreekt** in het gecompileerde PDF — de scriptie eindigt nu feitelijk zonder conclusie.
4. **Geen baseline-vergelijking** in de evaluatie — hierdoor zijn de resultaten op zichzelf staand maar niet contextueel interpreteerbaar.
5. **Geen gerelateerd werk** — de student situeert zijn eigen bijdrage niet in het academische en industriële landschap. Een jury zal altijd vragen: "Hoe verhoudt jouw aanpak zich tot bestaande oplossingen?"

### Wat absoluut nog verbeterd moet worden bij beperkte tijd?

In volgorde van prioriteit:

1. **Schrijf de conclusie uit** en zet ze aan in `main.tex`. Beantwoord de vier onderzoeksvragen expliciet met cijfers uit de evaluatie.
2. **Voeg een architectuurdiagram toe** — minimaal één overzichtsfiguur van de gelaagde architectuur.
3. **Vervang de bibliografie** en voeg citaties toe doorheen de tekst, minstens in de literatuurstudie.
4. **Verwijder alle informele commentaren** en open TODO's uit de broncode.
5. **Voeg een "gerelateerd werk"-subsectie toe** in de literatuurstudie: waarom is dit systeem anders dan M365 Copilot of Elastic?

---

### Brutale eindschatting

Dit is een scriptie die technisch **boven het gemiddelde** scoort voor een eerste versie, maar academisch **ver onder het gemiddelde**. Het prototype en de evaluatie zijn degelijk werk. Maar de omkadering — bronnen, literatuurverwerking, figuren, conclusie — zit op het niveau van een sjabloon dat nog niet ingevuld is. Als deze versie nu ingediend zou worden, zou een jury de technische kant waarderen en de academische kant afkeuren. Dat verschil moet in de volgende versie volledig overbrugd worden.
