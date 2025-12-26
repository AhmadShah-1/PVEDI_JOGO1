"""
Auth routes (MSAL / Entra ID).

Endpoints:
  - GET  /auth/login
  - GET  /auth/callback
  - GET  /auth/logout

Implementation notes:
  - Uses MSAL Authorization Code Flow.
  - Stores a minimal user profile in the server-side session.
  - Enforces an allowed email domain immediately after callback.
"""

from __future__ import annotations

from urllib.parse import urlencode

from flask import Blueprint, current_app, redirect, request, session, url_for

from .config import AuthSettings
from .msal_auth import build_msal_app, get_email_from_claims, new_state_token

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _settings() -> AuthSettings:
    settings = current_app.config.get("AUTH_SETTINGS")
    if not isinstance(settings, AuthSettings):
        raise RuntimeError("Auth settings not initialized. Call auth.config.init_auth(app) at startup.")
    return settings


@auth_bp.get("/login")
def login():
    """
    Start the login flow by redirecting the user to Microsoft.

    Optional query param:
      - next: where to redirect after successful login
    """

    s = _settings()
    msal_app = build_msal_app()

    state = new_state_token()
    session["auth_state"] = state
    session["post_login_redirect"] = request.args.get("next") or url_for("index")

    redirect_uri = url_for("auth.callback", _external=True)
    auth_url = msal_app.get_authorization_request_url(
        scopes=s.scopes,
        state=state,
        redirect_uri=redirect_uri,
        prompt="select_account",
    )
    return redirect(auth_url)


@auth_bp.get("/callback")
def callback():
    """Handle the OAuth2 redirect from Microsoft and create a local session."""

    # CSRF check
    expected_state = session.get("auth_state")
    received_state = request.args.get("state")
    if not expected_state or expected_state != received_state:
        session.clear()
        return "Authentication failed (invalid state). Please try again.", 400

    code = request.args.get("code")
    if not code:
        # Azure sends error params when login fails/cancelled.
        error = request.args.get("error")
        desc = request.args.get("error_description")
        session.clear()
        return f"Authentication failed: {error or 'unknown_error'}\n\n{desc or ''}", 400

    s = _settings()
    msal_app = build_msal_app()
    redirect_uri = url_for("auth.callback", _external=True)

    result = msal_app.acquire_token_by_authorization_code(
        code=code,
        scopes=s.scopes,
        redirect_uri=redirect_uri,
    )

    if not isinstance(result, dict) or "error" in result:
        session.clear()
        return f"Authentication failed: {result.get('error')} - {result.get('error_description')}", 400

    claims = result.get("id_token_claims") or {}
    email = get_email_from_claims(claims)
    if not email:
        session.clear()
        return "Authentication failed: no email claim returned by identity provider.", 400

    allowed = s.allowed_email_domain
    if not email.lower().endswith("@" + allowed):
        # Deny and force sign-out from our app session (user can still be signed into Microsoft).
        session.clear()
        return (
            f"Unauthorized: your account '{email}' is not allowed. "
            f"Please sign in with an @{allowed} account.",
            403,
        )

    session["user"] = {
        "name": claims.get("name") or email,
        "email": email,
        # Store claims for debugging / future use. Keep minimal; do not store access tokens in session.
        "claims": claims,
    }
    session.pop("auth_state", None)

    next_url = session.pop("post_login_redirect", None) or url_for("index")
    return redirect(next_url)


@auth_bp.get("/logout")
def logout():
    """
    Clear the local session and redirect to Microsoft logout.

    This ensures users are fully signed out from Entra ID when desired.
    """

    s = _settings()
    session.clear()

    post_logout_redirect = url_for("index", _external=True)
    logout_url = f"{s.authority}/oauth2/v2.0/logout?{urlencode({'post_logout_redirect_uri': post_logout_redirect})}"
    return redirect(logout_url)


