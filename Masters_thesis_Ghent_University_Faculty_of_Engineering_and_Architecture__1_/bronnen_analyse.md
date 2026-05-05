# Bronnenanalyse — technologieverkenning.pdf
## Overzicht van bruikbare bronnen voor de literatuurstudie

---

## Leeswijzer

De bronnen uit de technologieverkenning zijn ingedeeld in **drie niveaus**:

| Niveau | Beschrijving |
|--------|-------------|
| ✅ **Tier 1 — Must use** | Academische papers (ArXiv), officiële specificaties, white papers van primaire aanbieders. Direct citeerbaar in een masterproef. |
| ⚠️ **Tier 2 — Acceptable** | Officiële technische documentatie van Microsoft, Google, OpenAI. Aanvaardbaar in een ingenieursmasterproef als technische referentie. |
| ❌ **Tier 3 — Vermijden** | Medium-blogs, YouTube-video's, DataCamp-artikelen, persoonlijke blogs. Niet citeerbaar in een academische context. |

---

## Tier 1 — Must use (academisch sterk)

### 1. ReAct: Synergizing Reasoning and Acting in Language Models
- **Oorsprong in document:** Sectie "Belangrijke kenmerken van agents" — "het werd geïntroduceerd door Google Research in de paper *ReAct: Synergizing Reasoning and Acting in Language Models* (Yao et al., 2022)"
- **Wat het is:** Peer-reviewed paper op ArXiv door Google Research. Beschrijft het ReAct-patroon (Reason + Act) dat aan de basis ligt van moderne LLM-agents.
- **Link:** https://arxiv.org/abs/2210.03629
- **Waarom:** Elk agent framework in de scriptie (LangGraph, Semantic Kernel, MAF) bouwt op dit principe. De scriptie beschrijft agents als "redeneren en handelen" — dit is exact de ReAct paper. **Dit moet geciteerd worden.**
- **Aanbevolen voor sectie:** Literatuurstudie §1.3 (AI-agents)

---

### 2. ArXiv paper over multi-agent conflict en consensus (2407.12532)
- **Oorsprong in document:** Sectie "Conflict- en consensus afhandeling"
- **Wat het is:** Een academisch paper op ArXiv. Het exacte onderwerp is waarschijnlijk "A Survey on Multi-Agent Systems" of vergelijkbaar — het nummer 2407.12532 duidt op juli 2024.
- **Link:** https://arxiv.org/abs/2407.12532
- **Waarom:** Dit is de enige echte peer-reviewed bron in de lijst naast de ReAct paper. Relevant voor de verantwoording van de orchestrator/subagent-opsplitsing.
- **Aanbevolen voor sectie:** Literatuurstudie §1.3 (multi-agent systemen)
- **Actie:** Controleer wat dit paper juist bespreekt voor je het gebruikt.

---

### 3. Model Context Protocol — Officiële specificatie
- **Oorsprong in document:** Sectie "MCP Server/client architectuur"
- **Wat het is:** De officiële technische specificatie van het MCP-protocol, gepubliceerd door Anthropic op GitHub.
- **Link:** https://github.com/modelcontextprotocol/spec
- **Secundaire link (officiële website):** https://modelcontextprotocol.io/
- **Waarom:** MCP is een centraal onderdeel van de architectuur. De spec is de primaire bron. In een thesis citeer je de spec als technisch rapport/standaard.
- **Aanbevolen voor sectie:** Literatuurstudie §1.5 (MCP)

---

### 4. OpenAI — A Practical Guide to Building Agents
- **Oorsprong in document:** Sectie "Multi agent" — eerste bron
- **Wat het is:** Officieel white paper van OpenAI over agent-architecturen (PDF, gepubliceerd 23-10-2025).
- **Link:** https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf
- **Waarom:** OpenAI white paper. Bespreekt agent patterns, orchestratie, tool-gebruik en multi-agent samenwerking. Direct relevant voor hoofdstuk 1 van de scriptie. Citeerbaar als technisch rapport van een primaire aanbieder.
- **Aanbevolen voor sectie:** Literatuurstudie §1.3 (agents), §1.4 (frameworks)

---

## Tier 2 — Acceptable (officiële technische documentatie)

### 5. Google Cloud — What are AI agents?
- **Link:** https://cloud.google.com/discover/what-are-ai-agents
- **Waarom bruikbaar:** Officiële Google Cloud-documentatie. Beschrijft de kernkenmerken van AI-agents (Reasoning, Acting, Observing, Planning, Collaborating) zoals ook in de scriptie vermeld. Citeerbaar als technische bron.
- **Beperking:** Marketingpagina van Google — gebruik enkel voor definitie/kenmerken, niet als diepgaande analyse.
- **Aanbevolen voor sectie:** Literatuurstudie §1.3 (definitie AI-agent)

---

