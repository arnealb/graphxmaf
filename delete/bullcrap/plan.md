# Literatuurbronnen — Orchestrator Planning Architecture

## Directe fundamenten van de gekozen aanpak

### 1. ReAct: Synergizing Reasoning and Acting in Language Models
**Auteurs:** Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y.
**Publicatie:** ICLR 2023
**Link:** https://arxiv.org/abs/2210.03629

**Relevantie:** Fundamenteel paper dat laat zien dat LLMs beter presteren wanneer ze reasoning traces en acties afwisselen in plaats van ze apart te behandelen. Jouw plan-then-execute aanpak bouwt hierop voort: de planningsfase is in essentie een gestructureerde reasoning trace, en de executiefase combineert reasoning met tool-acties. ReAct toont aan dat deze synergie hallucinations vermindert en interpreteerbaarheid verhoogt — precies de motivatie voor het scheiden van planning en executie.

---

### 2. HuggingGPT: Solving AI Tasks with ChatGPT and its Friends in Hugging Face
**Auteurs:** Shen, Y., Song, K., Tan, X., Li, D., Lu, W., & Zhuang, Y.
**Publicatie:** NeurIPS 2023
**Link:** https://arxiv.org/abs/2303.17580

**Relevantie:** Dit is het meest directe precedent voor jouw architectuur. HuggingGPT gebruikt exact hetzelfde vier-fasen patroon: (1) task planning — de LLM parseert de user request in een takenlijst met execution order en dependencies, (2) model selection — toewijzing aan expert-agents, (3) task execution, (4) response generation (synthese). Het verschil is dat jij MCP-agents als executors gebruikt in plaats van Hugging Face-modellen, maar het orchestratiepatroon is identiek.

---

### 3. Agent-Oriented Planning in Multi-Agent Systems (AOP)
**Auteurs:** Zhang, Y. et al.
**Publicatie:** ICLR 2025
**Link:** https://arxiv.org/abs/2410.02189

**Relevantie:** Formaliseert drie designprincipes voor task planning in multi-agent systemen: *solvability* (elke subtaak moet oplosbaar zijn door de toegewezen agent), *completeness* (alle aspecten van de query moeten gedekt zijn), en *non-redundancy* (geen overbodige subtaken). Dit paper valideert jouw keuze om planning en toewijzing te combineren in één stap (ze tonen experimenteel aan dat dit beter werkt dan ze te scheiden). De `depends_on`-structuur in jouw plan-schema sluit direct aan bij hun "structured decomposition of tasks" met expliciete dependencies.

---

### 4. Least-to-Most Prompting Enables Complex Reasoning in Large Language Models
**Auteurs:** Zhou, D., Schärli, N., Hou, L., Wei, J., Scales, N., Wang, X., Schuurmans, D., Cui, C., Bousquet, O., Le, Q., & Chi, E.
**Publicatie:** ICLR 2023
**Link:** https://arxiv.org/abs/2205.10625

**Relevantie:** Introduceert het twee-fasen decompositiepatroon dat je gebruikt: eerst een complex probleem opsplitsen in deelproblemen, dan de deelproblemen sequentieel oplossen waarbij antwoorden van eerdere stappen beschikbaar zijn voor latere stappen. Jouw `depends_on`-mechanisme is een generalisatie hiervan naar een DAG-structuur in plaats van een lineaire keten.

---

### 5. Decomposed Prompting: A Modular Approach for Solving Complex Tasks
**Auteurs:** Khot, T., Trivedi, H., Finlayson, M., Fu, Y., Richardson, K., Clark, P., & Sabharwal, A.
**Publicatie:** ICLR 2023
**Link:** https://arxiv.org/abs/2210.02406

**Relevantie:** Formaliseert het idee van modulaire decompositie: complexe taken opsplitsen in subtaken die elk worden gedelegeerd aan een gespecialiseerde "sub-task handler." Dit is precies wat jouw orchestrator doet — elke sub-agent (graph, salesforce, smartsales) is een gespecialiseerde handler. Het paper toont aan dat modulaire decompositie beter generaliseert dan monolithische chain-of-thought, vooral bij toenemende complexiteit.

---

## Bredere context en surveys

### 6. Chain-of-Thought Prompting Elicits Reasoning in Large Language Models
**Auteurs:** Wei, J., Wang, X., Schuurmans, D., Bosma, M., Ichter, B., Xia, F., Chi, E., Le, Q., & Zhou, D.
**Publicatie:** NeurIPS 2022
**Link:** https://arxiv.org/abs/2201.11903

**Relevantie:** Het fundament waarop alle bovenstaande papers voortbouwen. Jouw planningsfase is in essentie een gestructureerde variant van chain-of-thought: in plaats van vrije reasoning traces forceer je de LLM om zijn redenering in een JSON-schema te gieten.

---

### 7. LLM-Based Multi-Agent Systems for Software Engineering: Literature Review, Vision, and the Road Ahead
**Auteurs:** Rasheed, Z. et al.
**Publicatie:** ACM Transactions on Software Engineering and Methodology, 2025
**Link:** https://dl.acm.org/doi/10.1145/3712003

**Relevantie:** Uitgebreide survey over LLM-based multi-agent systemen. Biedt context voor waar jouw systeem in het bredere landschap past: een LMA-systeem met gespecialiseerde agents en een meta-agent (orchestrator) die coördinatie verzorgt.

---

### 8. TDAG: A Multi-Agent Framework based on Dynamic Task Decomposition and Agent Generation
**Link:** https://arxiv.org/abs/2402.10178

**Relevantie:** Toont een vergelijkbaar patroon van dynamische taakdecompositie met agent-toewijzing, maar gaat een stap verder door agents on-the-fly te genereren. Nuttig als contrastpunt om jouw keuze voor vaste, voorgedefinieerde agents te motiveren (eenvoudiger, voorspelbaarder, minder overhead).

---

## Hoe deze bronnen jouw keuzes onderbouwen

| Ontwerpkeuze | Onderbouwd door |
|---|---|
| Plan-then-execute (twee fasen) | HuggingGPT, Least-to-Most, Decomposed Prompting |
| LLM als planner én executor | ReAct, HuggingGPT |
| Gestructureerd JSON plan-schema | AOP (structured decomposition), HuggingGPT (task list met dependencies) |
| Dependencies tussen stappen (DAG) | AOP, Least-to-Most, Decomposed Prompting |
| Gespecialiseerde sub-agents | HuggingGPT (expert models), Decomposed Prompting (sub-task handlers), AOP |
| Logging van plannen voor debugging | ReAct (interpretable trajectories) |
| Synthese als aparte stap | HuggingGPT (response generation stage) |

---

## Aanbevolen citaatvolgorde in thesis

Begin met **Chain-of-Thought** (Wei et al., 2022) als vertrekpunt voor LLM-reasoning. Introduceer dan **ReAct** (Yao et al., 2023) om te laten zien dat reasoning en acting gecombineerd moeten worden. Verwijs naar **Least-to-Most** (Zhou et al., 2023) en **Decomposed Prompting** (Khot et al., 2023) voor de theoretische basis van taakdecompositie. Gebruik **HuggingGPT** (Shen et al., 2023) als het meest directe architecturele precedent. Verwijs naar **AOP** (Zhang et al., 2025) voor de formele designprincipes die je plan-schema valideren.