# Literatuurbronnen — LLM-gebaseerde agentselectie als valide ontwerpkeuze

Dit bestand onderbouwt waarom volledig LLM-gebaseerde routing (geen rule-based classifier of keyword-filter) een wetenschappelijk verdedigbare keuze is in multi-agent systemen. De bronnen tonen aan dat dit het dominante patroon is in zowel academisch onderzoek als industriële implementaties.

---

## Directe onderbouwing

### 1. AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation
**Auteurs:** Wu, Q., Bansal, G., Zhang, J., Wu, Y., Zhang, S., Zhu, E., Li, B., Jiang, L., Zhang, X., & Wang, C.
**Publicatie:** arXiv 2023 / ICLR 2024
**Link:** https://arxiv.org/abs/2308.08155

**Relevantie:** Microsoft Research's AutoGen-framework is het meest geciteerde multi-agent framework en gebruikt uitsluitend LLM-gebaseerde agentselectie en handoffs. Er is geen rule-based router aanwezig: de LLM beslist op basis van de conversatie-context welke agent de volgende boodschap ontvangt. AutoGen valideert hiermee dat LLM-gebaseerde routing schaalbaar en robuust is voor complexe enterprise-scenario's. Jouw aanpak volgt exact dit patroon, maar voegt een gestructureerd JSON-plan toe als extra laag van interpreteerbaarheid.

---

### 2. Gorilla: Large Language Model Connected with Massive APIs
**Auteurs:** Patil, S.G., Zhang, T., Wang, X., & Gonzalez, J.E.
**Publicatie:** arXiv 2023
**Link:** https://arxiv.org/abs/2305.15334

**Relevantie:** Gorilla toont aan dat LLMs in staat zijn om uit duizenden API-beschrijvingen de juiste API te selecteren op basis van een natuurlijk-taalbeschrijving, zonder keyword-matching of rule-based filtering. De centrale bijdrage is dat semantisch begrip van API-beschrijvingen betere selectie oplevert dan handmatige classificatieschema's. Dit is de theoretische grondslag voor waarom jouw aanpak — het meegeven van agent-beschrijvingen aan de planner-LLM — een valide selectiemethode is: de LLM begrijpt de semantische scope van elke agent.

---

### 3. ToolLLM: Facilitating Large Language Models to Master 16000+ Real-world APIs
**Auteurs:** Qin, Y., Liang, S., Ye, Y., Zhu, K., Yan, L., Lu, Y., Lin, Y., Cong, X., Tang, X., Qian, B., Zhao, S., Tian, R., Xie, R., Zhou, J., Gerstein, M., Li, D., Liu, Z., & Sun, M.
**Publicatie:** ICLR 2024
**Link:** https://arxiv.org/abs/2307.16789

**Relevantie:** ToolLLM schijnt aan dat LLM-gebaseerde toolselectie (analoog aan jouw agentselectie) opschaalbaar is naar duizenden tools zonder expliciete routing-regels. De sleutel is de kwaliteit van de tool-beschrijving, niet de aanwezigheid van een classifier. Dit valideert jouw keuze om agentselectie te sturen via de `_available_agents_description()`-functie en de gedetailleerde `PLAN_SYSTEM_PROMPT` in plaats van via een regelset.

---

### 4. Toolformer: Language Models Can Teach Themselves to Use Tools
**Auteurs:** Schick, T., Dwivedi-Sahr, J., Dessì, R., Raileanu, R., Lomeli, M., Zettlemoyer, L., Cancedda, N., & Scialom, T.
**Publicatie:** NeurIPS 2023
**Link:** https://arxiv.org/abs/2302.04761

**Relevantie:** Toolformer toont aan dat LLMs zelfstandig kunnen leren wanneer en welke tool aan te roepen op basis van context, zonder expliciete regels of supervisie per tool. Dit ondersteunt de keuze om agentselectie aan het LLM over te laten: het model heeft het vermogen om contextueel de juiste bron te selecteren op basis van de aard van de vraag.

---

### 5. TaskMatrix.AI: Completing Tasks by Connecting Foundation Models with Millions of APIs
**Auteurs:** Liang, Y., Wu, C., Song, T., Wu, W., Xia, Y., Liu, Y., Ou, Y., Lu, S., Ji, L., Mao, S., Wang, Y., Shou, L., Gong, M., & Duan, N.
**Publicatie:** arXiv 2023
**Link:** https://arxiv.org/abs/2303.16434