### 6. Microsoft Azure — AI Agent Design Patterns
- **Link:** https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns
- **Waarom bruikbaar:** Officiële Microsoft Azure-architectuurdocumentatie. Beschrijft de samenwerkingspatronen (sequential, parallel/swarm, orchestrator/supervisor) die ook in de scriptie worden gebruikt. Dit is de autoriteitsbron voor de patronen die je implementeert.
- **Aanbevolen voor sectie:** Literatuurstudie §1.3 (multi-agent patronen), Architectuurhoofdstuk

---

### 7. Microsoft — Semantic Kernel Overview
- **Link:** https://learn.microsoft.com/en-us/semantic-kernel/overview/
- **Aanvullende links:**
  - Concepts/Planning: https://learn.microsoft.com/en-us/semantic-kernel/concepts/planning
  - Plugins: https://learn.microsoft.com/en-us/semantic-kernel/concepts/plugins/
  - AI Connectors: https://devblogs.microsoft.com/semantic-kernel/understanding-semantic-kernel-ai-connectors
  - Kernel Memory: https://microsoft.github.io/kernel-memory
- **Waarom bruikbaar:** Officiële Microsoft-documentatie voor Semantic Kernel. Nodig voor de frameworkvergelijking in §1.4.
- **Aanbevolen voor sectie:** Literatuurstudie §1.4 (Semantic Kernel)

---

### 8. Microsoft — Microsoft Agent Framework (via VentureBeat)
- **Link:** https://venturebeat.com/ai/microsoft-retires-autogen-and-debuts-agent-framework-to-unify-and-govern
- **Waarom bruikbaar:** Beschrijft de lancering van Microsoft Agent Framework als opvolger van AutoGen. Dit is relevant omdat de scriptie dit framework gebruikt en de keuze ervoor moet verantwoorden. VentureBeat is geen academische bron maar is hier de enige primaire nieuwsbron over de lancering.
- **Aanvullen met:** Officiële AutoGen/Microsoft Agent Framework docs: https://microsoft.github.io/autogen/stable/
- **Aanbevolen voor sectie:** Literatuurstudie §1.4 (Microsoft Agent Framework)

---

### 9. Microsoft Azure — Introduction to Agents and MCP
- **Link:** https://learn.microsoft.com/en-us/azure/developer/ai/intro-agents-mcp
- **Waarom bruikbaar:** Officiële Microsoft-documentatie over het gebruik van MCP in combinatie met Azure AI. Direct relevant voor de implementatiekeuzes in de scriptie.
- **Aanbevolen voor sectie:** Literatuurstudie §1.5 (MCP), Implementatiehoofdstuk

---

### 10. HuggingFace — MCP Course (Unit 1: Architectuur & Communicatieprotocol)
- **Links:**
  - https://huggingface.co/learn/mcp-course/unit1/architectural-components
  - https://huggingface.co/learn/mcp-course/unit1/communication-protocol
- **Waarom bruikbaar:** HuggingFace is een gezaghebbende bron in de AI-gemeenschap. De cursus beschrijft de MCP-architectuur (host, client, server) en communicatieprotocollen (STDIO, HTTP-streaming) die ook in de scriptie staan.
- **Beperking:** Cursusmateriaal, geen peer-reviewed paper. Gebruik als aanvulling op de officiële MCP-spec.
- **Aanbevolen voor sectie:** Literatuurstudie §1.5 (MCP componenten en communicatie)

---

