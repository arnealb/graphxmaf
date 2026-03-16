  Authentication Issues

  1. No Salesforce token refresh / expiry handling
  - main.py:188 gets a Salesforce token once at startup, then it's baked into httpx.AsyncClient headers forever. JWT tokens expire (typically 1–2 hours). The app will silently fail mid-session with 401s.
  - The StaticTokenCredential in auth/token_credential.py:14 also fakes expiry as now + 3600 — it never actually refreshes.

  2. Salesforce token passed as a plain dict key in _agent_cache
  - salesforce/mcp_router.py:22 — the cache key is the raw access token string. This creates a memory leak: every new token creates a new cache entry. There's no eviction, no TTL, no max size.

  3. Token stored in a plaintext file
  - main.py:33 — .token_cache.bin is a plaintext MSAL token cache on disk. Not encrypted, not .gitignored safely. Anyone with filesystem access can replay the token.

  4. Microsoft auth only tries accounts[0]
  - main.py:73 — if multiple accounts are cached, it silently uses the first one without checking if it's the right user.

  ---
  Salesforce-specific Issues

  5. print() left in production code
  - salesforce/repository.py:192 — print("soql: ", soql) — debug statement that logs full SOQL queries to stdout.

  6. Private key files in the repo root
  - salesforce.crt and salesforce.key are sitting at the project root. Even if .gitignored they're risky. These should be in a secrets store or at minimum a separate non-committed location.

  7. No SOQL injection protection for numeric fields
  - repository.py:162-163 — numeric fields skip the LIKE escape and are inserted raw: f"{field} = {v}". If someone passes "1 OR 1=1" as a numeric value, it becomes invalid SOQL rather than a security error,
  but there's no explicit numeric validation.

  8. API version hardcoded
  - repository.py:13 — _API_VERSION = "v59.0" — v59.0 is old (Winter '23). Salesforce is at v63.0 now.

  ---
  Architecture Issues

  9. No error handling for sub-agent failures in orchestrator
  - orchestrator_agent.py:19,23 — both ask_graph_agent and ask_salesforce_agent return "(no response from X)" as a string, but exceptions from agent.run() will propagate unhandled up to the orchestrator.

  10. Duplicate env loading across every agent file
  - salesforce_agent.py:6-11, orchestrator_agent.py:8-12, and agents/graph_agent.py all call load_dotenv() and re-read the same env vars independently. This is fine functionally but messy — the config should
  be centralized.


iets van ik vind geen entries met rrne -> bedoel je arne? 

---
- vraag aan dorian: 
2. Privacy van bedrijfsdata

Hier gaat het over:

gevoelige informatie

persoonsgegevens

vertrouwelijke documenten

interne communicatie

klantgegevens

Je systeem haalt mogelijk data op uit e-mails, CRM, documenten enzovoort. Dus je moet uitleggen dat niet alle data zomaar naar een taalmodel gestuurd mag worden. Belangrijke vragen:

welke data mag doorgestuurd worden?

hoeveel context geef je mee?

vermijd je onnodige blootstelling van gevoelige data?

hoe ga je om met logging en caching?

Dit is belangrijker dan veel studenten denken.

---

---
fetch me all information you can find on Advanced Communications

Here is the information available about Advanced Communications:

From Salesforce:
- **Account Information:**
  - **Name:** Advanced Communications
  - **Industry:** Communications
  - **Website:** [www.advancedcomms.net](http://www.advancedcomms.net)
  - **Phone:** Not available
  - **Number of Employees:** Not available
  - **Annual Revenue:** Not available
  - **Description:** Not available
  
- **Contacts:** No contact information found.

- **Leads:** No leads found.

### From Microsoft 365:
- No information retrieved.

If you need specific details or further assistance, please let me know!

-> maar is wel informatie over anual revenue en stuff
---