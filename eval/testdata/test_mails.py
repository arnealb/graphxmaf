import os
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATIE ---
CLIENT_ID = os.getenv("test_email_injector_client_id")
CLIENT_SECRET = os.getenv("test_email_injector_secret_value")
TENANT_ID = os.getenv("test_email_injector_tenant_id")
MAILBOX = "smartadmin@easigroupdemo.onmicrosoft.com"

# --- AUTH ---
def get_access_token():
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
    }
    response = requests.post(url, data=data)
    response.raise_for_status()
    return response.json()["access_token"]


# =============================================================================
# EMAILS
# =============================================================================

EMAILS = [
    {
        "from_name": "Marc Supplier",
        "from_addr": "marc.supplier@supplier1.be",
        "subject": "Follow-up: supplier1 Q2 2026 Delivery Contract",
        "body": """Dear team,

This is a follow-up regarding the supplier1 Q2 2026 Delivery Contract.

There has been an April delay in the delivery of goods from supplier1 to Brussels. The shipment originally scheduled for early April has been pushed back due to logistical issues on our end.

We are actively working to resolve this and will provide an updated timeline shortly.

Best regards,
Marc Supplier
supplier1""",
    },
    {
        "from_name": "Marc Supplier",
        "from_addr": "marc.supplier@supplier1.be",
        "subject": "supplier1 — Updated pricing for H2 2026",
        "body": """Dear team,

Please find below the updated pricing for supplier1 products, effective July 2026.

Product PROD-SUP1-001 (Industrial Components Pack) will see a price adjustment starting July 2026. The formal contract amendment will follow next week.

Best regards,
Marc Supplier
supplier1""",
    },
    {
        "from_name": "Colruyt Group Procurement",
        "from_addr": "procurement@colruyt.be",
        "subject": "Colruyt Group — SmartSales pilot bevestiging",
        "body": """Beste,

Hierbij bevestigt Colruyt Group de deelname aan het SmartSales pilootproject.

De piloot wordt opgezet vanuit onze vestiging in Halle. Het totale projectbudget bedraagt EUR 220,000, inclusief implementatie en eerste licentieperiode.

Met vriendelijke groeten,
Procurement Team
Colruyt Group""",
    },
    {
        "from_name": "GreenTech Solutions",
        "from_addr": "info@greentechsolutions.be",
        "subject": "GreenTech Solutions — Interest in sustainability dashboard",
        "body": """Hello,

GreenTech Solutions, based in Ghent, is interested in your sustainability dashboard offering.

We estimate a project scope of EUR 2,500 for the initial implementation phase. Could we schedule a call to discuss further?

Kind regards,
GreenTech Solutions
Ghent""",
    },
    {
        "from_name": "Ferrero Benelux Marketing",
        "from_addr": "marketing@ferrero.be",
        "subject": "Ferrero Benelux — Nutella spring campaign inquiry",
        "body": """Dear team,

Ferrero Benelux is planning a Nutella spring campaign centered around Brussels, featuring Nutella display jars as the key promotional item.

We would like to explore partnership opportunities for in-store activation.

Best regards,
Ferrero Benelux Marketing""",
    },
    {
        "from_name": "Dorian Feaux",
        "from_addr": "d.feaux@easi.net",
        "subject": "Intro: Dorian Feaux — EASI collaboration proposal",
        "body": """Hi,

My name is Dorian Feaux, reaching out from EASI at Avenue Louise 65, Brussels.

We see a strong opportunity to collaborate on upcoming enterprise software projects. Would you be open to a brief introductory call?

Best,
Dorian Feaux
EASI — Avenue Louise 65, Brussels""",
    },
    {
        "from_name": "SmartAdmin",
        "from_addr": "smartadmin@easigroupdemo.onmicrosoft.com",
        "subject": "Belgium region — Q1 2026 commercial summary",
        "body": """Hi team,

Q1 2026 commercial summary for the Belgium region:

- Total regional revenue: EUR 375,000
- Active accounts: supplier1, Colruyt Group, Ferrero Benelux
- Primary markets: Brussels and broader Belgium

Brussels remains the strongest market. supplier1 and Colruyt drove the majority of Q1 volume. Ferrero showed renewed interest following recent campaign discussions.

Best regards,
SmartAdmin""",
    },
]


def inject_emails(token):
    print("=" * 60)
    print("EMAILS")
    print("=" * 60)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    for i, email in enumerate(EMAILS, 1):
        payload = {
            "subject": email["subject"],
            "from": {"emailAddress": {"name": email["from_name"], "address": email["from_addr"]}},
            "toRecipients": [{"emailAddress": {"address": MAILBOX}}],
            "body": {"contentType": "Text", "content": email["body"]},
        }
        r = requests.post(
            f"https://graph.microsoft.com/v1.0/users/{MAILBOX}/messages",
            headers=headers,
            json=payload,
        )
        r.raise_for_status()
        message_id = r.json()["id"]

        r = requests.post(
            f"https://graph.microsoft.com/v1.0/users/{MAILBOX}/messages/{message_id}/move",
            headers=headers,
            json={"destinationId": "inbox"},
        )
        r.raise_for_status()
        print(f"[{i}/7] ✅ {email['subject']}")
    print()


