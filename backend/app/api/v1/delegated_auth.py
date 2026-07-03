"""Per-environment delegated SSO popup login (Section 8a): the browser
opens `/start` in a popup window, the provider redirects back to
`/callback` after the root-credential user signs in, and the callback
stores an encrypted session on the EnvironmentConnection row, then closes
the popup via postMessage. One login per (environment, provider) - reused
across every tenant/account in that environment. This is what "Sync
Accounts" and NAVIXA Discover actually authenticate with in delegated
mode - never the backend host's own CLI session.
"""

import json
import time

import aioboto3
import msal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.auth.pkce_store import consume_state, create_state, generate_pkce_pair
from app.auth.token_encryption import encrypt
from app.collectors.azure.client import ARM_SCOPE, build_msal_app
from app.config.settings import get_settings
from app.database.session import get_db
from app.models.role import ADMIN
from app.models.user import User
from app.tenant_registry.connection_service import get_connection, get_or_create_connection

router = APIRouter(prefix="/connections", tags=["Delegated Auth"])
settings = get_settings()


def _callback_url(environment: str, provider: str) -> str:
    return (
        f"{settings.backend_public_base_url}{settings.api_v1_prefix}"
        f"/connections/{environment}/{provider}/delegated-auth/callback"
    )


def _popup_response(success: bool, message: str = "") -> HTMLResponse:
    payload = json.dumps({"type": "navixa-sso-complete", "success": success, "message": message})
    html = f"""
    <html><body>
    <script>
      window.opener && window.opener.postMessage({payload}, window.location.origin);
      window.close();
    </script>
    <p>{"Sign-in complete, you may close this window." if success else f"Sign-in failed: {message}"}</p>
    </body></html>
    """
    return HTMLResponse(html)


# --- Azure -----------------------------------------------------------------


@router.get("/{environment}/azure/delegated-auth/start")
async def start_azure_delegated_auth(
    environment: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ADMIN)),
):
    connection = get_or_create_connection(db, environment, "azure", created_by=current_user.id)
    redirect_uri = _callback_url(environment, "azure")

    verifier, challenge = generate_pkce_pair()
    state = await create_state(environment, "azure", verifier)

    app = build_msal_app(connection)
    auth_url = app.get_authorization_request_url(
        scopes=[ARM_SCOPE],
        state=state,
        redirect_uri=redirect_uri,
        code_challenge=challenge,
        code_challenge_method="S256",
    )
    return RedirectResponse(auth_url)


@router.get("/{environment}/azure/delegated-auth/callback")
async def azure_delegated_auth_callback(
    environment: str,
    code: str | None = None,
    state: str | None = None,
    error_description: str | None = Query(default=None, alias="error_description"),
    db: Session = Depends(get_db),
):
    if error_description or not code or not state:
        return _popup_response(False, error_description or "Missing authorization code")

    state_payload = await consume_state(state)
    if state_payload is None or state_payload.get("scope_key") != environment:
        return _popup_response(False, "Invalid or expired sign-in attempt")

    connection = get_connection(db, environment, "azure")
    if connection is None:
        return _popup_response(False, "Connection setup expired, please try again")

    redirect_uri = _callback_url(environment, "azure")

    cache = msal.SerializableTokenCache()
    app = build_msal_app(connection, cache=cache)
    result = app.acquire_token_by_authorization_code(
        code=code,
        scopes=[ARM_SCOPE],
        redirect_uri=redirect_uri,
        code_verifier=state_payload["code_verifier"],
    )
    if "access_token" not in result:
        return _popup_response(False, result.get("error_description", "Token exchange failed"))

    connection.delegated_token_cache = encrypt(cache.serialize())
    db.commit()
    return _popup_response(True)


# --- AWS -----------------------------------------------------------------


def _aws_identity_center_region(connection) -> str:
    return connection.region or settings.aws_default_region


async def _get_or_register_sso_client(connection, region: str, redirect_uri: str) -> dict:
    from app.collectors.aws.client import get_sso_session_dict

    existing = get_sso_session_dict(connection)
    if existing and existing.get("client_id") and existing.get("region") == region:
        if existing.get("client_secret_expires_at", 0) > time.time() + 60:
            return existing

    session = aioboto3.Session(region_name=region)
    async with session.client("sso-oidc", region_name=region) as client:
        response = await client.register_client(
            clientName="navixa-ai",
            clientType="public",
            grantTypes=["authorization_code", "refresh_token"],
            redirectUris=[redirect_uri],
        )
    return {
        "region": region,
        "client_id": response["clientId"],
        "client_secret": response["clientSecret"],
        "client_secret_expires_at": response["clientSecretExpiresAt"],
    }


@router.get("/{environment}/aws/delegated-auth/start")
async def start_aws_delegated_auth(
    environment: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ADMIN)),
):
    connection = get_or_create_connection(db, environment, "aws", created_by=current_user.id)
    if not connection.sso_login_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Set this connection's IAM Identity Center start URL first "
                "(PUT /connections/{environment}/aws)."
            ),
        )
    redirect_uri = _callback_url(environment, "aws")
    region = _aws_identity_center_region(connection)

    client_info = await _get_or_register_sso_client(connection, region, redirect_uri)
    connection.delegated_token_cache = encrypt(json.dumps(client_info))
    connection.region = region
    db.commit()

    verifier, challenge = generate_pkce_pair()
    state = await create_state(environment, "aws", verifier)

    authorize_url = (
        f"https://oidc.{region}.amazonaws.com/authorize"
        f"?response_type=code&client_id={client_info['client_id']}"
        f"&redirect_uri={redirect_uri}&state={state}"
        f"&code_challenge={challenge}&code_challenge_method=S256"
    )
    return RedirectResponse(authorize_url)


@router.get("/{environment}/aws/delegated-auth/callback")
async def aws_delegated_auth_callback(
    environment: str,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    if error or not code or not state:
        return _popup_response(False, error or "Missing authorization code")

    state_payload = await consume_state(state)
    if state_payload is None or state_payload.get("scope_key") != environment:
        return _popup_response(False, "Invalid or expired sign-in attempt")

    from app.collectors.aws.client import get_sso_session_dict

    connection = get_connection(db, environment, "aws")
    if connection is None:
        return _popup_response(False, "Connection setup expired, please try again")

    session = get_sso_session_dict(connection)
    if session is None:
        return _popup_response(False, "Sign-in session expired, please try again")

    redirect_uri = _callback_url(environment, "aws")
    aio_session = aioboto3.Session(region_name=session["region"])
    async with aio_session.client("sso-oidc", region_name=session["region"]) as client:
        try:
            response = await client.create_token(
                clientId=session["client_id"],
                clientSecret=session["client_secret"],
                grantType="authorization_code",
                code=code,
                redirectUri=redirect_uri,
                codeVerifier=state_payload["code_verifier"],
            )
        except Exception as exc:  # noqa: BLE001 - surfaced to the popup, not raised
            return _popup_response(False, str(exc))

    session["access_token"] = response["accessToken"]
    session["refresh_token"] = response.get("refreshToken")
    session["access_token_expires_at"] = int(time.time()) + int(response.get("expiresIn", 28800))
    connection.delegated_token_cache = encrypt(json.dumps(session))
    db.commit()
    return _popup_response(True)