**Relevantie:** Microsoft Research-paper dat expliciet kiest voor LLM-gebaseerde API-selectie boven keyword-routing of intent-classifiers, met als argument dat een foundation model API-beschrijvingen semantisch kan vergelijken met de gebruikersvraag. De paper introduceert een "Action Executor" die sterk lijkt op jouw PlanningOrchestrator: selecteer op basis van beschrijving, voer uit, synthetiseer. De auteurs rechtvaardigen de keuze voor LLM-routing expliciet op basis van flexibiliteit en aanpasbaarheid bij uitbreiding met nieuwe APIs.

---

## Productiesystemen die LLM-routing valideren

### 6. LangGraph: Building Stateful, Multi-Actor Applications with LLMs
**Auteurs/Organisatie:** LangChain Inc.
**Publicatie:** Technische documentatie + blog, 2024
**Link:** https://langchain-ai.github.io/langgraph/

**Relevantie:** LangGraph is het meest gebruikte productie-framework voor multi-agent systemen en gebruikt LLM-gebaseerde routing als standaardpatroon via "conditional edges". Er is geen ingebouwde rule-based classifier: de LLM beslist bij elke stap welke node (agent) als volgende wordt geactiveerd. De expliciete ontwerpkeuze van LangGraph voor LLM-routing in productie-applicaties valideert dat dit patroon voldoende betrouwbaar is voor enterprise-gebruik.

---

### 7. OpenAI Assistants API: Function Calling and Tool Use
**Auteurs/Organisatie:** OpenAI
**Publicatie:** API-documentatie, 2023–2024
**Link:** https://platform.openai.com/docs/assistants/tools

**Relevantie:** OpenAI's eigen productie-API gebruikt uitsluitend LLM-gebaseerde toolselectie: het model beslist zelf welke function call te maken op basis van de tool-beschrijvingen. Er is bewust geen rule-based selector gebouwd bovenop dit mechanisme. Dit bevestigt dat LLM-gebaseerde routing industrieel de standaard is.

---

## Trade-offs en eerlijke beperkingen

### 8. AgentBench: Evaluating LLMs as Agents
**Auteurs:** Liu, X., Yu, H., Zhang, H., Xu, Y., Lei, X., Lai, H., Gu, Y., Ding, H., Men, K., Yang, K., Zhang, S., Deng, Z., Zeng, A., Du, Z., Zhang, C., Shen, S., Zhang, T., Su, Y., Sun, H., Huang, M., Dong, Y., & Tang, J.
**Publicatie:** ICLR 2024
**Link:** https://arxiv.org/abs/2308.03688

**Relevantie:** AgentBench benchmarkt LLMs als agents op redeneer- en planningtaken en toont aan dat LLM-routing betrouwbaar presteert op gestructureerde taken maar gevoelig blijft voor prompt-formulering en randgevallen. Dit paper ondersteunt de eerlijke positionering: LLM-routing is valide en schaalbaar, maar vereist een zorgvuldig opgestelde systemprompt en een empirische evaluatie van routeringskwaliteit — precies wat jouw routing precision/recall metrics meten.

---

## Hoe deze bronnen jouw keuze onderbouwen

| Claim in thesis | Onderbouwing |
|---|---|
| LLM-routing is een valide, gangbare aanpak | AutoGen, LangGraph, OpenAI Assistants API |
| Semantische agent-beschrijvingen zijn voldoende voor correcte selectie | Gorilla, ToolLLM, TaskMatrix.AI |
| Een rule-based classifier is niet noodzakelijk voor een eersteprototype | Toolformer, AutoGen, TaskMatrix.AI |
| LLM-routing heeft inherente beperkingen (niet-determinisme, randgevallen) | AgentBench |
| Empirische routing-evaluatie (precision/recall) is de juiste validatiemethode | AgentBench, ToolLLM |

---

## Aanbevolen formulering in thesis (§4.5 of §5.x)

> "De agentselectie wordt volledig door de plannercomponent bepaald op basis van de beschrijvingen van beschikbare agents en de gebruikersvraag, zonder tussenkomst van een rule-based classifier of keyword-filter. Deze keuze sluit aan bij het dominante patroon in recente multi-agent frameworks: zowel AutoGen \cite{wu2023autogen} als LangGraph gebruiken LLM-gebaseerde routing als standaardmechanisme, met als voornaamste argument de flexibiliteit bij het toevoegen van nieuwe agents en de capaciteit van foundation models om semantische overeenkomsten tussen agentrollen en querytypes te herkennen \cite{patil2023gorilla, liang2023taskmatrix}. De betrouwbaarheid van dit mechanisme wordt in dit onderzoek empirisch geëvalueerd via routeringsprecision en -recall op een testset van 88 queries."
