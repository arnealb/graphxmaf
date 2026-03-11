from datetime import datetime
from typing import Literal, Optional, List
from pydantic import BaseModel


class EmailAddress(BaseModel):
    name: str | None
    address: str | None


class Attendee(BaseModel):
    email: EmailAddress


class Email(BaseModel):
    id: str
    subject: str
    sender_name: str
    sender_email: str | None
    received: datetime
    body: str | None = None
    web_link: str | None = None


class File(BaseModel):
    id: str
    name: str
    is_folder: bool
    size: int | None
    created: datetime | None
    modified: datetime | None
    parent_id: str | None
    web_link: str | None


class Contact(BaseModel):
    id: str
    name: str
    email: str | None


class CalendarEvent(BaseModel):
    id: str
    subject: str
    start: str | None
    end: str | None
    organizer: EmailAddress | None
    attendees: list[Attendee]
    web_link: str | None


# ---------------------------------------------------------------------
EntityType = Literal["email", "file", "event", "contact"]


class SearchResult(BaseModel):
    type: EntityType
    id: str
    title: Optional[str]
    snippet: Optional[str]
    timestamp: Optional[datetime]
    people: List[EmailAddress]
    web_link: Optional[str]
    source: str = "graph"


class User(BaseModel):
    display_name: str | None
    email: str | None
