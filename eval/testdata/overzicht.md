# Testdata — Volledig Overzicht

> Bronnen: `testdata_setup.ipynb` · `testdata_fuzzy.ipynb` · `test_mails.py`  
> Mailbox: `smartadmin@easigroupdemo.onmicrosoft.com`  
> Systemen: **Salesforce** · **SmartSales** · **Microsoft 365** (Outlook + Calendar + OneDrive)

---

## Inhoudsopgave

1. [Salesforce](#salesforce)
2. [SmartSales](#smartsales)
3. [Microsoft 365](#microsoft-365)
4. [Fuzzy Mapping](#fuzzy-mapping)
5. [Tellingen](#tellingen)

---

## Salesforce

### Accounts (9)

| Naam | Stad | Industrie | SF ID | Bron |
|---|---|---|---|---|
| **supplier1** | Brussels | Manufacturing | `001KI00000N7MjVYAV` | setup |
| **Colruyt Group** | Halle | Retail | `001KI00000N7zHSYAZ` | setup |
| **GreenTech Solutions** | Ghent | Technology | `001KI00000N7zqXYAR` | setup |
| **Ferrero Benelux** | Brussels | Food & Beverage | `001KI00000N7zhFYAR` | setup |
| **EASI** | Brussels | Technology | `001J6000002LijjIAC` | setup |
| **Brussels Retail Partners** | Brussels | Retail | `001KI00000N7zSNYAZ` | setup |
| **Carrefour Belgium SA** ⚠️ | Evere | Retail | `001KI00000N80nMYAR` | fuzzy |
| **Delhaize Group** ⚠️ | Brussels | Retail | `001KI00000N7zVuYAJ` | fuzzy |
| **Anheuser-Busch InBev** ⚠️ | Leuven | Food & Beverage | `001KI00000N80nRYAR` | fuzzy |

> ⚠️ Fuzzy accounts hebben een formele/juridische naam die bewust **niet overeenkomt** met hun SS-locatienaam of email-domein.

---

### Contacts (3)

| Naam | Email | Titel | Account | SF ID | Bron |
|---|---|---|---|---|---|
| **Marc Supplier** | marc.supplier@supplier1.be | Account Manager | supplier1 | `003KI000009uzQsYAI` | setup |
| **Dorian Feaux** | d.feaux@easi.net | Sales Engineer | EASI | `003KI000009uzRRYAY` | setup |
| **Arne Albrecht** | a.albrecht@easi.net | Business Analyst | EASI | `003KI000009uzRbYAI` | setup |

---

### Opportunities (7)

| Naam | Stage | Bedrag | Sluitdatum | Account | SF ID | Bron |
|---|---|---|---|---|---|---|
| supplier1 — Q2 Delivery Contract | Negotiation/Review | €85.000 | 30 jun 2026 | supplier1 | `006KI000005bHekYAE` | setup |
| Colruyt Group — SmartSales Rollout 2026 | Proposal/Price Quote | €220.000 | 30 sep 2026 | Colruyt Group | `006KI000005bHl1YAE` | setup |
| GreenTech Solutions — Sustainability Dashboard | Qualification | €45.000 | 15 aug 2026 | GreenTech Solutions | `006KI000005bHl6YAE` | setup |
| Ferrero — Nutella In-Store Display Campaign | Prospecting | €30.000 | 1 okt 2026 | Ferrero Benelux | `006KI000005bHlBYAU` | setup |
| Carrefour Belgium SA — In-Store Analytics Pilot ⚠️ | Proposal/Price Quote | €175.000 | 31 jul 2026 | Carrefour Belgium SA | `006KI000005bIGDYA2` | fuzzy |
| Delhaize Group — Supply Chain Optimisation ⚠️ | Negotiation/Review | €310.000 | 31 aug 2026 | Delhaize Group | `006KI000005bIGIYA2` | fuzzy |
| Anheuser-Busch InBev — Distribution Network Mapping ⚠️ | Qualification | €520.000 | 15 sep 2026 | Anheuser-Busch InBev | `006KI000005bIGNYA2` | fuzzy |

**Totale pipeline: €1.385.000**

---

### Cases (4)

| Subject | Status | Prioriteit | Account | SF ID | Bron |
|---|---|---|---|---|---|
| Delayed shipment — supplier1 April batch | Working | High | supplier1 | `500KI000001mJjsYAE` | setup |
| Colruyt — Integration issue with POS system | New | Medium | Colruyt Group | `500KI000001mJiCYAU` | setup |
| Carrefour Belgium SA — POS integration delay ⚠️ | New | High | Carrefour Belgium SA | `500KI000001mK0yYAE` | fuzzy |
| Delhaize Group — EDI connection issue ⚠️ | Working | Medium | Delhaize Group | `500KI000001mK13YAE` | fuzzy |

---

## SmartSales

### Locaties (10)

| Naam | Code | Stad | Straat | UID | Bron |
|---|---|---|---|---|---|
| **supplier1** | SUP-001 | Brussels | Rue du Commerce 1 | `cac5b20d-285c-11f1-a2fe-005056010707` | setup |
| **Colruyt - Halle** | COLRUYT-HAL-001 | Halle | Edingensesteenweg 196 | `329a7e6c-42da-11f1-a803-005056010707` | setup |
| **GreenTech Solutions - Ghent** | GTS-GNT-001 | Ghent | Technologiepark 122 | `3d28b72d-42da-11f1-a803-005056010707` | setup |
| **Ferrero Benelux - Brussels (Nutella)** | FERR-BRU-001 | Brussels | Bld de la Woluwe 42 | `741d5f40-42da-11f1-a803-005056010707` | setup |
| **EASI - Brussels** | EASI-BRU-001 | Brussels | Avenue Louise 65 | `51f9e686-42da-11f1-a803-005056010707` | setup |
| **CRF - Anderlecht** ⚠️ | CRF-AND-001 | Brussels | Bergensesteenweg 1424 | `2d79461f-4310-11f1-a803-005056010707` | fuzzy |
| **AD Delhaize - Forest** ⚠️ | ADL-FOR-001 | Brussels | Chaussée de Neerstalle 800 | `2e532129-4310-11f1-a803-005056010707` | fuzzy |
| **AB InBev - Leuven** ⚠️ | ABI-LEU-001 | Leuven | Vaartstraat 94 | `2f355296-4310-11f1-a803-005056010707` | fuzzy |
| **Lidl Belgium - Antwerp** ⚠️ | LDL-ANT-001 | Antwerp | Noordersingel 10 | `301c94e5-4310-11f1-a803-005056010707` | fuzzy |
| **Customer1** | CUS-001 | Bruges | Markt 5 | `fa4acd29-285c-11f1-a2fe-005056010707` | pre-existing |

> ⚠️ Fuzzy locaties: naam komt bewust niet overeen met SF-accountnaam. Lidl is een **gap detection** case: alleen in SS, geen SF account en geen emails.
> Customer1 is een pre-existing locatie die als **customer** dient in alle 8 orders.

---

### Catalog Items (8)

| Code | Titel | Prijs | Eenheid | Groep | UID | Bron |
|---|---|---|---|---|---|---|
| PROD-SUP1-001 | supplier1 — Industrial Components Pack | €149,99 | piece | IT Hardware | `6ed4f5e9-42e3-11f1-a803-005056010707` | setup |
| PROD-COL-001 | Colruyt House Brand — Retail Display Kit | €89,50 | piece | IT Hardware | `6fd1e538-42e3-11f1-a803-005056010707` | setup |
| PROD-NUT-001 | Nutella 750g — Display Jar | €4,99 | jar (per 12) | Spreads | `70b59307-42e3-11f1-a803-005056010707` | setup |
| PROD-GTS-001 | GreenTech Solutions — Dashboard License | €2.500,00 | license | IT Software | `718ccfb1-42e3-11f1-a803-005056010707` | setup |
| PROD-CRF-001 ⚠️ | Carrefour — In-Store Analytics Module | €4.500,00 | license | IT Hardware | `31d61ac2-4310-11f1-a803-005056010707` | fuzzy |
| PROD-ADL-001 ⚠️ | Delhaize — EDI Connector Pack | €1.200,00 | piece | IT Hardware | `32a9422b-4310-11f1-a803-005056010707` | fuzzy |
| PROD-ABI-001 ⚠️ | AB InBev — Distribution Mapping License | €8.750,00 | license | IT Hardware | `33676a4f-4310-11f1-a803-005056010707` | fuzzy |
| PROD-LDL-001 ⚠️ | Lidl — Shelf Replenishment Kit | €299,00 | piece (per 5) | IT Hardware | `34579c1a-4310-11f1-a803-005056010707` | fuzzy |

---

### Orders (8)

| Referentie | Supplier | Qty × Product | Totaal | UID | Bron |
|---|---|---|---|---|---|
| **ORD-SUP1-2026-001** | supplier1 | 10× PROD-SUP1-001 | €1.499,90 | `76012bb6-42e3-11f1-a803-005056010707` | setup |
| **ORD-COL-2026-001** | Colruyt - Halle | 5× PROD-COL-001 | €447,50 | `76e7ca8d-42e3-11f1-a803-005056010707` | setup |
| **ORD-NUT-2026-001** | Ferrero Benelux - Brussels (Nutella) | 48× PROD-NUT-001 | €239,52 | `77a50163-42e3-11f1-a803-005056010707` | setup |
| **ORD-GTS-2026-001** | GreenTech Solutions - Ghent | 1× PROD-GTS-001 | €2.500,00 | `78655f28-42e3-11f1-a803-005056010707` | setup |
| **ORD-CRF-2026-001** ⚠️ | CRF - Anderlecht | 12× PROD-CRF-001 | €54.000,00 | `36cc5831-4310-11f1-a803-005056010707` | fuzzy |
| **ORD-ADL-2026-001** ⚠️ | AD Delhaize - Forest | 8× PROD-ADL-001 | €9.600,00 | `37bc49f5-4310-11f1-a803-005056010707` | fuzzy |
| **ORD-ABI-2026-001** ⚠️ | AB InBev - Leuven | 1× PROD-ABI-001 | €8.750,00 | `38ad6cf1-4310-11f1-a803-005056010707` | fuzzy |
| **ORD-LDL-2026-001** ⚠️ | Lidl Belgium - Antwerp | 20× PROD-LDL-001 | €5.980,00 | `39821838-4310-11f1-a803-005056010707` | fuzzy |

**Totale orderwaarde SS: €83.016,92** — Customer voor alle orders: `Customer1`

---

## Microsoft 365

**Mailbox:** `smartadmin@easigroupdemo.onmicrosoft.com`  
**Auth:** client_credentials (app-only) via `test_email_injector_*` env vars — gebruikt door zowel `test_mails.py` als `testdata_fuzzy.ipynb`

---

### Emails (13)

#### Setup-emails (7) — via `test_mails.py`

| Subject | Afzender | Email | Entiteit |
|---|---|---|---|
| Follow-up: supplier1 Q2 2026 Delivery Contract | Marc Supplier | marc.supplier@supplier1.be | supplier1 |
| supplier1 — Updated pricing for H2 2026 | Marc Supplier | marc.supplier@supplier1.be | supplier1 |
| Colruyt Group — SmartSales pilot bevestiging | Colruyt Group Procurement | procurement@colruyt.be | Colruyt |
| GreenTech Solutions — Interest in sustainability dashboard | GreenTech Solutions | info@greentechsolutions.be | GreenTech |
| Ferrero Benelux — Nutella spring campaign inquiry | Ferrero Benelux Marketing | marketing@ferrero.be | Nutella |
| Intro: Dorian Feaux — EASI collaboration proposal | Dorian Feaux | d.feaux@easi.net | Dorian |
| Belgium region — Q1 2026 commercial summary | SmartAdmin | smartadmin@easigroupdemo.onmicrosoft.com | België / Brussel |

> `test_mails.py` injecteert emails rechtstreeks in de inbox via de Graph API (geen echte SMTP), met idempotency check op subject. De calendar events en OneDrive upload staan ook in dit script maar waren uitgecommentarieerd (`inject_emails` en `inject_onedrive` waren actief, `inject_events` ook).

#### Fuzzy emails (6) — via `testdata_fuzzy.ipynb`

| Subject | Afzender | Email | Entiteit | Fuzzy aspect |
|---|---|---|---|---|
| Q2 pilot update — analytics rollout | Carrefour BE Operations | ops@carrefour-be.eu | Carrefour | domein ≠ SF naam |
| Offerte aanvraag — POS koppeling modules | CRF Belgium Procurement | procurement@carrefour-be.eu | Carrefour | domein ≠ SF naam |
| EDI connector — technische vraag | AD Delhaize IT | it@delhaize.eu | Delhaize | `.eu` + franchise prefix |
| Supply chain project — follow-up meeting | Delhaize Procurement | procurement@delhaize.eu | Delhaize | domein ≠ SF naam |
| Distribution mapping — scope confirmation | AB InBev Sales | sales@ab-inbev.com | AB InBev | afkorting vs juridisch |
| Proximus — partnership inquiry | Proximus Business | info@proximus.be | Proximus | **alleen email — gap detection** |

---

### Calendar Events (5) — via `test_mails.py`

| Subject | Start | Einde | Entiteit |
|---|---|---|---|
| supplier1 — Q2 Delivery Review | 10 mei 2026, 10:00 | 11:00 | supplier1 |
| Colruyt Group — SmartSales Rollout Kickoff | 15 mei 2026, 14:00 | 15:30 | Colruyt |
| GreenTech Solutions — Technical Qualification Call | 12 mei 2026, 11:00 | 12:00 | GreenTech |
| Weekly sync — Dorian Feaux | 6 mei 2026, 09:00 | 09:30 | Dorian |
| Sprint review — Arne Albrecht | 8 mei 2026, 14:00 | 15:00 | Arne |

---

### OneDrive (1) — via `test_mails.py`

| Bestandsnaam | Pad | Entiteit | Sleutelwoorden |
|---|---|---|---|
| `supplier1_delivery_report_Q2_2026.txt` | root | supplier1 | supplier1, SUP-001, Q2 2026, ORD-SUP1-2026-001, delayed, marc.supplier@supplier1.be |
| `contact_draftQ1.docx` | root | supplier1 | supplier1, SUP-001, Q1 2026, contact draft, Marc Supplier |
| `paste/origin.docx` | root/paste | Nutella / Ferrero | Nutella, Ferrero, origin, history |
| `paste/nutella verkoopcijfers.docx` | root/paste | Nutella / Ferrero | Nutella, Ferrero Benelux, verkoopcijfers, sales figures |
| `paste/nutella recept.docx` | root/paste | Nutella / Ferrero | Nutella, recept, recipe, Ferrero |
| `ABinbev deal draft.docx` | root | AB InBev / Anheuser-Busch InBev | AB InBev, Anheuser-Busch InBev, deal draft, Distribution Network Mapping, €520.000, Leuven, 006KI000005bIGNYA2 |

---

## Fuzzy Mapping

Bewuste naaminconsitenties tussen systemen, bedoeld om **entity resolution** te testen.

| Echte entiteit | SF naam | SF ID | SS locatie | SS UID | Email domein | Gap | Uitdaging |
|---|---|---|---|---|---|---|---|
| Carrefour | `Carrefour Belgium SA` | `001KI00000N80nMYAR` | `CRF - Anderlecht` | `2d79461f-...` | carrefour-be.eu | — | Afkorting + andere TLD |
| Delhaize | `Delhaize Group` | `001KI00000N7zVuYAJ` | `AD Delhaize - Forest` | `2e532129-...` | delhaize.eu | — | Franchise prefix, .eu |
| AB InBev | `Anheuser-Busch InBev` | `001KI00000N80nRYAR` | `AB InBev - Leuven` | `2f355296-...` | ab-inbev.com | — | Juridisch vs afkorting |
| Proximus | *(geen SF)* | — | *(geen SS)* | — | proximus.be | Alleen in email | Gap detection |
| Lidl | *(geen SF)* | — | `Lidl Belgium - Antwerp` | `301c94e5-...` | *(geen email)* | Alleen in SS | Gap detection |

### Wat dit aantoont

| Prompt | Zonder entity resolution | Met entity resolution |
|---|---|---|
| *"Which email senders have an active deal?"* | `carrefour-be.eu` ≠ `Carrefour Belgium SA` → mist match | Link gelegd → correct |
| *"Which companies emailed me but have no SS location?"* | `ops@carrefour-be.eu` ≠ `CRF - Anderlecht` → fout resultaat | Mapping bekend → correct |
| *"Which companies have an open order but no SF account?"* | Lidl gevonden maar SF-gap onbekend → onvolledig | Gap correct gedetecteerd |
| *"Who is the contact behind my most expensive order?"* | `AB InBev - Leuven` (SS) ≠ `Anheuser-Busch InBev` (SF) → geen contact | Alias bekend → contact gevonden |

---

## Tellingen

| Systeem | Type | Aantal |
|---|---|---|
| Salesforce | Accounts | 9 |
| Salesforce | Contacts | 3 |
| Salesforce | Opportunities | 7 |
| Salesforce | Cases | 4 |
| SmartSales | Locaties | 10 |
| SmartSales | Catalog items | 8 |
| SmartSales | Orders | 8 |
| M365 | Emails | 13 |
| M365 | Calendar events | 5 |
| M365 | OneDrive bestanden | 6 |
| **Totaal** | | **73** |