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

# ---------------------------------------------------------------------------
# Per-object field allowlists
# Keys are SOQL field names; values are the model attribute names.
# ---------------------------------------------------------------------------

_ACCOUNT_SELECTABLE: dict[str, str] = {
    "Phone":              "phone",
    "Type":               "type",
    "BillingStreet":      "billing_street",
    "BillingCity":        "billing_city",
    "BillingState":       "billing_state",
    "BillingPostalCode":  "billing_postal_code",
    "BillingCountry":     "billing_country",
    "NumberOfEmployees":  "number_of_employees",
    "AnnualRevenue":      "annual_revenue",
    "Description":        "description",
    "CreatedDate":        "created_date",
    "LastModifiedDate":   "last_modified_date",
}
_ACCOUNT_FILTERABLE = frozenset({
    "Name", "Industry", "Website",
    *_ACCOUNT_SELECTABLE,
})
_ACCOUNT_NUMERIC = frozenset({"NumberOfEmployees", "AnnualRevenue"})


_CONTACT_SELECTABLE: dict[str, str] = {
    "Phone":              "phone",
    "MobilePhone":        "mobile_phone",
    "Title":              "title",
    "Department":         "department",
    "MailingStreet":      "mailing_street",
    "MailingCity":        "mailing_city",
    "MailingState":       "mailing_state",
    "MailingPostalCode":  "mailing_postal_code",
    "MailingCountry":     "mailing_country",
    "LeadSource":         "lead_source",
    "CreatedDate":        "created_date",
}
_CONTACT_FILTERABLE = frozenset({
    "FirstName", "LastName", "Email", "Account.Name",
    *_CONTACT_SELECTABLE,
})
_CONTACT_NUMERIC: frozenset[str] = frozenset()


_LEAD_SELECTABLE: dict[str, str] = {
    "Phone":             "phone",
    "MobilePhone":       "mobile_phone",
    "Title":             "title",
    "Industry":          "industry",
    "LeadSource":        "lead_source",
    "Street":            "street",
    "City":              "city",
    "State":             "state",
    "PostalCode":        "postal_code",
    "Country":           "country",
    "Rating":            "rating",
    "NumberOfEmployees": "number_of_employees",
    "AnnualRevenue":     "annual_revenue",
    "CreatedDate":       "created_date",
}
_LEAD_FILTERABLE = frozenset({
    "FirstName", "LastName", "Email", "Company", "Status",
    *_LEAD_SELECTABLE,
})
_LEAD_NUMERIC = frozenset({"NumberOfEmployees", "AnnualRevenue"})


_OPP_SELECTABLE: dict[str, str] = {
    "Probability":      "probability",
    "Type":             "type",
    "LeadSource":       "lead_source",
    "ForecastCategory": "forecast_category",
    "Description":      "description",
    "CreatedDate":      "created_date",
    "LastModifiedDate": "last_modified_date",
}
_OPP_FILTERABLE = frozenset({
    "Name", "StageName", "Account.Name",
    *_OPP_SELECTABLE,
})
_OPP_NUMERIC = frozenset({"Probability", "Amount"})


