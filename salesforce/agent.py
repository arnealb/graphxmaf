from dataclasses import fields as dc_fields

from salesforce.models import (
    SalesforceAccount,
    SalesforceContact,
    SalesforceOpportunity,
    SalesforceCase,
    SalesforceLead,
)

_ACCOUNT_BASE = {"id", "name", "industry", "website"}
_CONTACT_BASE = {"id", "first_name", "last_name", "email", "account_name"}
_LEAD_BASE    = {"id", "first_name", "last_name", "email", "company", "status"}
_OPP_BASE     = {"id", "name", "stage", "amount", "close_date", "account_name"}
_CASE_BASE    = {"id", "subject", "status", "priority", "account_name", "created_date"}


def _extra_lines(obj, base: set[str]) -> list[str]:
    """Return 'Label: value' lines for any non-None extra fields."""
    lines = []
    for f in dc_fields(obj):
        if f.name in base:
            continue
        val = getattr(obj, f.name)
        if val is not None:
            label = f.name.replace("_", " ").title()
            lines.append(f"{label}: {val}")
    return lines


class SalesforceAgent:
    def __init__(self, repo):
        self.repo = repo

    async def find_accounts(
        self,
        query: str | None = None,
        extra_fields: list[str] | None = None,
        filters: dict[str, str] | None = None,
    ) -> str:
        accounts = await self.repo.get_accounts(
            query=query, extra_fields=extra_fields, filters=filters
        )
        if not accounts:
            return "No accounts found."
        out = []
        for a in accounts:
            lines = [
                f"ID: {a.id}",
                f"Name: {a.name}",
                f"Industry: {a.industry}",
                f"Website: {a.website}",
            ]
            lines.extend(_extra_lines(a, _ACCOUNT_BASE))
            out.append("\n".join(lines))
        return "\n\n".join(out)

    async def find_contacts(
        self,
        query: str | None = None,
        extra_fields: list[str] | None = None,
        filters: dict[str, str] | None = None,
    ) -> str:
        contacts = await self.repo.find_contacts(
            query=query, extra_fields=extra_fields, filters=filters
        )
        if not contacts:
            return "No contacts found."
        out = []
        for c in contacts:
            lines = [
                f"ID: {c.id}",
                f"Name: {c.first_name} {c.last_name}",
                f"Email: {c.email}",
                f"Account: {c.account_name}",
            ]
            lines.extend(_extra_lines(c, _CONTACT_BASE))
            out.append("\n".join(lines))
        return "\n\n".join(out)

    async def find_leads(
        self,
        query: str | None = None,
        extra_fields: list[str] | None = None,
        filters: dict[str, str] | None = None,
    ) -> str:
        leads = await self.repo.find_leads(
            query=query, extra_fields=extra_fields, filters=filters
        )
        if not leads:
            return "No leads found."
        out = []
        for lead in leads:
            lines = [
                f"ID: {lead.id}",
                f"Name: {lead.first_name} {lead.last_name}",
                f"Email: {lead.email}",
                f"Company: {lead.company}",
                f"Status: {lead.status}",
            ]
            lines.extend(_extra_lines(lead, _LEAD_BASE))
            out.append("\n".join(lines))
        return "\n\n".join(out)

    async def get_opportunities(
        self,
        account_id: str | None = None,
        stage: str | None = None,
        extra_fields: list[str] | None = None,
        filters: dict[str, str] | None = None,
    ) -> str:
        opps = await self.repo.get_opportunities(
            account_id=account_id, stage=stage, extra_fields=extra_fields, filters=filters
        )
        if not opps:
            return "No opportunities found."
        out = []
        for o in opps:
            lines = [
                f"ID: {o.id}",
                f"Name: {o.name}",
                f"Stage: {o.stage}",
                f"Amount: {o.amount}",
                f"Close date: {o.close_date}",
                f"Account: {o.account_name}",
            ]
            lines.extend(_extra_lines(o, _OPP_BASE))
            out.append("\n".join(lines))
        return "\n\n".join(out)

    async def get_cases(
        self,
        account_id: str | None = None,
        status: str | None = None,
        extra_fields: list[str] | None = None,
        filters: dict[str, str] | None = None,
    ) -> str:
        cases = await self.repo.get_cases(
            account_id=account_id, status=status, extra_fields=extra_fields, filters=filters
        )
        if not cases:
            return "No cases found."
        out = []
        for c in cases:
            lines = [
                f"ID: {c.id}",
                f"Subject: {c.subject}",
                f"Status: {c.status}",
                f"Priority: {c.priority}",
                f"Account: {c.account_name}",
            ]
            lines.extend(_extra_lines(c, _CASE_BASE))
            out.append("\n".join(lines))
        return "\n\n".join(out)
