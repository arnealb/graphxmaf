from salesforce.models import SalesforceAccount, SalesforceContact, SalesforceOpportunity, SalesforceCase, SalesforceLead


class SalesforceAgent:
    def __init__(self, repo):
        self.repo = repo

    async def find_accounts(self, query: str) -> str:
        accounts = await self.repo.get_accounts(query=query)
        if not accounts:
            return "No accounts found."
        out = []
        for a in accounts:
            out.append(
                f"ID: {a.id}\n"
                f"Name: {a.name}\n"
                f"Industry: {a.industry}\n"
                f"Website: {a.website}\n"
            )
        return "\n".join(out)

    async def find_contacts(self, query: str) -> str:
        contacts = await self.repo.find_contacts(query)
        if not contacts:
            return "No contacts found."
        out = []
        for c in contacts:
            out.append(
                f"ID: {c.id}\n"
                f"Name: {c.first_name} {c.last_name}\n"
                f"Email: {c.email}\n"
                f"Account: {c.account_name}\n"
            )
        return "\n".join(out)

    async def get_opportunities(self, account_id: str | None = None, stage: str | None = None) -> str:
        opps = await self.repo.get_opportunities(account_id=account_id, stage=stage)
        if not opps:
            return "No opportunities found."
        out = []
        for o in opps:
            out.append(
                f"ID: {o.id}\n"
                f"Name: {o.name}\n"
                f"Stage: {o.stage}\n"
                f"Amount: {o.amount}\n"
                f"Close date: {o.close_date}\n"
                f"Account: {o.account_name}\n"
            )
        return "\n".join(out)

    async def find_leads(self, query: str) -> str:
        leads = await self.repo.find_leads(query)
        if not leads:
            return "No leads found."
        out = []
        for lead in leads:
            out.append(
                f"ID: {lead.id}\n"
                f"Name: {lead.first_name} {lead.last_name}\n"
                f"Email: {lead.email}\n"
                f"Company: {lead.company}\n"
                f"Status: {lead.status}\n"
            )
        return "\n".join(out)

    async def get_cases(self, account_id: str | None = None, status: str | None = None) -> str:
        cases = await self.repo.get_cases(account_id=account_id, status=status)
        if not cases:
            return "No cases found."
        out = []
        for c in cases:
            out.append(
                f"ID: {c.id}\n"
                f"Subject: {c.subject}\n"
                f"Status: {c.status}\n"
                f"Priority: {c.priority}\n"
                f"Account: {c.account_name}\n"
            )
        return "\n".join(out)
