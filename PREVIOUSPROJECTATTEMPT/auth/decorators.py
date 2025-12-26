"""
Route decorators for authentication/authorization.

- `login_required`: user must be authenticated.
- `domain_required`: user must be authenticated and have an allowed email domain.
"""

from __future__ import annotations

from functools import wraps
from typing import Callable, TypeVar

from flask import current_app, redirect, request, session, url_for

from .config import AuthSettings
from .msal_auth import get_email_from_claims

F = TypeVar("F", bound=Callable[..., object])


def _auth_settings() -> AuthSettings:
    settings = current_app.config.get("AUTH_SETTINGS")
    if not isinstance(settings, AuthSettings):
        raise RuntimeError("Auth settings not initialized.")
    return settings


def login_required(fn: F) -> F:
    """Ensure the user is logged in; otherwise redirect to login."""

    @wraps(fn)
    def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
        if session.get("user"):
            return fn(*args, **kwargs)
        return redirect(url_for("auth.login", next=request.url))

    return wrapper  # type: ignore[return-value]


def domain_required(fn: F) -> F:
    """Ensure user is logged in and email ends with allowed domain."""

    @wraps(fn)
    def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
        user = session.get("user") or {}
        claims = user.get("claims") if isinstance(user, dict) else None
        email = get_email_from_claims(claims) if isinstance(claims, dict) else None

        if not email:
            # Treat missing email as unauthorized
            session.clear()
            return redirect(url_for("auth.login", next=request.url))

        allowed = _auth_settings().allowed_email_domain
        if email.lower().endswith("@" + allowed):
            return fn(*args, **kwargs)

        # Logged in, but not allowed
        session.clear()
        return (
            f"Unauthorized: your account '{email}' is not allowed. "
            f"Please sign in with an @{allowed} account.",
            403,
        )

    return wrapper  # type: ignore[return-value]


