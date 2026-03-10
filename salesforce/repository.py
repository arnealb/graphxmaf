from datetime import datetime, date

import httpx

from salesforce.models import (
    SalesforceAccount,
    SalesforceContact,
    SalesforceOpportunity,
    SalesforceCase,
    SalesforceLead,
)

_API_VERSION = "v59.0"


class SalesforceRepository:
    def __init__(self, access_token: str, instance_url: str):
        self.access_token = access_token
        self.instance_url = instance_url.rstrip("/")

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}"}

    async def _query(self, soql: str) -> list[dict]:
        url = f"{self.instance_url}/services/data/{_API_VERSION}/query"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, params={"q": soql}, headers=self._headers())
            r.raise_for_status()
            return r.json().get("records", [])

    @staticmethod
    def _esc(value: str) -> str:
        """Escape single quotes for SOQL string literals."""
        return value.replace("'", "\\'")

    # ------------------------------------------------------------------
    # Accounts
    # ------------------------------------------------------------------

    async def get_accounts(self, query: str | None = None, top: int = 25) -> list[SalesforceAccount]:
        if query:
            q = self._esc(query)
            soql = (
                f"SELECT Id, Name, Industry, Website FROM Account "
                f"WHERE Name LIKE '%{q}%' LIMIT {top}"
            )
        else:
            soql = f"SELECT Id, Name, Industry, Website FROM Account LIMIT {top}"

        records = await self._query(soql)
        return [
            SalesforceAccount(
                id=r["Id"],
                name=r["Name"],
                industry=r.get("Industry"),
                website=r.get("Website"),
            )
            for r in records
        ]

    # ------------------------------------------------------------------
    # Contacts
    # ------------------------------------------------------------------

    async def get_contact(self, contact_id: str) -> SalesforceContact | None:
        cid = self._esc(contact_id)
        soql = (
            f"SELECT Id, FirstName, LastName, Email, Account.Name "
            f"FROM Contact WHERE Id = '{cid}' LIMIT 1"
        )
        records = await self._query(soql)
        if not records:
            return None
        r = records[0]
        return SalesforceContact(
            id=r["Id"],
            first_name=r.get("FirstName"),
            last_name=r["LastName"],
            email=r.get("Email"),
            account_name=(r.get("Account") or {}).get("Name"),
        )

    async def find_contacts(self, query: str, top: int = 10) -> list[SalesforceContact]:
        q = self._esc(query)
        soql = (
            f"SELECT Id, FirstName, LastName, Email, Account.Name FROM Contact "
            f"WHERE Name LIKE '%{q}%' OR Email LIKE '%{q}%' LIMIT {top}"
        )
        records = await self._query(soql)
        return [
            SalesforceContact(
                id=r["Id"],
                first_name=r.get("FirstName"),
                last_name=r["LastName"],
                email=r.get("Email"),
                account_name=(r.get("Account") or {}).get("Name"),
            )
            for r in records
        ]

    # ------------------------------------------------------------------
    # Leads
    # ------------------------------------------------------------------

    async def find_leads(self, query: str, top: int = 25) -> list[SalesforceLead]:
        q = self._esc(query)
        soql = (
            f"SELECT Id, FirstName, LastName, Email, Company, Status FROM Lead "
            f"WHERE Name LIKE '%{q}%' OR Email LIKE '%{q}%' OR Company LIKE '%{q}%' "
            f"LIMIT {top}"
        )
        records = await self._query(soql)
        return [
            SalesforceLead(
                id=r["Id"],
                first_name=r.get("FirstName"),
                last_name=r["LastName"],
                email=r.get("Email"),
                company=r.get("Company"),
                status=r.get("Status"),
            )
            for r in records
        ]

    # ------------------------------------------------------------------
    # Opportunities
    # ------------------------------------------------------------------

    async def get_opportunities(
        self,
        account_id: str | None = None,
        stage: str | None = None,
        top: int = 25,
    ) -> list[SalesforceOpportunity]:
        conditions: list[str] = []
        if account_id:
            conditions.append(f"AccountId = '{self._esc(account_id)}'")
        if stage:
            conditions.append(f"StageName LIKE '%{self._esc(stage)}%'")

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        soql = (
            f"SELECT Id, Name, StageName, Amount, CloseDate, Account.Name "
            f"FROM Opportunity{where} LIMIT {top}"
        )

        records = await self._query(soql)
        result = []
        for r in records:
            close_date = date.fromisoformat(r["CloseDate"]) if r.get("CloseDate") else None
            result.append(
                SalesforceOpportunity(
                    id=r["Id"],
                    name=r["Name"],
                    stage=r["StageName"],
                    amount=r.get("Amount"),
                    close_date=close_date,
                    account_name=(r.get("Account") or {}).get("Name"),
                )
            )
        return result

    # ------------------------------------------------------------------
    # Cases
    # ------------------------------------------------------------------

    async def get_cases(
        self,
        account_id: str | None = None,
        status: str | None = None,
        top: int = 25,
    ) -> list[SalesforceCase]:
        conditions: list[str] = []
        if account_id:
            conditions.append(f"AccountId = '{self._esc(account_id)}'")
        if status:
            conditions.append(f"Status LIKE '%{self._esc(status)}%'")

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        soql = (
            f"SELECT Id, Subject, Status, Priority, Account.Name, CreatedDate "
            f"FROM Case{where} LIMIT {top}"
        )

        records = await self._query(soql)
        result = []
        for r in records:
            created = (
                datetime.fromisoformat(r["CreatedDate"].replace("Z", "+00:00"))
                if r.get("CreatedDate")
                else None
            )
            result.append(
                SalesforceCase(
                    id=r["Id"],
                    subject=r["Subject"],
                    status=r["Status"],
                    priority=r.get("Priority"),
                    account_name=(r.get("Account") or {}).get("Name"),
                    created_date=created,
                )
            )
        return result
