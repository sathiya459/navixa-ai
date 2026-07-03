"""Azure credential broker and async client factory for NAVIXA Discover
(Section 8 / 8a).

Two real modes, selected by `settings.cloud_auth_mode`:
- "delegated": uses the environment's own root-credential SSO session,
  captured via the OAuth 2.0 Device Authorization Grant (RFC 8628) in
  app/api/v1/delegated_auth.py and stored, encrypted, on
  `EnvironmentConnection.delegated_token_cache` - one login per
  (environment, provider), reused across every tenant in that
  environment, never the backend host's own `az login`. If there's no
  valid cached session, raises DelegatedAuthRequiredError.

  This authenticates as Microsoft's own well-known Azure CLI public
  client (04b07795-...) rather than NAVIXA's own app registration:
  NAVIXA's registration only declares Microsoft Graph permission (it's
  for logging into NAVIXA itself) and requesting the Azure Resource
  Manager resource through it fails with AADSTS650057. The Azure CLI
  client is pre-consented for ARM access in effectively every tenant -
  the same one `az login` itself uses - so this resolves the same
  tenants/subscriptions a user's own `az login` would. A device-code flow
  (not an authorization-code + redirect popup) is used deliberately:
  Azure CLI's app registration only accepts its own pre-registered
  loopback redirect URIs, which a real backend callback can't match
  (AADSTS50011) - device code has no redirect URI at all.
- "app_only": a real Entra ID client-credentials (ClientSecretCredential)
  exchange when `azure_federation_*` settings are configured - the
  platform authenticates as its own registered Entra app, which must be
  granted Reader (or equivalent) access on each target subscription.

Falls back to the Phase 2 stub when app_only isn't configured, so local
dev without a real Azure tenant keeps working unchanged.
"""

import json
import time

import httpx
from azure.core.credentials import AccessToken
from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import ClientSecretCredential
from azure.mgmt.network.aio import NetworkManagementClient
from azure.mgmt.subscription.aio import SubscriptionClient

from app.auth.token_encryption import decrypt, encrypt
from app.collectors.delegated_auth_errors import DelegatedAuthRequiredError
from app.config.settings import get_settings
from app.models.environment_connection import EnvironmentConnection

settings = get_settings()

ARM_SCOPE = "https://management.azure.com/.default"
DEVICE_FLOW_SCOPE = f"{ARM_SCOPE} offline_access"

# See module docstring for why this specific client ID is used instead of
# NAVIXA's own app registration.
AZURE_CLI_CLIENT_ID = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"


class StubAsyncCredential(AsyncTokenCredential):
    """Used only when neither delegated nor app-only Azure auth is configured."""

    async def get_token(self, *scopes: str, **kwargs) -> AccessToken:
        return AccessToken("stub-access-token", 9999999999)

    async def close(self) -> None:
        return None


def is_azure_federation_configured() -> bool:
    return bool(
        settings.azure_federation_tenant_id
        and settings.azure_federation_client_id
        and settings.azure_federation_client_secret
    )


def connection_tenant_id(connection: EnvironmentConnection) -> str:
    extra = connection.extra_config or {}
    return extra.get("app_registration_tenant_id") or settings.entra_tenant_id


def _token_endpoint(tenant_id: str) -> str:
    return f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"


def _devicecode_endpoint(tenant_id: str) -> str:
    return f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/devicecode"


async def start_device_flow(connection: EnvironmentConnection) -> dict:
    """Kicks off RFC 8628 device authorization - returns Azure AD's raw
    response (device_code, user_code, verification_uri, expires_in,
    interval, message)."""
    tenant_id = connection_tenant_id(connection)
    async with httpx.AsyncClient() as client:
        response = await client.post(
            _devicecode_endpoint(tenant_id),
            data={"client_id": AZURE_CLI_CLIENT_ID, "scope": DEVICE_FLOW_SCOPE},
        )
    response.raise_for_status()
    data = response.json()
    data["tenant_id"] = tenant_id
    return data


async def poll_device_flow(tenant_id: str, device_code: str) -> dict:
    """One poll attempt - returns Azure AD's raw token-endpoint response,
    which is either an error (`error: authorization_pending|slow_down|
    expired_token|access_denied`) or a real token payload."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            _token_endpoint(tenant_id),
            data={
                "client_id": AZURE_CLI_CLIENT_ID,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": device_code,
            },
        )
    return response.json()


def get_azure_session_dict(connection: EnvironmentConnection | None) -> dict | None:
    if connection is None or not connection.delegated_token_cache:
        return None
    return json.loads(decrypt(connection.delegated_token_cache))


def persist_azure_session(connection: EnvironmentConnection, session: dict) -> None:
    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        row = db.get(EnvironmentConnection, connection.id)
        if row is not None:
            row.delegated_token_cache = encrypt(json.dumps(session))
            db.commit()
    finally:
        db.close()


async def _refresh_azure_session(connection: EnvironmentConnection, session: dict) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            _token_endpoint(session["tenant_id"]),
            data={
                "client_id": AZURE_CLI_CLIENT_ID,
                "grant_type": "refresh_token",
                "refresh_token": session["refresh_token"],
                "scope": DEVICE_FLOW_SCOPE,
            },
        )
    data = response.json()
    if "access_token" not in data:
        raise DelegatedAuthRequiredError(connection.environment, "azure")

    session["access_token"] = data["access_token"]
    session["refresh_token"] = data.get("refresh_token", session["refresh_token"])
    session["access_token_expires_at"] = int(time.time()) + int(data.get("expires_in", 3600))
    persist_azure_session(connection, session)
    return session


async def get_valid_azure_session(connection: EnvironmentConnection | None) -> dict:
    """Returns a session dict with a non-expired access_token, refreshing
    via the stored refresh_token if needed. Raises
    DelegatedAuthRequiredError if there's no session, or the refresh token
    itself has expired/been revoked (requires a fresh device-flow login)."""
    if connection is None:
        raise DelegatedAuthRequiredError("unknown", "azure")

    session = get_azure_session_dict(connection)
    if session is None:
        raise DelegatedAuthRequiredError(connection.environment, "azure")

    if int(time.time()) < session["access_token_expires_at"] - 60:
        return session

    try:
        return await _refresh_azure_session(connection, session)
    except DelegatedAuthRequiredError:
        raise
    except Exception as exc:
        raise DelegatedAuthRequiredError(connection.environment, "azure") from exc


class DelegatedAzureCredential(AsyncTokenCredential):
    """Wraps the environment connection's stored device-flow session."""

    def __init__(self, connection: EnvironmentConnection | None):
        self._connection = connection

    async def get_token(self, *scopes: str, **kwargs) -> AccessToken:
        session = await get_valid_azure_session(self._connection)
        return AccessToken(session["access_token"], session["access_token_expires_at"])

    async def close(self) -> None:
        return None


def get_scoped_credential(connection: EnvironmentConnection | None) -> AsyncTokenCredential:
    if settings.cloud_auth_mode == "delegated":
        return DelegatedAzureCredential(connection)

    if not is_azure_federation_configured():
        return StubAsyncCredential()

    return ClientSecretCredential(
        tenant_id=settings.azure_federation_tenant_id,
        client_id=settings.azure_federation_client_id,
        client_secret=settings.azure_federation_client_secret,
    )


def get_network_client(
    credential: AsyncTokenCredential, subscription_id: str
) -> NetworkManagementClient:
    return NetworkManagementClient(credential, subscription_id)


def get_subscription_client(credential: AsyncTokenCredential) -> SubscriptionClient:
    return SubscriptionClient(credential)
