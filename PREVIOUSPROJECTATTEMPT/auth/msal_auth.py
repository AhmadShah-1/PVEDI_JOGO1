"""
MSAL helpers.

This wraps MSAL (Microsoft Authentication Library) setup for Entra ID
authentication. We use the OAuth2 Authorization Code Flow.
"""

from __future__ import annotations

import secrets
from typing import Any

import msal
from flask import Flask, current_app

from .config import AuthSettings


def _settings(app: Flask | None = None) -> AuthSettings:
    app = app or current_app  # type: ignore[assignment]
    settings = app.config.get("AUTH_SETTINGS")
    if not isinstance(settings, AuthSettings):
        raise RuntimeError("Auth settings not initialized. Call auth.config.init_auth(app) during app startup.")
    return settings


def build_msal_app(app: Flask | None = None) -> msal.ConfidentialClientApplication:
    """Create an MSAL confidential client app."""

    s = _settings(app)
    return msal.ConfidentialClientApplication(
        client_id=s.client_id,
        client_credential=s.client_secret,
        authority=s.authority,
    )


def new_state_token() -> str:
    """Generate a cryptographically secure state token for CSRF protection."""

    return secrets.token_urlsafe(32)


def get_email_from_claims(claims: dict[str, Any] | None) -> str | None:
    """
    Extract an email/UPN-like identifier from ID token claims.

    Entra ID commonly uses:
      - preferred_username (often UPN/email)
      - email
      - upn
    """

    if not claims:
        return None
    for key in ("preferred_username", "email", "upn"):
        val = claims.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


