"""
Authentication configuration.

All secrets are sourced from environment variables (recommended for Azure App
Service). This module validates presence of required settings and exposes a
single `init_auth(app)` entrypoint.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from flask import Flask


@dataclass(frozen=True)
class AuthSettings:
    """Configuration needed for Entra ID / MSAL auth."""

    tenant_id: str
    client_id: str
    client_secret: str
    allowed_email_domain: str
    scopes: list[str]

    @property
    def authority(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}"


def load_auth_settings() -> AuthSettings:
    """
    Load auth settings from environment variables.

    Required:
      - AAD_TENANT_ID
      - AAD_CLIENT_ID
      - AAD_CLIENT_SECRET

    Optional:
      - AAD_ALLOWED_EMAIL_DOMAIN (default: pvedi-ae.com)
      - AAD_SCOPES (default: 'openid profile email')
    """

    tenant_id = os.environ.get("AAD_TENANT_ID", "").strip()
    client_id = os.environ.get("AAD_CLIENT_ID", "").strip()
    client_secret = os.environ.get("AAD_CLIENT_SECRET", "").strip()

    missing = [k for k, v in [("AAD_TENANT_ID", tenant_id), ("AAD_CLIENT_ID", client_id), ("AAD_CLIENT_SECRET", client_secret)] if not v]
    if missing:
        raise RuntimeError(
            "Missing required auth environment variables: "
            + ", ".join(missing)
            + ". Set them in Azure App Service Configuration (or your local env) before starting the app."
        )

    allowed_email_domain = os.environ.get("AAD_ALLOWED_EMAIL_DOMAIN", "pvedi-ae.com").strip().lower()

    scopes_raw = os.environ.get("AAD_SCOPES", "openid profile email").strip()
    scopes = [s for s in scopes_raw.split() if s]

    return AuthSettings(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
        allowed_email_domain=allowed_email_domain,
        scopes=scopes,
    )


def init_auth(app: Flask) -> AuthSettings:
    """
    Validate and attach auth settings to Flask `app.config`.

    Returns the parsed `AuthSettings` for convenience.
    """

    settings = load_auth_settings()
    app.config["AUTH_SETTINGS"] = settings
    return settings


