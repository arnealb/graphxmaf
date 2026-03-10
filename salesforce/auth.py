"""Salesforce OAuth 2.0 authentication helpers.

Supports two flows (mirrored from simple-salesforce login.py, no dependency):
  - Password Grant  – client_id + client_secret + username + password
  - JWT Bearer      – client_id + RSA private key  (works with MFA)

Call `authenticate_password()` or `authenticate_jwt()` directly, or let
`authenticate_from_env()` pick the right flow from environment variables.
"""

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
import jwt as _jwt  # PyJWT[cryptography]

log = logging.getLogger("salesforce.auth")

# ──────────────────────────────────────────────────────────────────────────────
# Public types
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class SalesforceCredentials:
    """Successful Salesforce auth result."""
    access_token: str
    instance_url: str


class SalesforceAuthError(RuntimeError):
    """Raised for any Salesforce authentication failure."""


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _post_token(login_url: str, data: dict) -> SalesforceCredentials:
    """POST to the Salesforce token endpoint and parse the response."""
    url = f"{login_url.rstrip('/')}/services/oauth2/token"
    log.debug("Token request  url=%s  grant_type=%s", url, data.get("grant_type"))

    resp = httpx.post(url, data=data, timeout=30)

    if not resp.is_success:
        # Always include the JSON error_description when Salesforce provides it.
        try:
            body = resp.json()
            code = body.get("error", resp.status_code)
            msg = body.get("error_description", resp.text)
        except Exception:
            code, msg = resp.status_code, resp.text
        raise SalesforceAuthError(f"Salesforce auth failed [{code}]: {msg}")

    result = resp.json()
    creds = SalesforceCredentials(
        access_token=result["access_token"],
        instance_url=result["instance_url"],
    )
    log.info("Salesforce auth OK  instance_url=%s", creds.instance_url)
    return creds


# ──────────────────────────────────────────────────────────────────────────────
# Public auth functions
# ──────────────────────────────────────────────────────────────────────────────



def authenticate_jwt(
    *,
    client_id: str,
    username: str,
    private_key: str | None = None,
    private_key_path: str | None = None,
    login_url: str = "https://test.salesforce.com",
) -> SalesforceCredentials:
    """OAuth 2.0 JWT Bearer Token Flow.

    Requires a Connected App with a digital certificate uploaded and the user
    pre-authorised in the Connected App policies.  Works even when MFA is
    enforced because no interactive login takes place.

    Provide exactly one of:
      ``private_key``       – PEM string (e.g. read from env var SF_PRIVATE_KEY)
      ``private_key_path``  – path to a .pem file   (env var SF_PRIVATE_KEY_PATH)

    JWT claims follow simple-salesforce conventions:
      iss = client_id (consumer key)
      sub = username
      aud = login_url  (https://test.salesforce.com or https://login.salesforce.com)
      exp = now + 3 min  (Salesforce maximum)
    """
    if private_key is None and private_key_path is None:
        raise ValueError("Provide either private_key or private_key_path")

    key: str = (
        private_key
        if private_key is not None
        else Path(private_key_path).read_text(encoding="utf-8")  # type: ignore[arg-type]
    )

    log.info("Salesforce JWT bearer  user=%s  login_url=%s", username, login_url)

    payload = {
        "iss": client_id,
        "sub": username,
        "aud": login_url.rstrip("/"),
        "exp": int(time.time()) + 180,  # 3 minutes — Salesforce maximum
    }
    assertion = _jwt.encode(payload, key, algorithm="RS256")

    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": assertion,
    }
    return _post_token(login_url, data)


# ──────────────────────────────────────────────────────────────────────────────
# Convenience: pick flow from environment
# ──────────────────────────────────────────────────────────────────────────────

def authenticate_salesforce(login_url: str) -> SalesforceCredentials:
    client_id = _require_env("SF_CLIENT_ID")
    username = _require_env("SF_USERNAME")

    private_key_path = os.environ.get("SF_PRIVATE_KEY_PATH")
    private_key = os.environ.get("SF_PRIVATE_KEY")

    # use_jwt = has_jwt_key and forced_flow != "password"

    return authenticate_jwt(
        client_id=client_id,
        username=username,
        private_key=private_key,
        private_key_path=private_key_path,
        login_url=login_url,
    )




def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SalesforceAuthError(f"Required environment variable {name!r} is not set")
    return value
