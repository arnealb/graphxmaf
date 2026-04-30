# Document Generation Brief — EASI Group Test Data

## Context

For a prototype multi-agent system I need a set of **fictional but realistic company documents** from the fictional company **EASI Group**. The documents serve as test data for a RAG (Retrieval-Augmented Generation) system that indexes them semantically. The system already has 6 documents; this brief defines 20 additional ones.

**Requirements:**
- Language: **English**
- Format: **Microsoft Word (.docx)**
- Length: **800–1,500 words per document** — long, detailed, with real substance
- Style: professional, concrete — specific numbers, names, thresholds, timelines. No filler text. Every paragraph must contain information a user might actually query.
- The documents must embed the **same entities, people, places, and product names** that already appear in the test setup, so that the RAG system can link information across documents.

---

## Entity Reference — use these exactly throughout all documents

### Company
- **EASI Group** — Avenue Louise 65, 1050 Brussels, Belgium
- Internal domains: `@easi.net`
- Key contacts at EASI:
  - **Arne Albrecht** — Business Analyst — `a.albrecht@easi.net`
  - **Nathalie Pieters** — Customer Success Manager — `n.pieters@easi.net`
  - **HR department** — `hr@easi.net`
  - **IT / Service desk** — `servicedesk.easi.net` (portal) or `it@easi.net`
  - **Finance** — `finance@easi.net`
  - **Procurement** — `procurement@easi.net`
  - **Privacy / DPO** — `privacy@easi.net` / `dpo@easi.net`
  - **Security** — `security@easi.net`

### Clients / Partners (reference these by their exact names)
| Entity | Salesforce name | Address | Key contact |
|--------|----------------|---------|-------------|
| **supplier1** | supplier1 | Rue du Commerce 1, 1000 Brussels | Marc Supplier — `marc.supplier@supplier1.be` — Account Manager |
| **Colruyt Group** | Colruyt Group | Edingensesteenweg 196, 1500 Halle | `procurement@colruyt.be` |
| **GreenTech Solutions** | GreenTech Solutions | Technologiepark 122, 9052 Ghent | `info@greentechsolutions.be` |
| **Ferrero Benelux** | Ferrero Benelux | Bld de la Woluwe 42, 1200 Brussels | `marketing@ferrero.be` |
| **Carrefour Belgium SA** | Carrefour Belgium SA | Bergensesteenweg 1424, 1070 Brussels (Anderlecht) | `ops@carrefour-be.eu` |
| **Delhaize Group** | Delhaize Group | Chaussée de Neerstalle 800, 1190 Brussels (Forest) | `procurement@delhaize.eu` |
| **Anheuser-Busch InBev** | Anheuser-Busch InBev | Vaartstraat 94, 3000 Leuven | `sales@ab-inbev.com` |
| **Fujitsu Belgium NV** | — | Fujitsu Belgium, Brussels | `account.manager@fujitsu.be` |

### Active Opportunities (mention these where relevant)
- **supplier1 — Q2 Delivery Contract** — €85,000 — stage: Negotiation/Review — close: 30 Jun 2026
- **Colruyt Group — SmartSales Rollout 2026** — €220,000 — stage: Proposal/Price Quote — close: 30 Sep 2026
- **GreenTech Solutions — Sustainability Dashboard** — €45,000 — stage: Qualification — close: 15 Aug 2026
- **Ferrero — Nutella In-Store Display Campaign** — €30,000 — stage: Prospecting — close: 1 Oct 2026
- **Carrefour Belgium SA — In-Store Analytics Pilot** — €175,000 — 12 hypermarket locations — close: 31 Jul 2026
- **Delhaize Group — Supply Chain Optimisation** — €310,000 — stage: Negotiation/Review — close: 31 Aug 2026
- **Anheuser-Busch InBev — Distribution Network Mapping** — €520,000 — stage: Qualification — close: 15 Sep 2026

### Active Cases
- **Case 00001021** — Colruyt — Integration issue with POS system — Status: New — Priority: Medium
- **Case 00001022** — supplier1 — Delayed shipment April batch — Status: Working — Priority: High
- **Case 00001023** — Carrefour Belgium SA — POS integration delay — Status: New — Priority: High
- **Case 00001024** — Delhaize Group — EDI connection issue — Status: Working — Priority: Medium

### Products / Services EASI delivers
- **SmartSales** — EASI's field sales platform (locations, catalog, orders) — deployed at Colruyt, Carrefour, Delhaize, AB InBev, Ferrero, GreenTech
- **In-Store Analytics Module** — €4,500/license — deployed at Carrefour (12 locations)
- **EDI Connector Pack** — €1,200/piece — deployed at Delhaize AD-franchise stores
- **Distribution Mapping License** — €8,750/year — deployed at AB InBev Leuven
- **Sustainability Dashboard License** — €2,500/year — GreenTech Solutions

---

## Documents to Generate

### Folder: HR/

---

**1. leave_policy_easi.docx**

**Purpose:** Comprehensive leave policy covering all leave types at EASI Group.

**Must include:**
- 20 statutory vacation days per year + 12 ADV (reduction of working hours) days, for a total of 32 paid leave days
- Leave request procedure: submit via the HR portal at `hr.easi.net` at least 3 working days in advance for up to 3 consecutive days, at least 2 weeks in advance for periods longer than 3 days
- Leave carryover: maximum 5 days may be carried to the following calendar year; unused days expire on 31 March
- Sick leave: self-certification accepted for the first 2 days; a medical certificate from a licensed physician must be submitted to hr@easi.net on day 3 and beyond; prolonged sick leave (>30 consecutive calendar days) triggers a mandatory meeting with HR and the occupational physician
- Parental leave: 4 months unpaid leave available after 12 months of service; request must be submitted at least 3 months in advance via hr@easi.net; position is guaranteed upon return
- Breastfeeding breaks: 2 × 30-minute breaks per day, until the child reaches 9 months; schedule agreed with direct manager
- Bereavement leave: spouse or cohabiting partner: 3 days; first-degree relatives (parents, children, siblings): 3 days; second-degree relatives: 1 day
- Volunteer leave: 1 day per year for recognised volunteer work, subject to management approval
- Dorian Feaux (Sales Engineer) and Arne Albrecht (Business Analyst) are referenced as examples when illustrating partial-year calculations (both joined EASI mid-year)
- All leave balances are visible in the HR portal; questions to hr@easi.net

---

**2. remote_work_policy_easi.docx**

**Purpose:** Governs telework/remote work arrangements for all EASI employees.