# =============================================================================
# CALENDAR EVENTS
# =============================================================================

EVENTS = [
    {
        "subject": "supplier1 — Q2 Delivery Review",
        "start": "2026-05-10T10:00:00",
        "end":   "2026-05-10T11:00:00",
    },
    {
        "subject": "Colruyt Group — SmartSales Rollout Kickoff",
        "start": "2026-05-15T14:00:00",
        "end":   "2026-05-15T15:30:00",
    },
    {
        "subject": "GreenTech Solutions — Technical Qualification Call",
        "start": "2026-05-12T11:00:00",
        "end":   "2026-05-12T12:00:00",
    },
    {
        "subject": "Weekly sync — Dorian Feaux",
        "start": "2026-05-06T09:00:00",
        "end":   "2026-05-06T09:30:00",
    },
    {
        "subject": "Sprint review — Arne Albrecht",
        "start": "2026-05-08T14:00:00",
        "end":   "2026-05-08T15:00:00",
    },
]


def inject_events(token):
    print("=" * 60)
    print("CALENDAR EVENTS")
    print("=" * 60)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    for i, event in enumerate(EVENTS, 1):
        payload = {
            "subject": event["subject"],
            "start": {"dateTime": event["start"], "timeZone": "Europe/Brussels"},
            "end":   {"dateTime": event["end"],   "timeZone": "Europe/Brussels"},
        }
        r = requests.post(
            f"https://graph.microsoft.com/v1.0/users/{MAILBOX}/events",
            headers=headers,
            json=payload,
        )
        r.raise_for_status()
        print(f"[{i}/5] ✅ {event['subject']} ({event['start']})")
    print()


# =============================================================================
# ONEDRIVE
# =============================================================================

ONEDRIVE_FILES = [
    {
        "name": "supplier1_delivery_report_Q2_2026.txt",
        "content": """supplier1 - Q2 Delivery Report
================================
Supplier: supplier1 (SUP-001)
Period: Q2 2026 (April-June)

Orders:
- ORD-SUP1-2026-001: 10x Industrial Components Pack @ EUR 149.99 = EUR 1499.90
  Status: Shipped (5 days delay - under investigation)

Open Issues:
- April batch arrived late. supplier1 quality review initiated.
- Contract renewal (supplier1 Q2 Delivery Contract) pending signature.

Contact: Marc Supplier <marc.supplier@supplier1.be>
""",
    },
    {
        "name": "supplier1_contract_draft_Q2_2026.txt",
        "content": """Contract Draft — supplier1 Q2 Delivery Contract
=================================================
Reference: SUP-001 / Q2 2026
Counterpart: supplier1, Rue du Commerce 1, 1000 Brussels

Scope:
This contract covers the delivery of Industrial Components (PROD-SUP1-001)
for Q2 2026 under order ORD-SUP1-2026-001.

Contract Value: EUR 85,000
Payment Terms: Net 30 after confirmed delivery
Status: Negotiation/Review — pending final signature

Key Terms:
- 10 units Industrial Components Pack per delivery cycle
- Penalty clause: 2% per week for delays exceeding 7 business days
- Price adjustment (H2 2026) to be confirmed via separate amendment

Open Actions:
- Resolve April batch delay before contract can be signed
- Receive updated H2 2026 pricing from Marc Supplier

Contact: Marc Supplier <marc.supplier@supplier1.be>
""",
    },
]


def inject_onedrive(token):
    print("=" * 60)
    print("ONEDRIVE")
    print("=" * 60)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "text/plain",
    }
    for i, f in enumerate(ONEDRIVE_FILES, 1):
        r = requests.put(
            f"https://graph.microsoft.com/v1.0/users/{MAILBOX}/drive/root:/{f['name']}:/content",
            headers=headers,
            data=f["content"].encode("utf-8"),
        )
        r.raise_for_status()
        print(f"[{i}/{len(ONEDRIVE_FILES)}] ✅ {f['name']} geüpload naar OneDrive root")
    print()


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("\nToken ophalen...")
    token = get_access_token()
    print("Token verkregen.\n")

    # inject_emails(token)
    inject_events(token)
    # inject_onedrive(token)

    print("=" * 60)
    print("Klaar! Alle M365 testdata aangemaakt.")
    print("=" * 60)


if __name__ == "__main__":
    main()