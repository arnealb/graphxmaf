Hier is een overzicht van de sterkste bronnen, gestructureerd zodat je ze direct in je literatuurstudie kunt gebruiken:

---

## Literatuurbronnen voor jouw thesis

### Laag 1 — Waarom RAG nodig is (LLM-beperkingen)

**Kernprobleem:** LLMs hallucineren, hebben een knowledge cutoff, en kennen geen private bedrijfsdata.

- **Lewis et al. (2020)** — *"Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"* (NeurIPS 2020) — de originele RAG paper van Facebook AI. Dit is dé grondslag, elke thesis over RAG citeert dit. → `arxiv.org/abs/2005.11401`

- RAG pakt het probleem van hallucinaties aan door de trainingsdata van een LLM aan te vullen met actuele informatie uit externe bronnen via een retrievalmodel — zonder het model opnieuw te hoeven trainen. Dit maakt RAG zowel flexibel als schaalbaar.

- In domeinen zoals corporate governance, HR en finance is kritieke informatie vaak vervat in gestructureerde records, beleidsdocumenten en tabelformaten die LLMs niet van nature kunnen verwerken na deployment. RAG-frameworks pakken dit aan door retrieval te integreren met LLMs, zodat modellen externe kennis kunnen ophalen op het moment van inference.

- **Survey:** Fan et al. (2024) — *"A Survey on RAG Meeting LLMs"* → `arxiv.org/abs/2405.06211` (breed overzicht van RAG-architecturen, training en toepassingen)

---

### Laag 2 — Waarom gewone RAG niet volstaat (beperkingen van vector RAG)

- Een fundamentele beperking van traditionele RAG is dat het systeem verbanden tussen gerelateerde kennispunten niet robuust kan leggen, wat leidt tot gefragmenteerd begrip en verminderde effectiviteit bij domeinspecifieke expertise.

- Bij directe beantwoording door LLMs kunnen antwoorden oppervlakkig of weinig specifiek zijn. RAG pakt dit aan door relevante tekstuele informatie op te halen, maar worstelt nog steeds met de flexibele, natuurlijke taaluitdrukking van entiteitsrelaties — waardoor het bijv. moeilijkheden heeft met "invloed"-relaties die de kern van een vraag vormen.

- Traditionele RAG is beperkt tot single-hop retrieval en heeft moeite met vragen die inzicht in relaties vereisen of die informatie over meerdere documenten heen moeten samenvatten.

---

### Laag 3 — Waarom Graph RAG de juiste keuze is

**De sleutelpaper:** Edge et al. (2024) — *"From Local to Global: A Graph RAG Approach to Query-Focused Summarization"* — Microsoft Research, gepubliceerd april 2024, al 900+ citaties. → `arxiv.org/abs/2404.16130`

- RAG faalt bij globale vragen gericht op een volledig tekstcorpus — zoals "wat zijn de hoofdthema's in de dataset?" — omdat dit inherent een query-focused summarisatietaak is, geen expliciete retrievaltaak. GraphRAG combineert de sterktes van beide methoden via een graafgebaseerde aanpak die schaalt met zowel de algemeenheid van gebruikersvragen als de hoeveelheid brontekst.

- GraphRAG pakt de beperkingen van traditionele RAG aan via drie kerninnovaties: (i) graafgestructureerde kennisrepresentatie die entiteitsrelaties en domeinh iërarchieën expliciet vastlegt, (ii) efficiënte graafgebaseerde retrievaltechnieken die context-bewarende retrieval met multi-hop redeneervermogens mogelijk maken, en (iii) structuurbewuste kennisintegratie-algoritmen.

- Voor jouw specifieke uitbreidingsidee (entiteitsresolutie): toekomstige GraphRAG-systemen zullen contextuele disambiguatie gebruiken — via naburige knooppunten — en cross-document entity linking, waardoor "Apple Inc." en "Apple" automatisch samengevoegd worden wanneer dat passend is.

**Twee aanvullende surveys:**
- Peng et al. (2024) — *"Graph Retrieval-Augmented Generation: A Survey"* → `arxiv.org/abs/2408.08921`
- He et al. (2025) — *"A Survey of Graph Retrieval-Augmented Generation for Customized LLMs"* → `arxiv.org/abs/2501.13958`

---

### Hoe je dit opbouwt in je thesis

