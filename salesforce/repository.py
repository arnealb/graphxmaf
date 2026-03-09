from salesforce.models import SalesforceAccount, SalesforceContact, SalesforceOpportunity, SalesforceCase


class SalesforceRepository:
    def __init__(self, access_token: str, instance_url: str):
        self.access_token = access_token
        self.instance_url = instance_url

    async def get_accounts(self, query: str | None = None, top: int = 25) -> list[SalesforceAccount]:
        raise NotImplementedError

    async def get_contact(self, contact_id: str) -> SalesforceContact | None:
        raise NotImplementedError

    async def find_contacts(self, query: str, top: int = 10) -> list[SalesforceContact]:
        raise NotImplementedError

    async def get_opportunities(self, account_id: str | None = None, stage: str | None = None, top: int = 25) -> list[SalesforceOpportunity]:
        raise NotImplementedError

    async def get_cases(self, account_id: str | None = None, status: str | None = None, top: int = 25) -> list[SalesforceCase]:
        raise NotImplementedError
