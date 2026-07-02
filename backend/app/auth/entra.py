"""Entra ID OIDC/OAuth2 authorization code flow (Section 6, Phase 5).

MFA is enforced upstream by Entra Conditional Access policies configured
on the tenant, not by this application - there is no in-app MFA step.
This module only implements the authorization code exchange; it cannot be
exercised end-to-end without a real Entra tenant/app registration, so it
is unit-tested only at the "is this configured / does URL building work"
level, not against a live IdP.
"""

import msal

from app.config.settings import get_settings

settings = get_settings()

_AUTHORITY_TEMPLATE = "https://login.microsoftonline.com/{tenant_id}"
_SCOPES = ["User.Read"]


def is_entra_configured() -> bool:
    return bool(settings.entra_tenant_id and settings.entra_client_id and settings.entra_client_secret)


def _get_msal_app() -> msal.ConfidentialClientApplication:
    return msal.ConfidentialClientApplication(
        client_id=settings.entra_client_id,
        client_credential=settings.entra_client_secret,
        authority=_AUTHORITY_TEMPLATE.format(tenant_id=settings.entra_tenant_id),
    )


def get_authorization_url(state: str) -> str:
    app = _get_msal_app()
    return app.get_authorization_request_url(
        scopes=_SCOPES,
        state=state,
        redirect_uri=settings.entra_redirect_uri,
    )


def acquire_token_by_authorization_code(code: str) -> dict:
    """Returns the MSAL token response, including `id_token_claims` on
    success or an `error`/`error_description` pair on failure."""
    app = _get_msal_app()
    return app.acquire_token_by_authorization_code(
        code=code,
        scopes=_SCOPES,
        redirect_uri=settings.entra_redirect_uri,
    )