```
1. LLMs hebben inherente beperkingen (hallucination, cutoff, geen private data)
   → Lewis et al. 2020, Fan et al. 2024

2. RAG lost dit op, maar vector RAG schiet tekort bij complexe/relationele vragen
   → Survey Peng et al. 2024, He et al. 2025

3. Graph RAG lost precies die beperkingen op + schaalt naar enterprise use cases
   → Edge et al. 2024 (Microsoft) ← dit is je sterkste troef

4. Jouw specifieke case: entiteitsresolutie over systemen heen
   → Onderbouw met entity disambiguation literatuur uit de KG-surveys
```

Wil je dat ik de exacte citaten in LaTeX/BibTeX formaat zet zodat je ze direct in je thesis kunt plakken?


+++++++++++++++++++++++++++++++++==++++++++++++++++++
  Huidige situatie                                                                                                                                                                                                                                                                                 
                                                                                                                                                                                                                                                                                                   
  De graph agent heeft al OneDrive tools:                                                                                                                                                                                                                                                          
  - search_files → KQL keyword search → geeft metadata terug                                                                                                                                                                                                                                       
  - read_file / read_multiple_files → leest volledige documentinhoud (max 12.000 chars)                                                                                                                                                                                                            
                                                                                                                                                                                                                                                                                                   
  Het "zoek + lees" patroon bestaat dus al. De vraag is: waarom werkt dit nog niet voor de onedrive-rag prompts?                                                                                                                                                                                 
                                                                                                                                                                                                                                                                                                 
  Twee problemen:
  1. KQL keyword search is fragiel — "What should I do if my car gets damaged?" → welk keyword stuur je naar OneDrive? arbeidsreglement? Het document heet zo maar de query niet.
  2. Full-doc retrieval is inefficiënt — je gooit het hele document in de context, terwijl je maar één paragraaf nodig hebt.

  ---
  Wat GraphRAG hier betekent

  Voor de 6 onedrive-rag prompts is geen full Microsoft GraphRAG (entiteiten, kennisgraaf, communities) nodig. Wat je nodig hebt is vector RAG over OneDrive documents:

  Offline (index fase):
    OneDrive docs → chunk → embed → lokale vector store

  Online (query fase):
    vraag → embed → similarity search → relevante chunks → LLM antwoord

  ---
  Architectuur: nieuwe server of uitbreiding?

  Aanbeveling: extend de bestaande graph module, geen nieuwe agent.

  Redenen:
  - Graph auth is al aanwezig in de graph module
  - De graph agent weet al van OneDrive af
  - Het is conceptueel een betere zoekmethode voor hetzelfde domein, geen nieuw systeem
  - Nieuw agent = extra complexiteit in orchestrator, planner, startup

  Wat er bij moet komen:

  graph/
    rag_index.py      ← indexer: crawl OneDrive, chunk, embed, sla op in ChromaDB
    rag_searcher.py   ← zoek via vector similarity, return relevante chunks + source
    tools.yaml        ← nieuw tool: search_documents (vervangt/aanvult search_files voor policy/doc queries)

  Het nieuwe tool search_documents zou:
  1. Query embedden via Azure OpenAI
  2. Similarity search in lokale ChromaDB
  3. Top-k chunks teruggeven met bestandsnaam + fragment

  ---
  Vereisten voor testdata

  Voordat dit werkt, moeten de OneDrive documenten effectief aanwezig zijn in de test M365-omgeving:
  - arbeidsreglement_easi_group.docx
  - onkostenbeleid_easi_group.docx
  - raamovereenkomst_easi_supplier1.docx
  - samenwerkingsovereenkomst_easi_colruyt.docx
  - procedure_klachtenafhandeling_easi.docx
  - onboarding_gids_easi.docx

  Zijn deze documenten al aangemaakt en staan ze in OneDrive? Dit is de bottleneck voor de onedrive-rag prompts — zonder testdata kan je indexer niets vinden.

  ---
  Implementatievolgorde

  1. Maak de 6 testdocumenten aan in OneDrive (als dat nog niet is gedaan)
  2. graph/rag_index.py — indexeer alle OneDrive docs naar ChromaDB
  3. graph/rag_searcher.py — vector zoekfunctie
  4. Nieuw search_documents tool in tools.yaml + handler in mcp_router.py
  5. Update planner prompt: document/policy vragen → gebruik search_documents ipv search_files

  Wil je beginnen met de implementatie van de indexer, of is er nog onduidelijkheid over de testdata?