# Test Data Requirements — Entity-Centric Prompts

Status per systeem:
- **Salesforce** ✅ alles aangemaakt via notebook
- **SmartSales** ✅ locaties, catalog items en orders aangemaakt via notebook
- **Microsoft 365** ⬜ manueel aan te maken (zie checklist hieronder)

---

## M365 — Manueel aan te maken

### Emails (Outlook)
Maak deze emails aan in je inbox. Afzender en subject zijn belangrijk voor de agent.

| # | Afzender | Subject | Entiteit |
|---|----------|---------|----------|
| ⬜ | `marc.supplier@supplier1.be` (Marc Supplier) | `Follow-up: supplier1 Q2 2026 Delivery Contract` | supplier1 |
| ⬜ | `marc.supplier@supplier1.be` (Marc Supplier) | `supplier1 — Updated pricing for H2 2026` | supplier1 |
| ⬜ | `procurement@colruyt.be` (Colruyt Group Procurement) | `Colruyt Group — SmartSales pilot bevestiging` | Colruyt |
| ⬜ | `info@greentechsolutions.be` (GreenTech Solutions) | `GreenTech Solutions — Interest in sustainability dashboard` | GreenTech |
| ⬜ | `marketing@ferrero.be` (Ferrero Benelux Marketing) | `Ferrero Benelux — Nutella spring campaign inquiry` | Nutella |
| ⬜ | `d.feaux@easi.net` (Dorian Feaux) | `Intro: Dorian Feaux — EASI collaboration proposal` | Dorian |
| ⬜ | jouw eigen adres | `Belgium region — Q1 2026 commercial summary` | België + Brussel |

Minimale bodytekst per email:
- **supplier1 delivery**: vermeldt "supplier1", "Q2 2026", "April delay", "Brussels"
- **supplier1 pricing**: vermeldt "supplier1", "PROD-SUP1-001", "July 2026"
- **Colruyt**: vermeldt "Colruyt Group", "SmartSales", "Halle", "EUR 220,000"
- **GreenTech**: vermeldt "GreenTech Solutions", "Ghent", "sustainability dashboard", "EUR 2,500"
- **Nutella**: vermeldt "Ferrero Benelux", "Nutella", "Brussels", "display jars"
- **Dorian**: vermeldt "Dorian Feaux", "EASI", "Brussels", "Avenue Louise 65"
- **Belgium**: vermeldt "Belgium", "Brussels", "supplier1", "Colruyt", "Ferrero", "EUR 375,000"

---

### Calendar events (Outlook Calendar)
Maak deze afspraken aan in je eigen kalender. Geen attendees nodig — namen in de titel zijn voldoende.

| # | Subject | Start | Entiteit |
|---|---------|-------|----------|
| ⬜ | `supplier1 — Q2 Delivery Review` | 10 mei 2026, 10:00–11:00 | supplier1 |
| ⬜ | `Colruyt Group — SmartSales Rollout Kickoff` | 15 mei 2026, 14:00–15:30 | Colruyt |
| ⬜ | `GreenTech Solutions — Technical Qualification Call` | 12 mei 2026, 11:00–12:00 | GreenTech |
| ⬜ | `Weekly sync — Dorian Feaux` | 6 mei 2026, 09:00–09:30 | Dorian |
| ⬜ | `Sprint review — Arne Albrecht` | 8 mei 2026, 14:00–15:00 | Arne |

---

### OneDrive
Upload dit bestand naar je OneDrive root (kan gewoon via browser op onedrive.com).

| # | Bestandsnaam | Inhoud (verplichte termen) | Entiteit |
|---|--------------|---------------------------|----------|
| ⬜ | `supplier1_delivery_report_Q2_2026.txt` | "supplier1", "Q2 2026", "ORD-SUP1-2026-001", "delayed", "marc.supplier@supplier1.be" | supplier1 |

Voorbeeldinhoud:
```
supplier1 - Q2 Delivery Report
================================
Supplier: supplier1 (SUP-001)
Period: Q2 2026 (April–June)

Orders:
- ORD-SUP1-2026-001: 10x Industrial Components Pack @ EUR 149.99 = EUR 1499.90
  Status: Shipped (5 days delay — under investigation)

Open Issues:
- April batch arrived late. supplier1 quality review initiated.
- Contract renewal (supplier1 Q2 Delivery Contract) pending signature.

Contact: Marc Supplier <marc.supplier@supplier1.be>
```

---

## Volledige status per entiteit

| Entiteit | M365 emails | M365 events | M365 OneDrive | Salesforce | SmartSales |
|----------|-------------|-------------|---------------|------------|------------|
| supplier1 | ⬜ 2 emails | ⬜ 1 event | ⬜ 1 bestand | ✅ account + opp + case + contact | ✅ locatie + catalog item + order |
| Colruyt | ⬜ 1 email | ⬜ 1 event | — | ✅ account + opp + case | ✅ locatie + catalog item + order |
| GreenTech Solutions | ⬜ 1 email | ⬜ 1 event | — | ✅ account + opp | ✅ locatie + catalog item + order |
| Nutella / Ferrero | ⬜ 1 email | — | — | ✅ account + opp | ✅ locatie + catalog item + order |
| Dorian | ⬜ 1 email | ⬜ 1 event | — | ✅ contact | ✅ locatie (EASI) |
| Arne | — | ⬜ 1 event | — | ✅ contact | ✅ locatie (EASI) |
| België / Brussel | ⬜ 1 email | — | — | ✅ accounts in BE/BRU | ✅ locaties in Brussel |
