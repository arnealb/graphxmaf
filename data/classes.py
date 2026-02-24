from dataclasses import dataclass
from datetime import datetime

@dataclass
class Email:
    id: str
    subject: str
    sender: str
    received: datetime