_CASE_SELECTABLE: dict[str, str] = {
    "Description":      "description",
    "Origin":           "origin",
    "Type":             "type",
    "Reason":           "reason",
    "ClosedDate":       "closed_date",
    "LastModifiedDate": "last_modified_date",
}
_CASE_FILTERABLE = frozenset({
    "Subject", "Status", "Priority", "Account.Name",
    *_CASE_SELECTABLE,
})
_CASE_NUMERIC: frozenset[str] = frozenset()


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

    @staticmethod
    def _resolve_fields(
        extra_fields: list[str] | None,
        selectable: dict[str, str],
    ) -> tuple[list[str], dict[str, str]]:
        """Return (valid_soql_fields, soql→model_attr mapping) from requested extra_fields."""
        safe, mapping = [], {}
        for f in (extra_fields or []):
            if f in selectable:
                safe.append(f)
                mapping[f] = selectable[f]
        return safe, mapping

    def _apply_filters(
        self,
        conditions: list[str],
        filters: dict[str, str] | None,
        filterable: frozenset[str],
        numeric: frozenset[str],
    ) -> None:
        """Append validated filter conditions to the conditions list."""
        for field, value in (filters or {}).items():
            if field not in filterable:
                continue
            v = self._esc(str(value))
            if field in numeric:
                conditions.append(f"{field} = {v}")
            else:
                conditions.append(f"{field} LIKE '%{v}%'")

    # ------------------------------------------------------------------
    # Accounts
    # ------------------------------------------------------------------

    async def get_accounts(
        self,
        query: str | None = None,
        extra_fields: list[str] | None = None,
        filters: dict[str, str] | None = None,
        top: int = 25,
    ) -> list[SalesforceAccount]:
        safe_extras, field_map = self._resolve_fields(extra_fields, _ACCOUNT_SELECTABLE)
        extra_cols = (", " + ", ".join(safe_extras)) if safe_extras else ""

        conditions: list[str] = []
        if query:
            conditions.append(f"Name LIKE '%{self._esc(query)}%'")
        self._apply_filters(conditions, filters, _ACCOUNT_FILTERABLE, _ACCOUNT_NUMERIC)

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        soql = f"SELECT Id, Name, Industry, Website{extra_cols} FROM Account{where} LIMIT {top}"

        records = await self._query(soql)
        return [
            SalesforceAccount(
                id=r["Id"],
                name=r["Name"],
                industry=r.get("Industry"),
                website=r.get("Website"),
                **{field_map[f]: r.get(f) for f in safe_extras},
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

    async def find_contacts(
        self,
        query: str | None = None,
        extra_fields: list[str] | None = None,
        filters: dict[str, str] | None = None,
        top: int = 10,
    ) -> list[SalesforceContact]:
        safe_extras, field_map = self._resolve_fields(extra_fields, _CONTACT_SELECTABLE)
        extra_cols = (", " + ", ".join(safe_extras)) if safe_extras else ""

        conditions: list[str] = []
        if query:
            q = self._esc(query)
            conditions.append(f"(Name LIKE '%{q}%' OR Email LIKE '%{q}%')")
        self._apply_filters(conditions, filters, _CONTACT_FILTERABLE, _CONTACT_NUMERIC)

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        soql = (
            f"SELECT Id, FirstName, LastName, Email, Account.Name{extra_cols} "
            f"FROM Contact{where} LIMIT {top}"
        )
        records = await self._query(soql)
        return [
            SalesforceContact(
                id=r["Id"],
                first_name=r.get("FirstName"),
                last_name=r["LastName"],
                email=r.get("Email"),
                account_name=(r.get("Account") or {}).get("Name"),
                **{field_map[f]: r.get(f) for f in safe_extras},
            )
            for r in records
        ]

    # ------------------------------------------------------------------
    # Leads
    # ------------------------------------------------------------------

    async def find_leads(
        self,
        query: str | None = None,
        extra_fields: list[str] | None = None,
        filters: dict[str, str] | None = None,
        top: int = 25,
    ) -> list[SalesforceLead]:
        safe_extras, field_map = self._resolve_fields(extra_fields, _LEAD_SELECTABLE)
        extra_cols = (", " + ", ".join(safe_extras)) if safe_extras else ""

        conditions: list[str] = []
        if query:
            q = self._esc(query)
            conditions.append(f"(Name LIKE '%{q}%' OR Email LIKE '%{q}%' OR Company LIKE '%{q}%')")
        self._apply_filters(conditions, filters, _LEAD_FILTERABLE, _LEAD_NUMERIC)

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        soql = (
            f"SELECT Id, FirstName, LastName, Email, Company, Status{extra_cols} "
            f"FROM Lead{where} LIMIT {top}"
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
                **{field_map[f]: r.get(f) for f in safe_extras},
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
        extra_fields: list[str] | None = None,
        filters: dict[str, str] | None = None,
        top: int = 25,
    ) -> list[SalesforceOpportunity]:
        safe_extras, field_map = self._resolve_fields(extra_fields, _OPP_SELECTABLE)
        extra_cols = (", " + ", ".join(safe_extras)) if safe_extras else ""

        conditions: list[str] = []
        if account_id:
            conditions.append(f"AccountId = '{self._esc(account_id)}'")
        if stage:
            conditions.append(f"StageName LIKE '%{self._esc(stage)}%'")
        self._apply_filters(conditions, filters, _OPP_FILTERABLE, _OPP_NUMERIC)

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        soql = (
            f"SELECT Id, Name, StageName, Amount, CloseDate, Account.Name{extra_cols} "
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
                    **{field_map[f]: r.get(f) for f in safe_extras},
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
        extra_fields: list[str] | None = None,
        filters: dict[str, str] | None = None,
        top: int = 25,
    ) -> list[SalesforceCase]:
        safe_extras, field_map = self._resolve_fields(extra_fields, _CASE_SELECTABLE)
        extra_cols = (", " + ", ".join(safe_extras)) if safe_extras else ""

        conditions: list[str] = []
        if account_id:
            conditions.append(f"AccountId = '{self._esc(account_id)}'")
        if status:
            conditions.append(f"Status LIKE '%{self._esc(status)}%'")
        self._apply_filters(conditions, filters, _CASE_FILTERABLE, _CASE_NUMERIC)

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        soql = (
            f"SELECT Id, Subject, Status, Priority, Account.Name, CreatedDate{extra_cols} "
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
                    **{field_map[f]: r.get(f) for f in safe_extras},
                )
            )
        return result