**Must include:**
- Maximum 3 days remote work per week; EASI office at Avenue Louise 65 is the default workplace
- Mandatory office presence on Mondays and Thursdays (team alignment days); exceptions require manager approval at least 48 hours in advance
- Remote work is not permitted during the first 6 months of employment (probation period); this applies to all new joiners including those in client-facing roles such as Sales Engineers (e.g. Dorian Feaux's role)
- Internet allowance: €20/month, paid monthly via payroll, taxed as a benefit in kind above the legal ceiling; employees must have a minimum download speed of 25 Mbps
- Ergonomic equipment request (second screen, keyboard, sit-stand desk): submit an IT ticket via `servicedesk.easi.net`, category "Hardware Request — Remote Work", budget up to €400 per employee per 3-year cycle
- VPN is mandatory for all remote work; no client data (including data from Colruyt Group, Carrefour Belgium SA, Delhaize Group, Anheuser-Busch InBev, or any other client) may be stored on personal devices or accessed without VPN
- Client-site work: days spent at a client location (e.g. at Colruyt's Halle office or at Carrefour's Anderlecht store) do not count as remote work days
- Violations are handled under the disciplinary procedure; repeated violations may result in suspension of remote work privileges
- Policy review: annually in October, coordinated by HR (hr@easi.net) and the Works Council

---

**3. company_car_policy_easi.docx**

**Purpose:** Rules for company car allocation, use, fuel cards, damage, and return.

**Must include:**
- Three car categories: Category A (consultants and analysts with < 3 years seniority, e.g. Arne Albrecht — Business Analyst): compact electric or hybrid; Category B (seniors, Sales Engineers, team leads, e.g. Dorian Feaux — Sales Engineer): mid-range; Category C (managers, directors): premium
- Fuel card: covers professional kilometres only; private use requires a monthly personal contribution of €150 (deducted from net salary); employees must submit a monthly mileage log distinguishing professional from private kilometres by the 5th of each month to hr@easi.net
- Professional kilometres include travel to client locations: Colruyt Group (Halle), Carrefour Belgium SA (Anderlecht), Delhaize Group (Forest), AB InBev (Leuven), GreenTech Solutions (Ghent), Ferrero Benelux (Brussels), supplier1 (Rue du Commerce 1, Brussels)
- Vehicle replacement cycle: 4 years or 120,000 km, whichever comes first
- Damage reporting: any damage, even minor, must be reported within 24 hours via hr@easi.net; include a description, photos, and the reference number of the police or insurer report if applicable; failure to report within 24h may result in the employee bearing part of the repair cost
- Home charging station: employees with Category A or B electric vehicles may request a home charging station via an IT ticket (servicedesk.easi.net, category "EV Charging"); EASI covers installation up to €800; electricity cost reimbursement is €0.10/kWh for home charging based on monthly meter read
- Return of vehicle upon departure: vehicle must be returned clean, with all keys and documents, on the last working day; final mileage log must be submitted; any damage not previously reported will be charged to the employee
- Car list and available models are published on the intranet and updated quarterly by procurement@easi.net

---

**4. training_policy_easi.docx**

**Purpose:** EASI's training and certification policy, budget rules, and approved platforms.

**Must include:**
- Annual training budget: €1,500 per employee per calendar year; unused budget does not roll over
- Approval: training requests under €500 require only manager approval via the HR portal; requests between €500 and €1,500 require manager + HR approval; requests above €1,500 (e.g. multi-day external programmes or expensive certifications) require additionally the sign-off of the department director
- Approved self-paced platforms: Pluralsight, Udemy Business, LinkedIn Learning — licenses managed centrally by IT, request via `servicedesk.easi.net`
- Approved certifications: Salesforce certifications (Salesforce Administrator, Sales Cloud Consultant, Platform Developer) are fully reimbursed and encouraged especially for roles with client exposure to Colruyt Group, Carrefour Belgium SA, and Delhaize Group where EASI manages Salesforce environments; Microsoft Azure certifications; TOGAF; Prince2
- Repayment obligation: if an employee leaves EASI within 12 months of completing a company-funded training costing more than €500, they must reimburse 100% (departure within 6 months) or 50% (departure between 6 and 12 months); this applies to Arne Albrecht's recent Salesforce Administrator certification (completed March 2026, cost €1,200)
- Study leave: 1 day of paid leave per exam, maximum 6 days per calendar year; must be pre-approved via the HR portal at least 2 weeks in advance
- Conference attendance: attendance at external conferences (e.g. Dreamforce, Microsoft Ignite) requires manager and director approval; conference fees are charged separately from the training budget
- Training needs are discussed during the annual performance review cycle (September–November) and the mid-year check-in (April)
- All training completions and certifications must be logged in the HR portal within 5 working days of completion; contact hr@easi.net for questions

---

**5. performance_review_procedure_easi.docx**

**Purpose:** Full description of the annual and mid-year performance review process.

**Must include:**
- Annual review cycle: formal reviews are conducted in the period September–November each year; the exact timeline is announced by HR (hr@easi.net) in August
- Mid-year check-in: a lighter structured conversation in April between the employee and their direct manager; not rated but documented in the HR portal
- Self-evaluation: employees complete a structured self-evaluation form in the HR portal at least 2 weeks before the formal review meeting; the form covers objectives achieved, competency self-rating, training completed, and goals for the coming year
- Rating scale: 4 levels — "Insufficient" / "Meets Expectations" / "Exceeds Expectations" / "Exceptional"
- Link to compensation: "Insufficient" → 0% salary increase; "Meets Expectations" → 2–4% increase (based on market data); "Exceeds Expectations" → 4–7% increase; "Exceptional" → 7–10% increase + eligibility for spot bonus
- Roles and examples: Arne Albrecht (Business Analyst) and Dorian Feaux (Sales Engineer) are referenced as examples of employees whose objectives include quantitative delivery targets (project delivery) and qualitative targets (client satisfaction scores from accounts such as Colruyt Group and GreenTech Solutions)
- Client satisfaction ratings from accounts managed through Salesforce are used as an objective input for Sales Engineers and Business Analysts; Nathalie Pieters (Customer Success Manager) coordinates the collection of these ratings from Colruyt Group, Carrefour Belgium SA, and Delhaize Group each year in Q3
- Appeals procedure: an employee may challenge their rating in writing to the HR Director (hr@easi.net) within 10 working days of receiving the formal review; the HR Director will convene a review panel within 15 working days
- Managers must complete their part of the review form within 5 working days of receiving the employee's self-evaluation; late submissions are escalated to the department director

---

**6. health_insurance_guide_easi.docx**

**Purpose:** Guide to the group health insurance and hospitalisation plan at EASI Group.

**Must include:**
- Insurer: DKV Belgium (group policy number: DKV-EASI-2024-0091)
- Automatic enrollment: all employees are enrolled in the hospitalisation plan after completing 3 months of service; the HR department sends enrollment confirmation to the employee's EASI email address
- Hospitalisation coverage: room of choice (private or two-bed), 100% of specialist fees above RIZIV/INAMI tariff, 100% of surgical costs, coverage in Belgian hospitals and EU hospitals for stays related to professional travel; stays related to visits to client locations (Colruyt Group, Carrefour Belgium SA, AB InBev Leuven, etc.) are covered
- Outpatient care (ambulatory coverage — optional module): reimbursement of 75% of costs for GP visits, specialist consultations, physiotherapy, and prescription medication not reimbursed by mutuality, up to an annual ceiling of €750; employees may opt in during the annual benefits window (January) or within 30 days of joining
- Dental: 75% reimbursement of dental costs not covered by mutuality, maximum €500 per year; orthodontics excluded unless medically prescribed
- Enrolling family members: spouse or legal cohabitant and children under 25 may be added; the additional monthly premium is borne entirely by the employee and deducted from net salary; add via the HR portal or email hr@easi.net
- Direct billing (third-party payment): at affiliated hospitals, DKV will invoice the hospital directly; the employee does not need to advance costs; for non-affiliated hospitals, the employee pays and claims reimbursement via the MyDKV app or by submitting scanned invoices to `dkv@easi.net`
- DKV customer service: 02 550 05 00 (weekdays 08:00–18:00) or via MyDKV app
- HR contact for insurance questions: hr@easi.net; for urgent situations (e.g. emergency hospitalisation while on a client visit), call 02 123 45 68

---

**7. offboarding_guide_easi.docx**

**Purpose:** Complete employee offboarding checklist and procedure.

**Must include:**
- Notice periods: governed by Belgian labour law (Wet Eenheidsstatuut 2014); table showing notice in weeks per year of seniority for both employer-initiated and employee-initiated termination (e.g. 1 year seniority: 4 weeks by employee; 2 years: 6 weeks; 5 years: 13 weeks)
- Exit interview: mandatory meeting with HR within the first 2 weeks of the notice period; scheduled by hr@easi.net; covers reasons for departure, feedback on management and working conditions, and transfer of knowledge
- Knowledge transfer: the departing employee must prepare a handover document covering active projects, client relationships, and open items; for client-facing roles (e.g. Sales Engineers or Business Analysts managing accounts such as Colruyt Group SmartSales Rollout or GreenTech Solutions Sustainability Dashboard), the handover must include a client briefing shared with Nathalie Pieters (n.pieters@easi.net) and the relevant account manager (Dorian Feaux for new accounts, Arne Albrecht for technical handovers)
- Equipment return: laptop, badge, mobile phone (if applicable), and company car must be returned to the EASI reception at Avenue Louise 65 on or before the last working day; car return requires completing the final mileage log (see Company Car Policy)
- IT access revocation: IT (it@easi.net) will disable all accounts (Microsoft 365, Salesforce, SmartSales, VPN) within 24 hours of the last working day; access to client environments (e.g. Colruyt's Salesforce org, Carrefour's analytics module) is also revoked and communicated to the relevant client contact by Nathalie Pieters
- Final pay calculation: includes outstanding salary, holiday pay (pro-rated remaining vacation days), meal vouchers, and any accrued bonuses; payslip issued within 5 working days of departure
- Non-compete clause: applies to employees in Sales Engineer, Business Analyst, and Customer Success roles; duration: 12 months; geographic scope: Belgium; sectoral scope: field sales software, CRM implementation, retail analytics; compensation for the non-compete restriction: 50% of last gross monthly salary for the duration of the clause; EASI may waive the clause within 15 days of resignation
- Reference letter: request via hr@easi.net; standard turnaround 5 working days

---

### Folder: contracts/

---

**8. sla_agreement_easi_colruyt.docx**

**Purpose:** Formal Service Level Agreement between EASI Group (provider) and Colruyt Group (client) for managed services related to the SmartSales platform deployment.

**Must include:**
- Contract reference: EASI-COL-SLA-2026-001
- Scope: EASI provides managed operation, monitoring, and support of the SmartSales platform deployed at Colruyt Group locations, including the Halle head office (Edingensesteenweg 196) and all Colruyt retail outlets connected to the platform as part of the Colruyt Group — SmartSales Rollout 2026 opportunity (€220,000); as of signature date, 47 locations are in scope
- Account team: EASI account manager is Arne Albrecht (a.albrecht@easi.net); Colruyt procurement contact is `procurement@colruyt.be`; technical escalation is Dorian Feaux (d.feaux@easi.net)
- Priority definitions and response/resolution times:
  - P1 (critical — full platform outage, affecting all 47 locations or cash register operations): response within 1 hour, resolution target 4 hours, 24/7 coverage
  - P2 (high — partial outage, >10 locations affected or core catalogue unavailable): response within 4 hours, resolution within 1 business day, business hours (08:00–18:00 Mon–Fri)
  - P3 (medium — degraded performance, individual location issues): response within 1 business day, resolution within 5 business days
  - P4 (low — cosmetic issues, feature requests): best effort, no SLA commitment
- Open case reference: Case 00001021 (Colruyt — Integration issue with POS system, Priority Medium, Status: New) is the baseline case at time of signature and is managed under P3 until the integration root cause is resolved
- Availability SLA: 99.5% monthly uptime for the SmartSales platform, excluding scheduled maintenance windows (Saturdays 22:00–02:00); measured via automated monitoring; downtime is calculated from the moment EASI acknowledges the incident
- Reporting: EASI delivers a monthly service report to `procurement@colruyt.be` covering: uptime, incident count per priority, resolution times, open cases, and planned changes; report delivered by the 5th of the following month
- Penalties: for each P1 SLA breach (response or resolution missed), EASI issues a service credit of 10% of the monthly fee for that month; maximum total service credit per month is 30% of the monthly fee
- Scheduled maintenance: EASI provides 48 hours advance notice for planned maintenance; emergency maintenance requires notification within 2 hours; contact point is a.albrecht@easi.net and Colruyt's procurement
- Escalation path: P1 incidents → immediate notification to Arne Albrecht + Dorian Feaux + EASI Delivery Manager; if not resolved within 2 hours → escalation to EASI COO
- Contract term: 2 years from signing, automatically renewed for 1-year periods unless terminated with 3 months notice

---

**9. data_processing_agreement_colruyt.docx**

**Purpose:** GDPR Article 28 Data Processing Agreement (DPA) between EASI Group (processor) and Colruyt Group (controller) covering processing of personal data through the SmartSales platform and related integrations.

**Must include:**
- DPA reference: EASI-COL-DPA-2026-001; linked to the SLA (EASI-COL-SLA-2026-001) and the SmartSales Rollout opportunity
- Categories of personal data processed: (a) Colruyt retail employees — name, employee ID, store location, role, login credentials for SmartSales; (b) Colruyt customers — purchase history pseudonymised via tokenised customer ID, no direct identification possible; (c) supplier contact data — names and email addresses of supplier contacts including those registered in the SmartSales catalogue (e.g. Marc Supplier — marc.supplier@supplier1.be — Account Manager at supplier1)
- Purpose of processing: operation of the SmartSales field sales platform at Colruyt locations; integration with Colruyt's POS system (see Case 00001021); generation of sales and location analytics
- Sub-processors: (a) Microsoft Azure (Ireland data centre) — hosting of SmartSales backend; (b) Fujitsu Belgium NV — on-site hardware maintenance at Colruyt locations; approved sub-processor list must be kept updated; Colruyt must be notified 30 days before adding a new sub-processor
- Security measures: ISO 27001 certification held by EASI (certificate number: ISO27-EASI-2025-BE); all data encrypted in transit (TLS 1.3) and at rest (AES-256); access to personal data restricted to EASI staff with documented need-to-know (currently: Arne Albrecht, Dorian Feaux, the platform operations team)
- Data retention: personal data is deleted within 30 days of contract termination or upon written request from Colruyt; Colruyt may request a data export in machine-readable format (CSV/JSON) at any time via a.albrecht@easi.net
- Audit rights: Colruyt may conduct an on-site or remote audit of EASI's data processing activities once per year with 30 days' written notice; audit costs borne by Colruyt unless EASI is found to be in breach
- Data breach: EASI notifies Colruyt (procurement@colruyt.be and EASI DPO dpo@easi.net) within 24 hours of becoming aware of a personal data breach; subsequent notification to the Belgian Data Protection Authority (GBA/APD) within 72 hours is coordinated between the parties
- Data subject rights: Colruyt is the point of contact for data subject requests from its employees and customers; EASI assists Colruyt within 5 working days upon written request
- Applicable law: Belgian law; disputes submitted to the Brussels Commercial Court
- DPO contacts: EASI DPO — dpo@easi.net; Colruyt DPO — presumed via procurement@colruyt.be

---

**10. framework_agreement_easi_supplier2.docx**

**Purpose:** Master procurement agreement between EASI Group and Fujitsu Belgium NV covering hardware supply and maintenance for EASI's internal infrastructure and client deployments.

**Must include:**
- Contract reference: EASI-FUJ-FWA-2026-001
- Scope: Fujitsu Belgium NV (registered at Fujitsu Belgium, Brussels) supplies IT hardware (servers, networking equipment, workstations) and provides on-site hardware maintenance for (a) EASI's internal infrastructure at Avenue Louise 65 and (b) hardware deployed at EASI client locations where EASI is responsible for hardware under managed services agreements — including Colruyt Group's locations (Halle and all 47 SmartSales-connected retail outlets), Carrefour Belgium SA (Anderlecht hypermarket pilot, 12 locations), and Delhaize Group (Forest franchise stores)
- Pricing: list prices as per Fujitsu's current price book; volume discounts: 5% for orders totalling >€10,000, 10% for orders totalling >€50,000 in a single purchase order; discount applied on invoice; contact for pricing: account.manager@fujitsu.be
- Payment: 30 days net from invoice date; invoices sent to finance@easi.net; EASI procurement contact: procurement@easi.net
- Warranty: all hardware supplied under this agreement carries a 3-year on-site next-business-day warranty; spare parts availability guaranteed for minimum 5 years after model end-of-sale
- Maintenance SLA (hardware): response on-site within 4 business hours for critical failures at client locations; EASI must provide Fujitsu with access to client premises (Colruyt Halle, Carrefour Anderlecht, Delhaize Forest) and notify the relevant client contact (Arne Albrecht for Colruyt, Dorian Feaux for Carrefour and Delhaize) before scheduling on-site visits
- New client deployments: EASI notifies Fujitsu at least 6 weeks before the planned go-live of a new client deployment requiring hardware; current pipeline requiring hardware procurement includes the Anheuser-Busch InBev Distribution Network Mapping project (Vaartstraat 94, Leuven) and the GreenTech Solutions Sustainability Dashboard pilot (Technologiepark 122, Ghent)
- Term: 3 years from signing (1 January 2026), automatically renewed annually unless terminated with 3 months' written notice to procurement@easi.net and account.manager@fujitsu.be
- Disputes: Brussels Commercial Court; Belgian law applies

---

**11. nda_easi_template.docx**

**Purpose:** Standard bilateral non-disclosure agreement template used by EASI when entering discussions with new clients or partners.

**Must include:**
- Parties: EASI Group (Avenue Louise 65, 1050 Brussels) and [Counterparty Name] (address to be completed)
- Definition of confidential information: all non-public information disclosed by either party, whether orally or in writing, including but not limited to: client lists (including EASI's relationships with Colruyt Group, Carrefour Belgium SA, Delhaize Group, Anheuser-Busch InBev, Ferrero Benelux, GreenTech Solutions, and supplier1), pricing structures (including the SmartSales platform pricing, annual license fees, and EASI professional services day rates), technical architecture of EASI's SmartSales and analytics platforms, source code, product roadmaps, sales pipeline data (including opportunities in Salesforce CRM), and any personal data of EASI employees or clients
- Exclusions from confidentiality: information that is or becomes publicly available without breach of this NDA; information independently developed by the receiving party without use of confidential information; information disclosed by a third party with authorisation
- Obligations: each party may use confidential information solely for the purpose of evaluating or executing a potential business relationship; information may only be shared internally with personnel who have a need to know; all disclosures must be documented
- Duration: confidentiality obligations apply for 5 years after the date of last disclosure; the NDA itself may be terminated with 30 days' notice, but obligations on already-disclosed information survive
- Prohibition on reverse engineering: the receiving party may not reverse engineer, disassemble, or decompile any software, hardware, or technical deliverable received under this NDA
- Return or destruction: upon request or upon NDA termination, the receiving party must return or certifiably destroy all confidential information and confirm in writing within 5 business days
- Penalty: each breach of confidentiality obligations entitles the disclosing party to claim a contractual penalty of €25,000 per breach, without prejudice to claiming additional damages
- Governing law: Belgian law; disputes: Brussels Commercial Court
- Signing process at EASI: the counterparty's signed NDA must be returned to procurement@easi.net; the signed original is archived by the EASI legal/procurement team; Arne Albrecht or Dorian Feaux (as the relationship owner) must notify procurement@easi.net before any confidential presentation or product demonstration to a new prospect

---

**12. maintenance_contract_supplier1.docx**

**Purpose:** Maintenance and support contract between EASI Group and supplier1 for industrial components and related support services.

**Must include:**
- Contract reference: EASI-SUP1-MAINT-2026-001
- Parties: EASI Group (Avenue Louise 65, 1050 Brussels) and supplier1 (Rue du Commerce 1, 1000 Brussels; Salesforce ID: 001KI00000N7MjVYAV)
- EASI contact: procurement@easi.net; supplier1 contact: Marc Supplier — marc.supplier@supplier1.be — Account Manager at supplier1
- Scope: supplier1 provides (a) preventive maintenance of the Industrial Components Pack (product code PROD-SUP1-001) units deployed by EASI, scheduled twice per year (Q1 and Q3), and (b) corrective maintenance on demand when defects are identified; this contract is linked to the active Salesforce opportunity "supplier1 — Q2 Delivery Contract" (€85,000, stage: Negotiation/Review, close date: 30 June 2026) and the existing case "Delayed shipment — supplier1 April batch" (Case 00001022, Priority High, Status: Working)
- Preventive maintenance schedule: Q1 maintenance window: second week of February; Q3 window: second week of September; scheduling confirmed via email to procurement@easi.net at least 4 weeks in advance by Marc Supplier
- Corrective maintenance: EASI reports defects via email to marc.supplier@supplier1.be; response time: acknowledgement within 4 business hours; on-site technician within 8 business hours on weekdays; weekend response available for Priority High issues at additional cost (€200 call-out fee)
- Open issue — April batch delay: the delayed shipment from the April batch (Case 00001022) is under investigation; root cause analysis to be provided by supplier1 to procurement@easi.net within 5 working days of this contract being signed; EASI reserves the right to apply a penalty of €500 per additional day of delay beyond the agreed resolution date
- Spare parts: supplier1 guarantees availability of all spare parts for PROD-SUP1-001 for a minimum of 5 years from the date of last delivery; parts not in stock to be ordered and delivered within 10 business days
- Pricing: monthly retainer €850 excl. VAT covering preventive maintenance visits and up to 4 hours of corrective maintenance per month; additional corrective maintenance hours billed at €120/hour excl. VAT; annual price adjustment based on the ABEX construction cost index
- Communication protocol: as documented in the separate framework agreement (EASI-SUP1-FWA-2025-001), all operational communications must go through the dedicated Teams channel "EASI-supplier1 Operaties"; email to marc.supplier@supplier1.be is acceptable only for urgent issues when Teams is unavailable
- Term: 1 year from 1 January 2026, automatically renewed unless terminated with 2 months' notice by either party to procurement@easi.net and marc.supplier@supplier1.be

---

### Folder: procedures/

---

**13. it_security_procedure_easi.docx**

**Purpose:** EASI Group IT Security Policy covering access, devices, data, and incident reporting.

**Must include:**
- Password policy: minimum 14 characters; must include uppercase, lowercase, number, and special character; Multi-Factor Authentication (MFA) mandatory for all EASI systems including Microsoft 365, Salesforce CRM, SmartSales admin console, VPN, and any client system EASI has access to (Colruyt's Salesforce org, Carrefour's analytics platform, Delhaize's EDI environment, AB InBev's distribution mapping system); password rotation every 90 days; password reuse for the last 12 passwords is prohibited
- Device security: company-issued laptops must have full-disk encryption enabled (BitLocker for Windows); screen must auto-lock after 5 minutes of inactivity; personal USB drives are prohibited; only approved EASI-issued encrypted USB drives (available from IT via servicedesk.easi.net) may be used; personal devices may not be used to access client data
- Clean desk policy: no sensitive documents, including client contracts (e.g. with Colruyt Group, Carrefour Belgium SA, supplier1), pricing materials, or employee data, may be left unattended on a desk or visible on screen when the employee is away from their workstation; physical documents must be locked in the provided pedestal drawer
- Data classification: four levels — Public (marketing materials, press releases), Internal (internal policies, project plans, this document), Confidential (client contracts, personal data of employees and clients, Salesforce CRM data, SmartSales order and catalogue data), Strictly Confidential (financial forecasts, board materials, M&A-related information); Confidential and Strictly Confidential data must be encrypted when transmitted externally
- Client data handling: data from any client system that EASI manages — including SmartSales data for Colruyt Group, In-Store Analytics data for Carrefour Belgium SA (12 hypermarkets), EDI connector data for Delhaize Group, and Distribution Mapping data for Anheuser-Busch InBev (Leuven) — is classified as Confidential and may only be accessed by EASI personnel with a documented business need; access is logged and reviewed quarterly by the IT security team (security@easi.net)
- Phishing tests: IT conducts simulated phishing tests quarterly; employees who click a simulated phishing link or enter credentials are automatically enrolled in a mandatory 30-minute online security awareness training; managers are notified; second failure within 12 months triggers an escalation to HR
- Software installation: employees may not install unapproved software on company devices; all software requests go via servicedesk.easi.net; browser extensions are governed by a whitelist managed by IT
- Incident reporting: all suspected security incidents (phishing, malware, unauthorised access, data loss) must be reported immediately via the security portal at `security.easi.net` or by email to security@easi.net; do not attempt to investigate or remediate independently; preserve all evidence (do not turn off the affected device); Arne Albrecht and Dorian Feaux are trained first responders who can assist colleagues in the initial reporting step
- Policy violations are handled under the EASI disciplinary procedure and may constitute grounds for dismissal

---

**14. incident_management_procedure_easi.docx**

**Purpose:** End-to-end incident management process for EASI's managed services, covering detection through post-mortem.

**Must include:**
- Scope: applies to all incidents affecting EASI-managed services at client locations, including the SmartSales platform (Colruyt Group — 47 locations, Carrefour Belgium SA — 12 hypermarkets, Delhaize Group — AD-franchise stores), In-Store Analytics (Carrefour Belgium SA), EDI Connector (Delhaize Group), Distribution Mapping (Anheuser-Busch InBev, Leuven), and any other managed service
- Definition: an incident is any unplanned interruption or quality reduction of a managed service; a service request (e.g. a new user account, a configuration change) is NOT an incident
- Severity levels:
  - S1 (Critical): full service outage affecting all users/locations at one or more clients; examples: SmartSales platform completely down for Colruyt Group, Carrefour analytics inaccessible across all 12 hypermarkets; 24/7 coverage, immediate war-room activation
  - S2 (High): major partial outage, >30% of users/locations affected or a critical business function unavailable; example: Colruyt POS integration down (Case 00001021 would be reclassified S2 if all stores affected), Delhaize EDI not processing orders (Case 00001024); business hours primary, on-call for off-hours
  - S3 (Medium): degraded performance or individual location failures; example: single Carrefour hypermarket losing analytics sync, one Delhaize store's EDI connector dropping messages; business hours only
  - S4 (Low): minor issues, cosmetic bugs, performance slightly below benchmark; business hours, no on-call
- Reporting channels: SmartSales client portal, email to support@easi.net, or phone 02 123 45 67 (S1/S2 only); EASI's internal monitoring may also auto-create incidents
- Escalation matrix: S1 → immediate notification to Arne Albrecht (a.albrecht@easi.net), Dorian Feaux (d.feaux@easi.net), and EASI Delivery Manager; if unresolved within 2 hours → COO notified; S2 → Arne Albrecht notified within 30 minutes; S3/S4 → service desk handles without escalation unless SLA breach risk
- Client communication: for S1 and S2, the EASI account manager (Arne Albrecht for Colruyt, Dorian Feaux for Carrefour and Delhaize) sends a status update to the client contact every 2 hours until resolved; Nathalie Pieters (n.pieters@easi.net) co-ordinates client communication for accounts she manages
- Post-mortem: mandatory for all S1 and S2 incidents; must be completed within 5 working days of resolution; includes timeline, root cause, contributing factors, impact assessment (number of locations affected, estimated business impact in EUR if known), remediation steps, and preventive measures; post-mortem is shared with the client; current open post-mortems: Case 00001023 (Carrefour POS delay, S2) and Case 00001022 (supplier1 shipment delay, classified separately as a supply chain incident)

---

**15. data_breach_procedure_easi.docx**

**Purpose:** EASI's procedure for detecting, assessing, and reporting personal data breaches under GDPR.

**Must include:**
- Scope: applies to all personal data EASI processes as a data processor or controller, including: employee data of EASI staff, personal data of client employees (Colruyt Group retail staff using SmartSales, Carrefour Belgium SA store employees using the analytics module, Delhaize Group franchise employees), pseudonymised customer data, and supplier contact data (e.g. Marc Supplier — marc.supplier@supplier1.be — registered in Salesforce CRM and the SmartSales supplier catalogue)
- Definition of a personal data breach: any accidental or unlawful destruction, loss, alteration, unauthorised disclosure of, or access to personal data; examples: a laptop containing Colruyt employee data is lost (especially relevant for field visits by Arne Albrecht or Dorian Feaux); an EASI system is compromised and client data is exfiltrated; an employee mistakenly sends a Salesforce data export to the wrong email address
- Internal reporting obligation: any EASI employee who suspects or discovers a data breach must report it to the EASI Data Protection Officer within 2 hours, via privacy@easi.net or dpo@easi.net (DPO direct line: 02 123 45 99); do NOT attempt to contain the breach without informing the DPO; preserve all logs and evidence
- Initial assessment (DPO + IT Security, within 4 hours): determine (a) is personal data actually involved? (b) what categories of data and how many data subjects? (c) is there risk to data subjects' rights and freedoms? (d) is cross-border processing involved (relevant for clients with EU-wide operations such as Anheuser-Busch InBev or Ferrero Benelux)?
- Notification to the Belgian DPA (GBA/APD): if the assessment concludes there is a risk to data subjects, EASI must notify the GBA at `www.gegevensbeschermingsautoriteit.be` within 72 hours of first becoming aware; the DPO (dpo@easi.net) coordinates this; the notification must include: nature of the breach, categories and approximate number of data subjects, likely consequences, measures taken or proposed
- Notification to data subjects: if the breach is likely to result in high risk (e.g. financial fraud, identity theft), EASI (and the relevant data controller, e.g. Colruyt Group or Carrefour Belgium SA under the DPA agreements EASI-COL-DPA-2026-001) must communicate the breach directly to affected individuals; communication must be in plain language, describe the nature of the breach, provide the DPO contact, and describe the steps taken
- Notification to client controllers: EASI notifies affected clients (Colruyt Group: procurement@colruyt.be; Carrefour Belgium SA: ops@carrefour-be.eu; Delhaize Group: procurement@delhaize.eu) within 24 hours of identifying a breach affecting their data, irrespective of whether GBA notification is required; this is required under the respective Data Processing Agreements
- Documentation: all breaches must be logged in the internal breach register maintained by the DPO (dpo@easi.net), even if GBA notification is not required; the register includes date, nature, data categories, affected data subjects, actions taken, and outcome
- Annual review: the DPO presents an anonymised breach summary to EASI management and the Works Council each January; the security team (security@easi.net) uses breach data to prioritise preventive controls

---

**16. procurement_procedure_easi.docx**

**Purpose:** EASI's internal purchasing and vendor management process.

**Must include:**
- Scope: applies to all purchases of goods and services by EASI Group, including hardware (managed via framework agreement with Fujitsu Belgium NV — EASI-FUJ-FWA-2026-001), software licences, professional services, and office supplies; does NOT apply to client project expenses which are governed by individual project budgets
- Approval thresholds: <€500 → team lead approval; €500–€5,000 → department manager approval; €5,000–€25,000 → CFO approval; >€25,000 → board approval; all approvals must be obtained before placing an order; verbal approvals are not accepted
- Three-quote rule: for any purchase >€5,000 not covered by an existing framework agreement, EASI must obtain at least 3 competitive quotes; the quotes, the evaluation summary, and the approval must be documented and filed with procurement@easi.net; exceptions (single-source justification) must be approved by the CFO
- Preferred suppliers / framework agreements: for hardware, use Fujitsu Belgium NV (EASI-FUJ-FWA-2026-001); for components, use supplier1 (EASI-SUP1-MAINT-2026-001); for cloud infrastructure, use the existing Microsoft Azure enterprise agreement; check the intranet supplier list (maintained by procurement@easi.net) before approaching a new vendor
- New supplier registration: a new supplier not on the approved list must complete EASI's supplier registration form (available at `intranet.easi.net/procurement`), submit proof of business registration, a signed copy of the Supplier Code of Conduct, and evidence of GDPR compliance if the supplier will process personal data; registration approved by procurement@easi.net within 5 working days; for suppliers who will handle data from EASI clients (e.g. Colruyt Group, Carrefour Belgium SA), a Data Processing Agreement is also required
- Invoices: all supplier invoices must be sent to finance@easi.net; paper invoices must be scanned and emailed; EASI's standard payment term is 30 days net from the invoice date; for the Fujitsu Belgium NV framework agreement and the supplier1 maintenance contract, specific payment terms in those contracts apply
- Purchase cards (company credit cards): issued only to department managers and above; monthly statement must be submitted with receipts to finance@easi.net by the 5th of the following month; no private purchases; Arne Albrecht and Dorian Feaux have expense claim cards (not purchase cards) for client entertainment, governed by the Expense Policy
- Prohibited: purchasing goods or services from suppliers in which an EASI employee has a personal financial interest without prior written disclosure to the CFO

---

**17. invoice_approval_procedure_easi.docx**

**Purpose:** Step-by-step workflow for receiving, approving, and paying supplier invoices.

**Must include:**
- Receipt: all invoices must be addressed to EASI Group, Avenue Louise 65, 1050 Brussels, VAT BE 0123.456.789, and sent to finance@easi.net; invoices received by post are scanned by the receptionist and forwarded to finance@easi.net on the day of receipt
- Three-way matching: finance performs a three-way match for every invoice: (1) purchase order in the procurement system, (2) goods receipt or service delivery confirmation, (3) invoice; invoices for ongoing contracts (e.g. the €850/month maintenance retainer from supplier1 under EASI-SUP1-MAINT-2026-001, or the Fujitsu hardware invoices under EASI-FUJ-FWA-2026-001) are matched against the contract standing order; mismatches are flagged to the relevant budget owner
- Budget owner approval: after three-way match, finance routes the invoice to the budget owner for approval; budget owner must approve in the finance portal or by email to finance@easi.net within 5 working days; overdue approvals are escalated to the department manager after 5 days, then to the CFO after a further 5 days; Arne Albrecht is the budget owner for Colruyt Group project costs; Dorian Feaux is budget owner for Carrefour Belgium SA and GreenTech Solutions project costs; Nathalie Pieters is budget owner for Delhaize Group, Ferrero Benelux, and Anheuser-Busch InBev project costs
- Payment: approved invoices are paid on the due date (invoice date + stated payment term, usually 30 days); EASI uses SEPA bank transfer; payment batches are processed every Tuesday and Thursday; payment confirmations are sent by finance@easi.net to the supplier and to the budget owner
- Dispute procedure: if an invoice is incorrect (wrong amount, wrong services described, or not matching a purchase order), the budget owner contacts the supplier within 10 working days of receiving the invoice; a credit note is requested; the original invoice is placed on hold in the system; Arne Albrecht handled the disputed invoice from supplier1 related to the April batch delay (Case 00001022) — the original invoice for PROD-SUP1-001 included a late-delivery charge which EASI contested; resolution pending
- VAT reclaim: finance submits quarterly VAT returns; invoices with incorrect VAT treatment must be flagged to finance@easi.net immediately
- Archiving: all invoices and supporting documents are archived digitally for 7 years (Belgian accounting law); the archive is managed by finance@easi.net and accessible to authorised EASI staff

---

**18. change_management_procedure_easi.docx**

**Purpose:** ITIL-aligned change management process covering all changes to EASI-managed platforms.

**Must include:**
- Scope: applies to all changes to production environments managed by EASI, including the SmartSales platform (Colruyt Group — 47 locations, Carrefour Belgium SA, Delhaize Group), the In-Store Analytics Module (Carrefour Belgium SA — 12 hypermarkets), the EDI Connector (Delhaize Group AD-franchise stores), the Distribution Mapping platform (Anheuser-Busch InBev, Leuven), the GreenTech Sustainability Dashboard, and EASI's internal IT infrastructure at Avenue Louise 65
- Change types:
  - Standard change: pre-approved, low-risk, repeatable changes with a documented procedure (e.g. adding a new SmartSales user for Colruyt, updating catalogue prices in SmartSales for Ferrero Benelux); no CAB review required; documented in the change log by the implementer
  - Normal change: any change requiring assessment and CAB approval (e.g. deploying a new SmartSales module version, modifying the Carrefour analytics data pipeline, updating the Delhaize EDI connector configuration); RFC required; CAB review required
  - Emergency change: urgent change required to restore service or prevent imminent impact (e.g. emergency hotfix for the Colruyt POS integration issue — Case 00001021, or the Delhaize EDI issue — Case 00001024); verbal approval from IT manager (it@easi.net) + Arne Albrecht (as account owner) sufficient to proceed; retroactive RFC must be submitted to the change log within 24 hours
- RFC (Request for Change) process: RFC submitted via `servicedesk.easi.net`, category "Change Request"; must include: description of change, business justification, affected systems and clients, risk assessment (Low/Medium/High), rollback plan (mandatory), proposed implementation window, and requester details; Arne Albrecht or Dorian Feaux submits RFCs for client-facing changes; IT team submits RFCs for infrastructure changes
- CAB (Change Advisory Board): meets every Thursday at 14:00 at EASI's Avenue Louise 65 office (virtual attendance available); members: IT Manager (chair), Arne Albrecht, Dorian Feaux, Nathalie Pieters, Finance representative; quorum: 3 members including the chair; CAB reviews all pending normal change RFCs; approved changes are scheduled for the next available maintenance window
- Implementation windows: standard window is Saturday 22:00–06:00 Brussels time; additional window on Tuesday 02:00–04:00 for minor changes; client-specific windows may apply (e.g. Colruyt has requested no changes during the period Fri 18:00–Mon 08:00 during promotional campaign weeks — confirmed by procurement@colruyt.be); emergency changes may be implemented outside windows with CAB chair approval
- Stakeholder communication: for normal changes affecting client environments, Arne Albrecht notifies the relevant client contact (e.g. procurement@colruyt.be, ops@carrefour-be.eu, procurement@delhaize.eu) at least 48 hours before the implementation window; notifications include: what will change, expected downtime (if any), rollback plan summary, contact for questions
- Failed change / rollback: if a change causes service degradation, the implementer initiates rollback immediately; an S1 or S2 incident is raised via the Incident Management Procedure; a post-mortem is conducted within 5 working days

---

**19. business_continuity_plan_easi.docx**

**Purpose:** EASI Group's Business Continuity Plan (BCP) covering disaster scenarios, recovery targets, and crisis procedures.

**Must include:**
- Objectives: RTO (Recovery Time Objective) of 4 hours for all critical systems; RPO (Recovery Point Objective) of 1 hour (maximum data loss of 1 hour)
- Critical systems (Priority 1): (a) SmartSales platform — serves Colruyt Group (47 locations, SmartSales Rollout 2026 opportunity at €220,000), Carrefour Belgium SA (12 hypermarkets, In-Store Analytics Pilot €175,000), Delhaize Group (EDI Connector, Supply Chain Optimisation €310,000); (b) Salesforce CRM — contains all client data including opportunities for Colruyt, Carrefour, Delhaize, AB InBev, GreenTech Solutions, Ferrero Benelux, and supplier1; (c) Microsoft 365 (email, Teams, OneDrive) — critical for all internal and client communication; (d) VPN — required for all remote access to internal and client systems
- Critical systems (Priority 2): Finance ERP, HR portal, internal IT ticketing (servicedesk.easi.net)
- Infrastructure: primary data centre is located in Brussels (Azure West Europe region); failover environment in Azure North Europe (Dublin, Ireland); Fujitsu Belgium NV (under framework agreement EASI-FUJ-FWA-2026-001) provides on-site hardware maintenance and failover hardware support
- Backup policy: all critical system data backed up every hour (RPO = 1 hour); backups stored in Azure North Europe; restore tested quarterly; for Salesforce CRM, nightly full backup plus hourly incremental via the Salesforce Backup and Restore service; for SmartSales, backups include full order history, catalogue data (including PROD-SUP1-001, PROD-COL-001, PROD-CRF-001, PROD-ADL-001, PROD-ABI-001), and location data for all 10 SmartSales locations
- Crisis team: CEO (overall authority), COO (operational response), IT Manager (technical recovery), Arne Albrecht (client communication — Colruyt Group, GreenTech Solutions), Dorian Feaux (client communication — Carrefour Belgium SA, Delhaize Group, Ferrero Benelux), Nathalie Pieters (client communication — Anheuser-Busch InBev, supplier1, ongoing CS accounts), HR Manager (employee communication), Finance Director (financial impact assessment)
- Communication protocol: internal crisis communication via Microsoft Teams channel "Crisis — EASI BCP" (all crisis team members are members); external client communication is handled by the designated account managers (see above); media/press communication is handled exclusively by the CEO; client SLA implications (see SLA agreement EASI-COL-SLA-2026-001 for Colruyt; similar SLAs apply for Carrefour and Delhaize) are assessed by Arne Albrecht within 30 minutes of crisis declaration
- Disaster scenarios and responses: (a) primary data centre failure → automatic failover to Azure North Europe, IT Manager activates within 15 minutes; (b) key personnel unavailability (e.g. both Arne Albrecht and Dorian Feaux simultaneously unreachable) → Nathalie Pieters assumes client communication responsibility for all accounts; (c) ransomware attack → immediate isolation of affected systems, activate Incident Management (security@easi.net), initiate restore from last clean backup; (d) EASI offices at Avenue Louise 65 inaccessible → all staff work remotely (see Remote Work Policy), crisis team convenes via Teams
- Annual BCP exercise: tabletop exercise conducted in Q4 each year; all crisis team members participate; exercise scenario is changed annually (2025 scenario: primary data centre failure; 2026 scenario: ransomware attack); findings documented and BCP updated within 30 days of exercise

---

**20. supplier_code_of_conduct_easi.docx**

**Purpose:** EASI's requirements for all suppliers covering ethics, labour, environment, data, and compliance.

**Must include:**
- Applicability: applies to all organisations supplying goods or services to EASI Group, including hardware suppliers (Fujitsu Belgium NV — EASI-FUJ-FWA-2026-001), component suppliers (supplier1 — EASI-SUP1-MAINT-2026-001), and any new supplier onboarded via the Procurement Procedure; also applies to sub-contractors engaged by suppliers to fulfil EASI contracts; suppliers are required to communicate this Code to their own supply chain
- Labour and human rights: no child labour (minimum age: 15 years or local legal minimum if higher); no forced or compulsory labour; employees must be free to resign with reasonable notice; living wages paid in accordance with local legal requirements; maximum working hours comply with Belgian labour law (for Belgian suppliers) or local law; safe and healthy working conditions required; suppliers must permit EASI audit of labour conditions with 30 days' notice
- Environmental responsibility: suppliers with >50 employees are expected to hold ISO 14001 certification or demonstrate equivalent environmental management; all suppliers must have a documented waste disposal policy; suppliers delivering hardware (applicable to Fujitsu Belgium NV) must comply with EU WEEE Directive for end-of-life equipment management; any environmental violations must be reported to procurement@easi.net within 48 hours
- Business integrity and anti-corruption: zero tolerance for bribery, corruption, and facilitation payments; no gifts or hospitality of a value >€50 may be offered to or accepted from EASI staff or EASI clients (including Colruyt Group, Carrefour Belgium SA, Delhaize Group, Anheuser-Busch InBev, Ferrero Benelux, GreenTech Solutions); any offer of a gift above this threshold received by an EASI employee from a supplier must be declared to procurement@easi.net; suppliers must maintain accurate financial records; conflicts of interest must be disclosed
- Data protection and information security: suppliers who process personal data on behalf of EASI or EASI's clients must comply with GDPR; a Data Processing Agreement is required (see also: DPA with Colruyt Group — EASI-COL-DPA-2026-001, which lists Fujitsu Belgium NV as a sub-processor); suppliers must maintain appropriate technical and organisational security measures; EASI may require suppliers to undergo a security assessment (questionnaire or on-site audit) before and during the contract
- Supplier self-declaration: each supplier must complete and sign EASI's annual Supplier Self-Declaration form confirming compliance with this Code; the signed form must be submitted to procurement@easi.net by 31 January each year; new suppliers must submit the form as part of the supplier registration process; Marc Supplier (marc.supplier@supplier1.be) at supplier1 is the registered contact for compliance submissions; Fujitsu Belgium NV's compliance contact is account.manager@fujitsu.be
- EASI audit right: EASI reserves the right to conduct or commission audits of supplier compliance with this Code with 30 days' written notice (procurement@easi.net); audit costs borne by EASI unless a material breach is found, in which case costs are borne by the supplier
- Breach and remediation: a supplier found in breach of this Code will receive a written notice with a 30-day remediation period; if the breach is not remediated, EASI may terminate the relevant contract with immediate effect; EASI will also assess the impact on any ongoing client deliverables (e.g. Colruyt SmartSales deployment relying on Fujitsu hardware support) and activate contingency sourcing if required

---

## Practical Notes for the Generator

- Each document should reference at least 3–5 entities from the "Entity Reference" section above (client names, people names, addresses, case numbers, opportunity names, product codes)
- Semantic gaps are intentional: the document content answers questions that use different vocabulary than the document itself (e.g. the SLA agreement answers "what happens if EASI misses their support commitment to Colruyt" even though it says "service credit" and "SLA breach penalty", not "missing commitments")
- Do not add a "this is a test document" disclaimer anywhere
- The 6 existing documents (employment_regulations, expense_policy, onboarding_guide, complaint_handling, collaboration_agreement_colruyt, framework_agreement_supplier1) should NOT be regenerated; the new documents must be consistent with and complementary to those existing documents
