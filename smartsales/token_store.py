"""SmartSales token persistence.

Provides:
  StoredTokens          – dataclass holding access/refresh tokens
  SmartSalesTokenStore  – ABC
  JsonFileTokenStore    – dev/local store backed by a JSON file
  build_token_store()   – factory that reads SS_TOKEN_STORE env var
"""

import asyncio
import json
import os
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


# ──────────────────────────────────────────────────────────────────────────────
# StoredTokens
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class StoredTokens:
    """All persisted credentials for a single SmartSales session."""
    access_token: str
    refresh_token: str
    expires_at: float  # Unix epoch seconds

    def is_expired(self, buffer_seconds: int = 300) -> bool:
        """True if the access token expires within *buffer_seconds*."""
        return time.time() >= (self.expires_at - buffer_seconds)


# ──────────────────────────────────────────────────────────────────────────────
# Abstract base
# ──────────────────────────────────────────────────────────────────────────────

class SmartSalesTokenStore(ABC):
    @abstractmethod
    async def get(self, session_token: str) -> Optional[StoredTokens]:
        """Return stored tokens for *session_token*, or None if not found."""

    @abstractmethod
    async def save(self, session_token: str, tokens: StoredTokens) -> None:
        """Persist *tokens* under *session_token*."""

    @abstractmethod
    async def delete(self, session_token: str) -> None:
        """Remove the entry for *session_token* (no-op if not found)."""

    def generate_session_token(self) -> str:
        return str(uuid.uuid4())


# ──────────────────────────────────────────────────────────────────────────────
# JSON file store (dev / local)
# ──────────────────────────────────────────────────────────────────────────────

class JsonFileTokenStore(SmartSalesTokenStore):
    """Stores tokens as JSON in a local file."""

    def __init__(self, path: str = ".smartsales_tokens.json") -> None:
        self._path = Path(path)
        self._lock = asyncio.Lock()

    def _read_raw(self) -> dict:
        if not self._path.exists():
            return {}
        return json.loads(self._path.read_text(encoding="utf-8"))

    def _write_raw(self, data: dict) -> None:
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    async def get(self, session_token: str) -> Optional[StoredTokens]:
        async with self._lock:
            entry = self._read_raw().get(session_token)
        if entry is None:
            return None
        return StoredTokens(**entry)

    async def save(self, session_token: str, tokens: StoredTokens) -> None:
        async with self._lock:
            data = self._read_raw()
            data[session_token] = asdict(tokens)
            self._write_raw(data)

    async def delete(self, session_token: str) -> None:
        async with self._lock:
            data = self._read_raw()
            data.pop(session_token, None)
            self._write_raw(data)


# ──────────────────────────────────────────────────────────────────────────────
# Factory
# ──────────────────────────────────────────────────────────────────────────────

def build_token_store() -> SmartSalesTokenStore:
    """Return the right token store based on the ``SS_TOKEN_STORE`` env var.

    Values:
      ``"file"`` – JsonFileTokenStore (default)
    """
    path = os.environ.get("SS_TOKEN_STORE_FILE", ".smartsales_tokens.json")
    return JsonFileTokenStore(path=path)
