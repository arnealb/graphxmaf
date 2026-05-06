# Analysis 05 — Authenticatie, autorisatie en governance

## 1. Microsoft Graph / MS365

### Authenticatiemethode
**OAuth2 Authorization Code Flow (PKCE-variant via MSAL ConfidentialClientApplication)**

Twee scenario's:
1. **Orchestrator-initiatie** (`startup.py`): MSAL `ConfidentialClientApplication` met `client_secret`. Bij eerste run: browser-auth via `webbrowser.open(flow["auth_uri"])` en lokale callback-server op poort 5001. Token wordt gecached in `.token_cache.bin`.
2. **MCP-server (agent_framework-interactie)**: De Graph MCP-server (`graph/mcp_server.py`) fungeert als OAuth-proxy. Het inkomende Bearer-token (uitgerold door de orchestrator/UI) wordt uitgewisseld voor een Graph-token via de **On-Behalf-Of (OBO)** flow (regels 101–128 van `graph/mcp_server.py`):

```python
data = {
    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
    "client_id": _CLIENT_ID,
    "client_secret": _azure_settings["clientSecret"],
    "assertion": assertion,
    "scope": " ".join(_GRAPH_SCOPES),
    "requested_token_use": "on_behalf_of",
}
```

**Opmerking**: In de huidige code is OBO uitgecommentarieerd. Regel 131–132 van `graph/mcp_server.py`:
```python
# register_graph_tools(mcp, _azure_settings, _extract_and_exchange_token)
register_graph_tools(mcp, _azure_settings, extract_session_token)
```
De `extract_session_token` functie extraheert enkel het Bearer-token uit de `Authorization`-header zonder OBO-uitwisseling. Dit suggereert dat het token dat de orchestrator doorstuurt direct door de Graph SDK wordt gebruikt, of dat de OBO-stap tijdelijk is uitgeschakeld.

### Gedelegeerde toegang

De gevraagde Microsoft Graph-scopes in `config.cfg`:
```
https://graph.microsoft.com/User.Read
https://graph.microsoft.com/User.Read.All
https://graph.microsoft.com/Mail.Read
https://graph.microsoft.com/Calendars.Read
https://graph.microsoft.com/Contacts.Read
https://graph.microsoft.com/Files.Read.All
https://graph.microsoft.com/People.Read
```

Dit zijn gedelegeerde scopes (namens de ingelogde gebruiker). De autorisatie is gebaseerd op de rechten van de gebruiker in Microsoft 365; de applicatie kan niet meer ophalen dan de gebruiker zelf mag zien.

### Waar tokens/secrets zitten

