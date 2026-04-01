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
_ACCOUNT_NOT_NULL = frozenset({
    "Name", "Industry", "Website", "Phone", "Type",
    "BillingCity", "BillingCountry", "BillingPostalCode",
})


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
_CONTACT_NOT_NULL = frozenset({
    "Email", "FirstName", "LastName", "Name", "Phone", "MobilePhone",
    "Title", "Department", "Account.Name",
})


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
    "FirstName", "LastName", "Email", "Company", "Status", "IsConverted",
    *_LEAD_SELECTABLE,
})
_LEAD_NUMERIC = frozenset({"NumberOfEmployees", "AnnualRevenue"})
_LEAD_BOOLEAN = frozenset({"IsConverted"})
_LEAD_NOT_NULL = frozenset({
    "Email", "FirstName", "LastName", "Company", "Status",
    "Phone", "Industry", "Country", "City",
})


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
    "Name", "StageName", "Account.Name", "IsClosed",
    *_OPP_SELECTABLE,
})
_OPP_NUMERIC = frozenset({"Probability", "Amount"})
_OPP_BOOLEAN = frozenset({"IsClosed"})
_OPP_NOT_NULL = frozenset({
    "Name", "Amount", "CloseDate", "StageName", "Account.Name",
})


_CASE_SELECTABLE: dict[str, str] = {
    "Description":      "description",
    "Origin":           "origin",
    "Type":             "type",
    "Reason":           "reason",
    "ClosedDate":       "closed_date",
    "LastModifiedDate": "last_modified_date",
}
_CASE_FILTERABLE = frozenset({
    "Subject", "Status", "Priority", "Account.Name", "IsClosed",
    *_CASE_SELECTABLE,
})
_CASE_NUMERIC: frozenset[str] = frozenset()
_CASE_BOOLEAN = frozenset({"IsClosed"})
_CASE_NOT_NULL = frozenset({
    "Subject", "Status", "Priority", "Account.Name",
    "CaseNumber", "Description", "ClosedDate",
})


