from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class SalesforceAccount:
    id: str
    name: str
    industry: str | None
    website: str | None


@dataclass
class SalesforceContact:
    id: str
    first_name: str | None
    last_name: str
    email: str | None
    account_name: str | None


@dataclass
class SalesforceOpportunity:
    id: str
    name: str
    stage: str
    amount: float | None
    close_date: datetime | None
    account_name: str | None


@dataclass
class SalesforceCase:
    id: str
    subject: str
    status: str
    priority: str | None
    account_name: str | None
    created_date: datetime | None


@dataclass
class SalesforceLead:
    id: str
    first_name: str | None
    last_name: str
    email: str | None
    company: str | None
    status: str | None
