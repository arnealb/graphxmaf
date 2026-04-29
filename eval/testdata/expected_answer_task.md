# Taak: expected_answer invullen voor nieuwe prompts

## Context
We vullen `eval/prompts.json` en `eval/all_prompts.json` aan met correcte `expected_answer` velden
voor alle nieuwe prompts (categorieën: `entity-centric1`, `entity-centric2`, `implicit-cross-system`).

Deze prompts dienen als benchmark voor een **GraphRAG** verbetering op het huidige multi-agent systeem.
Het huidige prototype is de **baseline** — het zal op bepaalde prompts falen of onvolledige antwoorden geven.
De `expected_answer` beschrijft het **ideale correcte antwoord**, niet wat het prototype nu geeft.

---

## Werkwijze

**Source of truth = `eval/testdata/overzicht.json` (of overzicht.md)**

1. Gebruik overzicht.json om te bepalen wat er in een correct antwoord moet zitten
2. Het prototype-antwoord dient **uitsluitend** om pre-existing data te identificeren
   (data die in het systeem zit maar niet in het overzicht staat, bv. `supp_opportyunity`, `supplier1_contact lastname`)
3. Pre-existing data → zet in expected_answer als "Additional pre-existing data is acceptable"
4. Als het prototype iets mist → staat toch in de expected_answer (het is een verwachte fout van de baseline)
5. Als het prototype iets fout geeft → corrigeer dit expliciet in de expected_answer

**Dit is een GraphRAG benchmark — de baseline mag falen. De expected_answer is het doel, niet de huidige staat.**

---

## Format expected_answer

- Kort en scanbaar — geen gigantisch tekstblok
- Per systeem (SF / Graph / SmartSales) apart indien van toepassing
- Concrete entiteitsnamen, bedragen, datums uit overzicht.json
- Eindig met scoringsregels indien nuttig (bv. "Missing Graph entirely = max 3")

---

## Workflow per prompt

De gebruiker geeft:
- De prompttekst
- Het antwoord van het prototype

Jij doet:
1. Zoek de relevante entiteiten op in overzicht.json
2. Stel expected_answer op op basis van overzicht (NIET op basis van prototype)
3. Gebruik prototype enkel om pre-existing data te spotten
4. Schrijf de expected_answer in het afgesproken format
5. Update zowel `eval/prompts.json` als `eval/all_prompts.json`

---

## Nog te doen (31 prompts)

### entity-centric1 (10 nog te doen)
- [ ] Give me a full briefing on Colruyt.
- [ ] What is the current status of our relationship with supplier1?
- [x] Who is Dorian and how do we work with him? — expected_agents: graph + salesforce only (SS is optionele bonus)
- [ ] Give me a complete overview of everything related to Arne.
- [ ] What do we know about GreenTech Solutions?
- [x] Prepare me for my next meeting. What do I have coming up and what do I know about the companies involved?
- [ ] Who are the most important companies we work with right now?
- [ ] Is there anything I should follow up on today?
- [ ] Give me a 360 view of the most recent email sender.
- [ ] ~~Tell me everything you know about supplier1.~~ ✓

### entity-centric2 (11 nog te doen)
- [ ] What files, meetings, and deals are linked to supplier1?
- [ ] Show me everything related to Belgium across all our systems.
- [ ] What is the full picture of our top open deal?
- [ ] How active have we been with supplier1 over the past month?
- [ ] Find everything related to the word 'nutella' across all our systems.
- [ ] Give me a summary of all activity related to my next calendar event.
- [ ] Which companies appear both in our CRM and in our email history?
- [ ] What locations do we have and what deals are linked to them?
- [ ] Tell me about the companies behind my open support cases.
- [ ] What do I need to know about the people I have meetings with this week?
- [ ] Give me a full picture of our commercial activity in Brussels.

### implicit-cross-system (10 nog te doen)
- [ ] Who is the contact person behind my most expensive open order?
- [ ] Which of my recent email senders also have an active deal with us?
- [ ] Are there companies in my upcoming calendar that we have no record of?
- [ ] Which companies that emailed me recently do not seem to have a location registered with us?
- [ ] For the company behind my most recent open support case, what else do we know about them?
- [ ] What is the total order value for companies that currently have an open support case?
- [ ] Which companies am I meeting this week that have no active deal with us?
- [ ] For each person I have a meeting with this week, give me everything we know about them.
- [ ] Which of our accounts have both an active deal and a recent order?
- [ ] Find any files we have related to our most valuable open deal and summarise them.

---

## Relevante bestanden
- `eval/prompts.json` — primaire prompts file
- `eval/all_prompts.json` — sync met prompts.json (altijd beide updaten)
- `eval/testdata/overzicht.json` — ground truth data (source of truth)
- `eval/testdata/overzicht.md` — leesbare versie van overzicht.json
- `smartsales/info/jemoeder.json` — raw SmartSales API responses voor pre-existing locaties (supplier1, Customer1) en een testorder. Bevat o.a. Customer1 adres (Markt 5, Bruges, 8000).

## Extra noten
- De SmartSales catalog is een **gedeelde catalogus** — alle items zijn zichtbaar voor alle queries, niet gefilterd per locatie. Een correct antwoord toont enkel items die gelinkt zijn aan de gevraagde entiteit via orders of code. Volledige catalogus tonen = information overload = minor deduction.