### 11. RedHat — MCP Security Risks and Controls
- **Link:** https://www.redhat.com/en/blog/model-context-protocol-mcp-understanding-security-risks-and-controls
- **Waarom bruikbaar:** RedHat is een gezaghebbende technische bron. Dit artikel bespreekt beveiligingsrisico's van MCP (verkeerde permissies, command injection, kwaadaardige servers) — exact de "gevaren" die ook in de technologieverkenning staan en relevant zijn voor §1.6 van de scriptie (governance).
- **Aanbevolen voor sectie:** Literatuurstudie §1.6 (veiligheidsrisico's MCP), Architectuurhoofdstuk §3.5

---

### 12. LangChain Blog — Multi-Agent Workflows
- **Links:**
  - https://blog.langchain.com/langgraph-multi-agent-workflows/
  - https://blog.langchain.com/how-and-when-to-build-multi-agent-systems
- **Waarom bruikbaar:** Officiële LangChain/LangGraph blog. Beschrijft wanneer en hoe multi-agent systemen te bouwen — relevant voor de frameworkvergelijking en de verantwoording van de architectuurkeuze.
- **Aanbevolen voor sectie:** Literatuurstudie §1.4 (LangGraph)

---

### 13. LangGraph Officiële Documentatie
- **Link:** https://docs.langchain.com/oss/python/langchain/overview
- **Waarom bruikbaar:** Officiële technische documentatie. Nodig voor de beschrijving van LangGraph in de frameworkvergelijking.
- **Aanbevolen voor sectie:** Literatuurstudie §1.4 (LangGraph)

---

## Tier 3 — Vermijden in de bibliografie

| Bron | Reden |
|------|-------|
| Medium-artikelen (diverse auteurs) | Niet peer-reviewed, wisselende kwaliteit, niet citeerbaar |
| YouTube-video's | Niet citeerbaar in een academische context |
| DataCamp blog | Commercieel leerplatform, geen academische bron |
| Confluent blog | Bedrijfsblog, niet citeerbaar |
| thecodestreet.dev | Onbekende auteur, geen academische waarde |
| medium.com/@saeedhajebi — LangGraph is not a true agentic framework | Interessante kritiek maar te informeel voor citatie |

> **Uitzondering:** Als je een specifieke technische claim wil ondersteunen die nergens anders staat, mag je een Medium-artikel in een voetnoot vermelden, maar **niet** in de officiële bibliografie.

---

## Wat ontbreekt en wat je nog moet toevoegen

De bronnenlijst uit de technologieverkenning dekt agent frameworks en MCP goed, maar mist bronnen voor andere cruciale secties van de scriptie:

### Ontbrekend: Enterprise Search
Er is geen enkele bron over enterprise search in de technologieverkenning. Voeg toe:
- **Aandousi et al. (2020)** of vergelijkbaar academisch werk over enterprise information retrieval
- Eventueel: Microsoft's eigen documentatie over Microsoft Search / M365 Copilot als afbakening van "bestaande oplossingen"

### Ontbrekend: LLM-achtergrond
- **Brown et al. (2020) — GPT-3**: "Language Models are Few-Shot Learners" — al in je `.bib`, maar moet ook effectief geciteerd worden
- **Lewis et al. (2020) — RAG**: "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" (ArXiv: 2005.11401) — essentieel want RAG is het alternatief voor tool-calling in enterprise search

### Ontbrekend: LLM-as-Judge evaluatiemethodologie
- **Zheng et al. (2023)** — "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena" (ArXiv: 2306.05685) — **dit moet geciteerd worden** want je gebruikt exact deze methode in je evaluatie

### Ontbrekend: Prompt Injection / Beveiliging
- **Perez & Ribeiro (2022)** — "Ignore Previous Prompt: Attack Techniques For Language Models" — relevant voor §2.4 (risico's) en §3.5 (veiligheid)

---

## Prioriteiten: wat eerst toevoegen

| # | Bron | Prioriteit | Reden |
|---|------|-----------|-------|
| 1 | Yao et al. (2022) ReAct — arxiv.org/abs/2210.03629 | 🔴 Kritisch | Wordt al bij naam geciteerd in de technologieverkenning, moet in de scriptie staan |
| 2 | ArXiv 2407.12532 | 🔴 Kritisch | Enige academische paper over MAS in je bronnen |
| 3 | Zheng et al. (2023) LLM-as-Judge — arxiv.org/abs/2306.05685 | 🔴 Kritisch | Jouw evaluatiemethode heeft een citaat nodig |
| 4 | MCP Officiële Spec (github.com/modelcontextprotocol/spec) | 🔴 Kritisch | Centrale technologie van de architectuur |
| 5 | OpenAI Practical Guide to Building Agents | 🟠 Hoog | White paper, dekt agents & multi-agent patronen |
| 6 | Microsoft Azure AI Agent Design Patterns | 🟠 Hoog | Dekt de orchestrator/subagent patronen die je gebruikt |
| 7 | Lewis et al. (2020) RAG — arxiv.org/abs/2005.11401 | 🟠 Hoog | RAG is relevant voor context in enterprise search |
| 8 | Semantic Kernel Docs (learn.microsoft.com) | 🟡 Gemiddeld | Nodig voor frameworkvergelijking |
| 9 | LangGraph/LangChain blog + docs | 🟡 Gemiddeld | Nodig voor frameworkvergelijking |
| 10 | RedHat — MCP Security | 🟡 Gemiddeld | Ondersteunt §1.6 en §3.5 over beveiliging |
| 11 | Google Cloud — What are AI agents | 🟡 Gemiddeld | Definitie van agent kenmerken |
| 12 | HuggingFace MCP Course | 🟢 Aanvullend | Ondersteuning voor MCP-architectuur uitleg |
| 13 | Microsoft Agent Framework (VentureBeat + AutoGen docs) | 🟢 Aanvullend | Achtergrond bij de keuze voor MAF |

---

## Snelle samenvatting

Van de bronnen in de technologieverkenning zijn er **4 echt academisch sterk** (Tier 1): de ReAct paper, het ArXiv MAS-paper, de MCP-spec en de OpenAI white paper. De rest zijn officiële technische documentaties die aanvaardbaar zijn in een ingenieursmasterproef maar geen vervanging zijn voor peer-reviewed werk.

**Het grootste gat** in de bronnenlijst is het ontbreken van:
1. Literatuur over enterprise search
2. Een citaat voor de LLM-as-judge evaluatiemethode (Zheng et al.)
3. De RAG-paper (Lewis et al.) als relevant alternatief voor de tool-calling aanpak

Deze drie ontbrekende bronnen vallen volledig buiten de technologieverkenning en moeten apart worden opgezocht.