| Locatie | Inhoud |
|---|---|
| `.env` | `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `deployment` |
| `config.cfg` | `clientId`, `tenantId`, `clientSecret`, `graphUserScopes` |
| `.token_cache.bin` | MSAL SerializableTokenCache (access + refresh tokens) — plaintext JSON-bestand |

**Risico**: `.token_cache.bin` bevat geserialiseerde refresh-tokens in plaintext. Het bestand staat in de projectroot en is niet versleuteld. Bij onbedoelde blootstelling kunnen tokens worden misbruikt totdat ze vervallen.

### Token refresh

MSAL beheert automatisch refresh via `acquire_token_silent()` (`startup.py`, regels 53–62). Bij cache-hit wordt het token vernieuwd als het bijna vervalt. Bij mislukking valt het systeem terug naar de browser-auth flow.

### User permissions afgedwongen

De Microsoft Graph API dwingt de gebruikersrechten af op serverniveau. Als de gebruiker geen `Mail.Read`-toestemming heeft gegeven, retourneert Graph een 403. Dit is volledig op MS-zijde afgedwongen en buiten controle van de applicatie.

---

## 2. Salesforce CRM

### Authenticatiemethode
**OAuth2 Authorization Code Flow (browser-gebaseerd)**

De gebruiker wordt doorgestuurd naar `<sf_url>/auth/salesforce/login` → Salesforce consent page. Na authenticatie verwerkt `/auth/salesforce/callback` de autorisatiecode en wisselt die in voor tokens.

De `salesforce/auth.py` ondersteunt ook een **JWT Bearer Flow** (`authenticate_jwt()`), maar in de huidige `mcp_server.py`-code wordt alleen de Authorization Code Flow gebruikt voor de browser-gestuurde flow.

### Sessiemanagement

Na succesvolle auth:
1. `StoredTokens.from_token_response(token_data)` bouwt het token-object
2. `_token_store.save(session_token, tokens)` persisteert in `JsonFileTokenStore` (`.salesforce_tokens.json`)
3. `_write_session_ref(session_token)` schrijft de UUID naar `.sf_session.json`
4. Toekomstige requests: `extract_session_token(ctx)` extraheert UUID → `_resolve_session()` haalt tokens op en refresht indien nodig

### Token refresh

`salesforce/mcp_server.py`, `_resolve_session()` (regels 191–234): Als `tokens.is_expired()` (buffer van 300 seconden), wordt `refresh_access_token()` aangeroepen. Salesforce roteert refresh-tokens niet standaard, dus de bestaande refresh-token wordt bewaard. Bij refresh-fout wordt de sessie verwijderd en een foutmelding met re-auth URL teruggegeven.

### Waar tokens/secrets zitten

| Locatie | Inhoud |
|---|---|
| `.env` | `SF_CLIENT_ID`, `SF_CLIENT_SECRET`, `SF_LOGIN_URL`, `SF_OAUTH_CALLBACK_URL` |
| `.salesforce_tokens.json` | `JsonFileTokenStore`: access_token, refresh_token, instance_url, expires_at (plaintext) |
| `.sf_session.json` | Verwijzing naar actieve sessie UUID |

**Risico**: `.salesforce_tokens.json` bevat plaintext access- en refresh-tokens. Er is een optionele Fernet-encryptie (`SF_TOKEN_STORE_ENCRYPTION_KEY`), maar dit is niet standaard ingesteld. De `AzureKeyVaultTokenStore` is beschikbaar als productie-alternatief.

### CSRF-beveiliging

`_pending_states: set[str] = set()` (`salesforce/mcp_server.py`, regel 49): State-parameter voor CSRF-bescherming bij de OAuth-callback.

### User permissions

De Salesforce-access is delegatief via OAuth2. De gebruiker geeft toestemming voor scope `"api refresh_token"`. De daadwerkelijke data-toegang wordt bepaald door de Salesforce-profielrechten van de geauthenticeerde gebruiker. De applicatie kan niet meer ophalen dan de gebruiker in Salesforce mag zien.

---

## 3. SmartSales

### Authenticatiemethode
**Aangepaste client credentials flow (geen browser-interactie)**

```python
# smartsales/auth.py, regels 42-79
def authenticate_smartsales(*, grant_type, code, client_id, client_secret):
    data = {
        "grant_type": grant_type,
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    resp = httpx.post(_TOKEN_URL, data=data, timeout=30)
```

Token URL: `https://proxy-smartsales.easi.net/proxy/rest/auth/v3/token`

Dit is een server-to-server authenticatie: de credentials staan in omgevingsvariabelen en er is geen gebruikersinteractie. De token is een toepassingstoken, niet gekoppeld aan een individuele gebruiker.

### Gedelegeerde toegang

**Niet van toepassing.** SmartSales gebruikt server-to-server authenticatie. Het systeem authentiseert als de applicatie zelf, niet namens een individuele gebruiker. Dit betekent dat alle SmartSales-data zichtbaar is via de applicatiecredentials, ongeacht welke gebruiker de query uitvoert.

**Architecturaal risico**: Als de applicatie-credentials worden gebruikt door meerdere gebruikers, is er geen onderscheid mogelijk in welke gebruiker welke data heeft opgevraagd. Er is ook geen garantie dat gebruikersrechten vanuit SmartSales worden gerespecteerd.

### Waar tokens/secrets zitten

| Locatie | Inhoud |
|---|---|
| `.env` | `GRANT_TYPE`, `CODE_SMARTSALES`, `CLIENT_ID_SMARTSALES`, `CLIENT_SECRET_SMARTSALES` |
| `.ss_session.json` | Verwijzing naar actieve sessie UUID |
| SmartSales token store | Access + refresh tokens in tokenstore |

### Token refresh

Bij `tokens.is_expired()`: `authenticate_from_env()` opnieuw aanroepen (`smartsales/mcp_server.py`, regels 105–118). Dit vervangt de tokens in de store. Geen aparte refresh-token flow; herAuthenticatie vanuit env-variabelen.

---

## 4. Samenvatting per databron

| Aspect | Graph/MS365 | Salesforce | SmartSales |
|---|---|---|---|
| Flow | Auth Code + MSAL cache | Auth Code Flow (browser) | Client credentials (env) |
| Gedelegeerd | Ja (namens gebruiker) | Ja (namens gebruiker) | Nee (applicatie-account) |
| Token-opslag | `.token_cache.bin` (MSAL) | `.salesforce_tokens.json` | SmartSales token store |
| Refresh | MSAL automatisch | Eigen `refresh_access_token()` | Herautenthenticatie van env |
| Encryptie opslag | Nee (plaintext) | Optioneel (Fernet) | Niet waarneembaar |
| User rechten gerespecteerd | Ja (MS Graph API) | Ja (Salesforce API) | Niet aantoonbaar |
| Productie-store | Niet geïmplementeerd voor MSAL cache | `AzureKeyVaultTokenStore` beschikbaar | Niet waarneembaar |

---

## 5. Thesis-ready paragraaf: Governance, authenticatie en autorisatie

### Governance, authenticatie en autorisatie binnen de voorgestelde architectuur

De drie geïntegreerde systemen — Microsoft 365 via de Graph API, Salesforce CRM en het SmartSales-platform — kennen elk een eigen authenticatiearchitectuur die in de implementatie afzonderlijk is uitgewerkt.

Voor Microsoft 365 wordt gebruik gemaakt van de OAuth 2.0 Authorization Code Flow in combinatie met de MSAL-bibliotheek. Tijdens de opstartfase authentiseert de applicatie zich namens de geauthenticeerde gebruiker via een browser-interactie, waarbij de verkregen tokens worden gecached in een lokaal bestand (`.token_cache.bin`). De Graph MCP-server biedt tevens ondersteuning voor een On-Behalf-Of (OBO) mechanisme, waarmee het inkomende Bearer-token kan worden uitgewisseld voor een Graph-specifiek token met de gevraagde scopes (`User.Read`, `Mail.Read`, `Calendars.Read`, `Files.Read.All`, `People.Read`). In de huidige productieconfiguratie is de OBO-uitwisseling echter uitgecommentarieerd ten gunste van directe tokendoorgifte via `extract_session_token()`. De Microsoft Graph API dwingt op serverniveau de gebruikersrechten af: de applicatie ontvangt enkel data waartoe de ingelogde gebruiker bevoegd is.

Bij Salesforce wordt eveneens de OAuth 2.0 Authorization Code Flow gehanteerd, waarbij de gebruiker via een browsersessie toestemming geeft voor scope `api refresh_token`. De verkregen access- en refresh-tokens worden opgeslagen in een lokaal JSON-bestand (`.salesforce_tokens.json`) via de `JsonFileTokenStore`. Voor productie-omgevingen is een `AzureKeyVaultTokenStore` geïmplementeerd die tokens als geëncrypteerde secrets opslaat in Azure Key Vault. De `_resolve_session()`-functie in `salesforce/mcp_server.py` controleert bij elke tool-aanroep of het token nog geldig is en vernieuwt het automatisch indien nodig, met een buffer van 300 seconden voor de vervaldatum. Salesforce dwingt de autorisatie af op objectniveau: de applicatie kan niet meer ophalen dan de Salesforce-profielrechten van de geauthenticeerde gebruiker toestaan.

Het SmartSales-systeem hanteert een server-to-server authenticatiestroom waarbij de applicatiecredentials (`CLIENT_ID_SMARTSALES`, `CLIENT_SECRET_SMARTSALES`, `CODE_SMARTSALES`) uit omgevingsvariabelen worden geladen. Er is geen browser-interactie vereist en de authenticatie vindt automatisch plaats bij serverstart. Dit impliceert dat de toegang tot SmartSales niet aan een individuele eindgebruiker is gekoppeld, maar aan de applicatieregistratie zelf. Er bestaat daardoor geen mechanisme om per-gebruiker toegangscontrole vanuit SmartSales af te dwingen: alle gebruikers van het systeem krijgen via dezelfde applicatiecredentials toegang tot dezelfde SmartSales-data. Dit onderscheidt zich wezenlijk van de gedelegeerde toegangsmodellen bij Graph en Salesforce, waarbij het token-based mechanisme garandeert dat individuele gebruikersrechten worden gerespecteerd.

Wat tokenopslag betreft, stellen de huidige lokale opslag van tokens in plaintext-bestanden (`.token_cache.bin`, `.salesforce_tokens.json`) risico's voor bij onbedoelde blootstelling van het bestandssysteem. Voor de Graph-cache is geen versleuteling geïmplementeerd. Voor de Salesforce-opslag is optionele Fernet-encryptie beschikbaar maar niet standaard ingeschakeld. In een productie-omgeving met Azure Key Vault voor Salesforce-tokens wordt dit risico deels gemitigeerd; voor de Graph-tokencache is echter geen equivalent productie-alternatief geïmplementeerd.

Op het vlak van autorisatie binnen de multi-agent-architectuur is het relevant op te merken dat de orchestrator geen toegangsbeleid afdwingt op het niveau van de gebruikersvraag. De orchestrator routeert alle vragen naar alle beschikbare agents ongeacht de bevoegdheid van de vragende gebruiker in die specifieke systemen. De autorisatie-handhaving is volledig gedelegeerd aan de bronsystemen zelf: Graph, Salesforce en SmartSales retourneren enkel data waartoe het gebruikte token bevoegd is. Deze aanpak is functioneel correct voor gedelegeerde flows (Graph, Salesforce), maar introduceert een governance-leemte voor SmartSales waar de server-to-server authenticatie niet aan een individuele gebruiker is gekoppeld. Een volgende architectuurversie zou kunnen overwegen een centrale autorisatielaag toe te voegen die bepaalt welke vragen naar welke systemen mogen worden doorgestuurd op basis van de identiteit van de vragende gebruiker, onafhankelijk van de backend-autorisatie.