class SalesforceRepository:
    def __init__(self, access_token: str, instance_url: str):
        self.access_token = access_token
        self.instance_url = instance_url.rstrip("/")

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}"}

    async def _query(self, soql: str) -> list[dict]:
        # Endpoint: GET {instance_url}/services/data/{version}/query?q={soql}
        # All repository methods funnel through this single REST endpoint.
        # Docs — REST API Query resource:
        #   https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/resources_query.htm
        # Docs — SOQL syntax reference:
        #   https://developer.salesforce.com/docs/atlas.en-us.soql_sosl.meta/soql_sosl/sforce_api_calls_soql.htm
        url = f"{self.instance_url}/services/data/{_API_VERSION}/query"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, params={"q": soql}, headers=self._headers())
            r.raise_for_status()
            return r.json().get("records", [])

    @staticmethod
    def _esc(value: str) -> str:
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

    @staticmethod
    def _apply_not_null(
        conditions: list[str],
        not_null_fields: list[str] | None,
        allowed: frozenset[str],
    ) -> None:
        """Append field != null conditions for each requested field that is in the allowlist."""
        for field in (not_null_fields or []):
            if field in allowed:
                conditions.append(f"{field} != null")

    def _apply_filters(
        self,
        conditions: list[str],
        filters: dict[str, str] | None,
        filterable: frozenset[str],
        numeric: frozenset[str],
        boolean: frozenset[str] = frozenset(),
    ) -> None:
        """Append validated filter conditions to the conditions list."""
        for field, value in (filters or {}).items():
            if field not in filterable:
                continue
            if field in boolean:
                soql_bool = "true" if str(value).lower() in ("true", "1", "yes") else "false"
                conditions.append(f"{field} = {soql_bool}")
            elif field in numeric:
                v = self._esc(str(value))
                conditions.append(f"{field} = {v}")
            else:
                v = self._esc(str(value))
                conditions.append(f"{field} LIKE '%{v}%'")

    # ------------------------------------------------------------------
    # Accounts
    # Salesforce Object: Account
    # SOQL: SELECT ... FROM Account [WHERE ...] LIMIT n
    # Object reference (all fields + types):
    #   https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/sforce_api_objects_account.htm
    # ------------------------------------------------------------------

    async def get_accounts(
        self,
        query: str | None = None,
        extra_fields: list[str] | None = None,
        filters: dict[str, str] | None = None,
        not_null_fields: list[str] | None = None,
        top: int = 25,
    ) -> list[SalesforceAccount]:
        safe_extras, field_map = self._resolve_fields(extra_fields, _ACCOUNT_SELECTABLE)
        extra_cols = (", " + ", ".join(safe_extras)) if safe_extras else ""

        conditions: list[str] = []
        if query and not (filters and "Name" in filters):
            conditions.append(f"Name LIKE '%{self._esc(query)}%'")
        self._apply_not_null(conditions, not_null_fields, _ACCOUNT_NOT_NULL)
        self._apply_filters(conditions, filters, _ACCOUNT_FILTERABLE, _ACCOUNT_NUMERIC)

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        soql = f"SELECT Id, Name, Industry, Website{extra_cols} FROM Account{where} LIMIT {top}"

        print("soql: ", soql)

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
    # Salesforce Object: Contact
    # SOQL: SELECT ... FROM Contact [WHERE ...] LIMIT n
    # Object reference (all fields + types):
    #   https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/sforce_api_objects_contact.htm
    # Note: Account.Name uses a relationship query (dot-notation) to the parent
    # Account object — see relationship query docs:
    #   https://developer.salesforce.com/docs/atlas.en-us.soql_sosl.meta/soql_sosl/sforce_api_calls_soql_relationships.htm
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
        not_null_fields: list[str] | None = None,
        top: int = 10,
    ) -> list[SalesforceContact]:
        safe_extras, field_map = self._resolve_fields(extra_fields, _CONTACT_SELECTABLE)
        extra_cols = (", " + ", ".join(safe_extras)) if safe_extras else ""

        conditions: list[str] = []
        if query:
            q = self._esc(query)
            conditions.append(f"(Name LIKE '%{q}%' OR Email LIKE '%{q}%')")
        self._apply_not_null(conditions, not_null_fields, _CONTACT_NOT_NULL)
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
    # Salesforce Object: Lead
    # SOQL: SELECT ... FROM Lead [WHERE ...] LIMIT n
    # Object reference (all fields + types):
    #   https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/sforce_api_objects_lead.htm
    # Note: IsConverted is a standard boolean field on Lead; it becomes true
    # when the lead is converted to an Account/Contact/Opportunity.
    # ------------------------------------------------------------------

    async def find_leads(
        self,
        query: str | None = None,
        extra_fields: list[str] | None = None,
        filters: dict[str, str] | None = None,
        not_null_fields: list[str] | None = None,
        top: int = 25,
    ) -> list[SalesforceLead]:
        safe_extras, field_map = self._resolve_fields(extra_fields, _LEAD_SELECTABLE)
        extra_cols = (", " + ", ".join(safe_extras)) if safe_extras else ""

        conditions: list[str] = []
        if query:
            q = self._esc(query)
            conditions.append(f"(Name LIKE '%{q}%' OR Email LIKE '%{q}%' OR Company LIKE '%{q}%')")
        self._apply_not_null(conditions, not_null_fields, _LEAD_NOT_NULL)
        self._apply_filters(conditions, filters, _LEAD_FILTERABLE, _LEAD_NUMERIC, _LEAD_BOOLEAN)

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
    # Salesforce Object: Opportunity
    # SOQL: SELECT ... FROM Opportunity [WHERE ...] LIMIT n
    # Object reference (all fields + types):
    #   https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/sforce_api_objects_opportunity.htm
    # Note: IsClosed is a formula boolean — true when StageName is a "Closed"
    # stage (Closed Won / Closed Lost). Use IsClosed = false for open opps.
    # Standard stage values:
    #   https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/sforce_api_objects_opportunity.htm#kanchor861
    # ------------------------------------------------------------------

    async def get_opportunities(
        self,
        account_id: str | None = None,
        stage: str | None = None,
        min_amount: str | None = None,
        extra_fields: list[str] | None = None,
        filters: dict[str, str] | None = None,
        not_null_fields: list[str] | None = None,
        top: int = 25,
    ) -> list[SalesforceOpportunity]:
        safe_extras, field_map = self._resolve_fields(extra_fields, _OPP_SELECTABLE)
        extra_cols = (", " + ", ".join(safe_extras)) if safe_extras else ""

        conditions: list[str] = []
        if account_id:
            conditions.append(f"AccountId = '{self._esc(account_id)}'")
        if stage:
            conditions.append(f"StageName LIKE '%{self._esc(stage)}%'")
        if min_amount is not None:
            conditions.append(f"Amount >= {min_amount}")
        self._apply_not_null(conditions, not_null_fields, _OPP_NOT_NULL)
        self._apply_filters(conditions, filters, _OPP_FILTERABLE, _OPP_NUMERIC, _OPP_BOOLEAN)

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
    # Salesforce Object: Case
    # SOQL: SELECT ... FROM Case [WHERE ...] LIMIT n
    # Object reference (all fields + types):
    #   https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/sforce_api_objects_case.htm
    # Note: IsClosed is a formula boolean — true when Status = "Closed".
    # Actual status picklist values depend on org config; common defaults:
    #   New | Working | Escalated | Closed
    # CaseNumber is an auto-generated read-only field (e.g. "00001023").
    # ------------------------------------------------------------------

    async def get_cases(
        self,
        account_id: str | None = None,
        status: str | None = None,
        extra_fields: list[str] | None = None,
        filters: dict[str, str] | None = None,
        not_null_fields: list[str] | None = None,
        top: int = 25,
    ) -> list[SalesforceCase]:
        safe_extras, field_map = self._resolve_fields(extra_fields, _CASE_SELECTABLE)
        extra_cols = (", " + ", ".join(safe_extras)) if safe_extras else ""

        conditions: list[str] = []
        if account_id:
            conditions.append(f"AccountId = '{self._esc(account_id)}'")
        if status:
            conditions.append(f"Status LIKE '%{self._esc(status)}%'")
        self._apply_not_null(conditions, not_null_fields, _CASE_NOT_NULL)
        self._apply_filters(conditions, filters, _CASE_FILTERABLE, _CASE_NUMERIC, _CASE_BOOLEAN)

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        soql = (
            f"SELECT Id, CaseNumber, Subject, Status, Priority, Account.Name, CreatedDate{extra_cols} "
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
                    case_number=r.get("CaseNumber"),
                    subject=r["Subject"],
                    status=r["Status"],
                    priority=r.get("Priority"),
                    account_name=(r.get("Account") or {}).get("Name"),
                    created_date=created,
                    **{field_map[f]: r.get(f) for f in safe_extras},
                )
            )
        return result
