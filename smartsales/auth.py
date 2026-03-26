"""SmartSales authentication helpers.

Token endpoint: POST https://proxy-smartsales.easi.net/proxy/rest/auth/v3/token
Required env vars: GRANT_TYPE, CODE_SMARTSALES, CLIENT_ID_SMARTSALES, CLIENT_SECRET_SMARTSALES
Response: { token_type, scope, expires_in, access_token, refresh_token }
"""

import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

import httpx

log = logging.getLogger("smartsales.auth")

_TOKEN_URL = "https://proxy-smartsales.easi.net/proxy/rest/auth/v3/token"


# ──────────────────────────────────────────────────────────────────────────────
# Public types
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class SmartSalesCredentials:
    """Successful SmartSales auth result."""
    access_token: str
    refresh_token: str
    expires_at: float  # Unix epoch seconds


class SmartSalesAuthError(RuntimeError):
    """Raised for any SmartSales authentication failure."""


# ──────────────────────────────────────────────────────────────────────────────
# Public auth functions
# ──────────────────────────────────────────────────────────────────────────────

def authenticate_smartsales(
    *,
    grant_type: str,
    code: str,
    client_id: str,
    client_secret: str,
) -> SmartSalesCredentials:
    """Obtain a SmartSales access token using the provided credentials."""
    data = {
        "grant_type": grant_type,
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    log.info(
        "SmartSales auth request  grant_type=%s  client_id=%s",
        grant_type,
        client_id[:4] + "…" if len(client_id) > 4 else client_id,
    )

    resp = httpx.post(_TOKEN_URL, data=data, timeout=30)

    if not resp.is_success:
        try:
            body = resp.json()
            msg = body.get("error_description") or body.get("error") or resp.text
        except Exception:
            msg = resp.text
        raise SmartSalesAuthError(f"SmartSales auth failed [{resp.status_code}]: {msg}")

    result = resp.json()
    expires_in = float(result.get("expires_in", 3600))
    creds = SmartSalesCredentials(
        access_token=result["access_token"],
        refresh_token=result.get("refresh_token", ""),
        expires_at=time.time() + expires_in,
    )
    log.info("SmartSales auth OK  expires_in=%ss", int(expires_in))
    return creds


def authenticate_from_env() -> SmartSalesCredentials:
    """Read credentials from environment variables and authenticate."""
    return authenticate_smartsales(
        grant_type=_require_env("GRANT_TYPE"),
        code=_require_env("CODE_SMARTSALES"),
        client_id=_require_env("CLIENT_ID_SMARTSALES"),
        client_secret=_require_env("CLIENT_SECRET_SMARTSALES"),
    )


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SmartSalesAuthError(f"Required environment variable {name!r} is not set")
    return value
