
- iets van ik vind geen entries met rrne -> bedoel je arne? 
- shortcut planning orchestrator vor single agent queries

---


  1. Sub-agent system prompts verbeteren (hoogste ROI)
  De eval toont welke categorieën laag scoren. SmartSales orders/catalog scoorden 2-3/5 — waarschijnlijk omdat de SmartSales agent niet weet hoe hij de tools correct moet aanroepen. --service smartsales geeft je nu precies die data. Dit is de directe weg naar hogere llm_scores.

  2. Structured output voor de planner (betrouwbaarheid)
  Vervang de vrije JSON-output van de planner door Azure OpenAI's response_format={"type": "json_object"}. Minder parse-fouten, geen markdown-stripping meer nodig.

  3. Ablation study als thesis-bijdrage (academisch sterkst)
  Je hebt al: baseline (wat?) vs v1-planning-orchestrator. Voeg toe:
  - --service salesforce direct vs via orchestrator → kwantificeer wat de planning/synthesis overhead kost in latency + tokens + kwaliteit
  - Dat is een echte empirische vergelijking die publiceerbaar is

  4. Retry met feedback op falende stappen (architectureel interessant)
  Als een stap faalt, geef de foutmelding terug aan de planner voor een herplanning. Dat is het "reflection" pattern uit de literatuur (ReAct / Reflexion) — goed te verwijzen naar bestaand onderzoek.


09:29:24  ERROR     agents.planning_orchestrator — Planning failed: Failed to produce a valid plan after 2 attempts: 'steps' must not be empty