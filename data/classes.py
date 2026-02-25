from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional, List

@dataclass
class Email:
    id: str
    subject: str
    sender_name: str
    sender_email: str | None
    received: datetime
    body: str | None = None
    web_link: str | None = None


@dataclass
class File:
    id: str
    name: str
    is_folder: bool
    size: int | None
    created: datetime | None
    modified: datetime | None
    parent_id: str | None
    web_link: str | None

@dataclass
class Contact:
    id: str
    name: str
    email: str | None


# kan zijn dat calendar shit niet zelfde is als contacten dus best andere zeker?
@dataclass
class CalendarEvent:
    id: str
    subject: str
    start: datetime | None
    end: datetime | None
    organizer: EmailAddress | None
    attendees: list[Attendee]

@dataclass
class EmailAddress:
    name: str | None
    address: str | None

@dataclass
class Attendee:
    email: EmailAddress



# ---------------------------------------------------------------------
EntityType = Literal["email", "file", "event", "contact"]


@dataclass
class SearchResult:
    type: EntityType
    id: str
    title: Optional[str]
    snippet: Optional[str]
    timestamp: Optional[datetime]
    people: List[EmailAddress]
    web_link: Optional[str]
    source: str = "graph"
