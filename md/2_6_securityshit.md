Ja, maar je mag 2.6 niet reduceren tot: “als de user geen access heeft, geeft de API een fout”.

Dat is **een deel** van security, maar veel te beperkt voor een scriptie.
In dat hoofdstuk moet je tonen welke bredere risico’s en vereisten er zijn wanneer een AI-systeem toegang krijgt tot bedrijfsdata.

## Wat moet daar zeker in?

### 1. Authenticatie en autorisatie

Hier leg je uit:

* **authenticatie**: het verifiëren van de identiteit van de gebruiker of applicatie
* **autorisatie**: bepalen tot welke data en functionaliteiten die geauthenticeerde entiteit toegang heeft

In jouw case is dat inderdaad vaak user-based toegang:

* de agent of MCP-tool roept een externe API aan in naam van de gebruiker
* de onderliggende systemen blijven hun eigen toegangsrechten afdwingen
* als een gebruiker geen rechten heeft, zal de API de toegang weigeren

Maar je moet erbij zeggen dat dit nuttig is omdat:

* de bestaande toegangscontrole van bronsystemen behouden blijft
* de agent dus niet zomaar meer rechten krijgt dan de gebruiker zelf

### 2. Privacy van bedrijfsdata

Hier gaat het over:

* gevoelige informatie
* persoonsgegevens
* vertrouwelijke documenten
* interne communicatie
* klantgegevens

Je systeem haalt mogelijk data op uit e-mails, CRM, documenten enzovoort. Dus je moet uitleggen dat niet alle data zomaar naar een taalmodel gestuurd mag worden. Belangrijke vragen:

* welke data mag doorgestuurd worden?
* hoeveel context geef je mee?
* vermijd je onnodige blootstelling van gevoelige data?
* hoe ga je om met logging en caching?

Dit is belangrijker dan veel studenten denken.

### 3. Governance

Dit is het meest vage begrip, dus je moet het concreet maken. In jouw context betekent governance vooral:

* duidelijke regels over welke tools beschikbaar zijn
* controle over welke databronnen aangesproken mogen worden
* afbakening van welke acties agents mogen uitvoeren
* auditability: kunnen nagaan wat het systeem deed
* traceerbaarheid: welke tool werd aangeroepen, met welke input, en welk resultaat kwam terug

Dus governance = controle en beleid rond het gebruik van data en tools.

### 4. Least privilege

Heel belangrijk om te vermelden:
agents en tools mogen idealiter enkel toegang hebben tot wat strikt noodzakelijk is.

Dus:

* geen brede rechten als read-only volstaat
* geen toegang tot alle mailboxen of alle documentsites als dat niet nodig is
* scoped permissions waar mogelijk

Dat is een sterk principe om expliciet te noemen.

### 5. Risico van indirecte data-exposure

Zelfs als een API correct toegang weigert, kan er nog risico zijn:

* gevoelige data kan in prompts terechtkomen
* output kan informatie samenvatten die de gebruiker niet volledig had mogen zien als filtering fout loopt
* logs kunnen gevoelige info bevatten
* tussenresultaten of caches kunnen data bewaren

Dus security is niet alleen “API geeft 403”.

### 6. Tool- en action control

Niet elke tool is even veilig:

* read-only tools zijn veiliger
* write-acties, deletes of updates zijn gevoeliger
* een agent mag niet zomaar autonome acties uitvoeren zonder controle

Dus je kan zeggen dat in enterprisecontext expliciet moet worden bepaald:

* welke tools read-only zijn
* welke acties menselijke bevestiging vereisen
* welke oproepen gelogd of beperkt worden

### 7. Foutafhandeling en veilige defaults

Ook relevant:
als een tool faalt of een gebruiker geen rechten heeft, moet het systeem:

* veilig falen
* geen ongeoorloofde fallback doen
* geen misleidend antwoord hallucineren alsof de data wel beschikbaar was

Dat is een heel goed punt voor jouw thesis:
een autorisatiefout moet correct behandeld
