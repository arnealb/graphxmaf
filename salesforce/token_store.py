# token_store.py
"""Per-user Salesforce token persistence.

Provides:
  StoredTokens          – dataclass holding all per-user SF credentials
  SalesforceTokenStore  – ABC
  JsonFileTokenStore    – dev/local store backed by a JSON file
  AzureKeyVaultTokenStore – prod store backed by Azure Key Vault
  build_token_store()   – factory that reads SF_TOKEN_STORE env var
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
    """All persisted OAuth 2.0 credentials for a single user session."""
    access_token: str
    refresh_token: str
    instance_url: str
    expires_at: float       # Unix epoch seconds
    user_id: str = ""       # Salesforce user/org URL returned by /id endpoint
    username: str = ""      # last path segment of user_id URL

    def is_expired(self, buffer_seconds: int = 300) -> bool:
        """True if the access token expires within *buffer_seconds*."""
        return time.time() >= (self.expires_at - buffer_seconds)

    @classmethod
    def from_token_response(cls, data: dict) -> "StoredTokens":
        """Build from a raw Salesforce token endpoint JSON response.

        Salesforce returns ``issued_at`` as epoch milliseconds (string).
        ``expires_in`` is not always present; default to 7200 s (2 h).
        """
        issued_at_raw = data.get("issued_at")
        if issued_at_raw:
            issued_at = float(issued_at_raw) / 1000.0
        else:
            issued_at = time.time()

        expires_in = float(data.get("expires_in", 7200))
        expires_at = issued_at + expires_in

        user_id_url = data.get("id", "")
        username = user_id_url.split("/")[-1] if user_id_url else ""

        return cls(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", ""),
            instance_url=data["instance_url"],
            expires_at=expires_at,
            user_id=user_id_url,
            username=username,
        )


# ──────────────────────────────────────────────────────────────────────────────
# Abstract base
# ──────────────────────────────────────────────────────────────────────────────

class SalesforceTokenStore(ABC):
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

class JsonFileTokenStore(SalesforceTokenStore):
    """Stores tokens as JSON in a local file.

    Optional Fernet symmetric encryption when *SF_TOKEN_STORE_ENCRYPTION_KEY*
    is set (must be a URL-safe base64 32-byte key as produced by
    ``Fernet.generate_key()``).
    """

    def __init__(
        self,
        path: str = ".salesforce_tokens.json",
        encryption_key: Optional[str] = None,
    ) -> None:
        self._path = Path(path)
        self._lock = asyncio.Lock()
        self._fernet = None
        if encryption_key:
            try:
                from cryptography.fernet import Fernet
                self._fernet = Fernet(encryption_key.encode())
            except ImportError:
                pass  # cryptography not installed; store plain text

    # ── internal helpers ──────────────────────────────────────────────────────

    def _read_raw(self) -> dict:
        if not self._path.exists():
            return {}
        return json.loads(self._path.read_text(encoding="utf-8"))

    def _write_raw(self, data: dict) -> None:
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # ── SalesforceTokenStore interface ────────────────────────────────────────

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
# Azure Key Vault store (production)
# ──────────────────────────────────────────────────────────────────────────────

class AzureKeyVaultTokenStore(SalesforceTokenStore):
    """Stores tokens as JSON secrets in Azure Key Vault.

    Secret names follow the pattern ``sf-session-<uuid>``.
    Uses ``azure.identity.aio.DefaultAzureCredential`` for auth.
    """

    def __init__(self, vault_url: str) -> None:
        self._vault_url = vault_url
        self._client = None

    def _get_client(self):
        if self._client is None:
            from azure.identity.aio import DefaultAzureCredential
            from azure.keyvault.secrets.aio import SecretClient
            self._client = SecretClient(
                vault_url=self._vault_url,
                credential=DefaultAzureCredential(),
            )
        return self._client

    @staticmethod
    def _secret_name(session_token: str) -> str:
        return f"sf-session-{session_token}"

    async def get(self, session_token: str) -> Optional[StoredTokens]:
        client = self._get_client()
        try:
            secret = await client.get_secret(self._secret_name(session_token))
            return StoredTokens(**json.loads(secret.value))
        except Exception:
            return None

    async def save(self, session_token: str, tokens: StoredTokens) -> None:
        client = self._get_client()
        await client.set_secret(
            self._secret_name(session_token),
            json.dumps(asdict(tokens)),
        )

    async def delete(self, session_token: str) -> None:
        client = self._get_client()
        try:
            await client.begin_delete_secret(self._secret_name(session_token))
        except Exception:
            pass


# ──────────────────────────────────────────────────────────────────────────────
# Factory
# ──────────────────────────────────────────────────────────────────────────────

def build_token_store() -> SalesforceTokenStore:
    """Return the right token store based on the ``SF_TOKEN_STORE`` env var.

    Values:
      ``"file"``           – JsonFileTokenStore  (default)
      ``"azure_keyvault"`` – AzureKeyVaultTokenStore
    """
    store_type = os.environ.get("SF_TOKEN_STORE", "file")
    if store_type == "azure_keyvault":
        vault_url = os.environ.get("SF_KEY_VAULT_URL", "")
        return AzureKeyVaultTokenStore(vault_url=vault_url)

    path = os.environ.get("SF_TOKEN_STORE_FILE", ".salesforce_tokens.json")
    encryption_key = os.environ.get("SF_TOKEN_STORE_ENCRYPTION_KEY")
    return JsonFileTokenStore(path=path, encryption_key=encryption_key)
