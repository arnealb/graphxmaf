from dataclasses import dataclass
from datetime import datetime

@dataclass
class Email:
    id: str
    subject: str
    sender_name: str
    sender_email: str | None
    received: datetime
    body: str | None = None
    web_link: str | None = None