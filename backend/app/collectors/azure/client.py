"""Azure credential broker and async client factory for NAVIXA Discover
(Section 8 / 8a).

Two real modes, selected by `settings.cloud_auth_mode`:
- "delegated": uses the environment's own root-credential SSO session (an
  MSAL token cache captured by the OAuth2 authorization code + PKCE flow
  in app/api/v1/delegated_auth.py and stored, encrypted, on
  `EnvironmentConnection.delegated_token_cache`) - one popup login per
  (environment, provider), reused across every tenant in that
  environment, never the backend host's own `az login`. If there's no
  valid cached session, raises DelegatedAuthRequiredError so the caller
  can prompt the popup.
- "app_only": a real Entra ID client-credentials (ClientSecretCredential)
  exchange when `azure_federation_*` settings are configured - the
  platform authenticates as its own registered Entra app, which must be
  granted Reader (or equivalent) access on each target subscription.

Falls back to the Phase 2 stub when app_only isn't configured, so local
dev without a real Azure tenant keeps working unchanged.
"""

import asyncio
import time

import msal
from azure.core.credentials import AccessToken
from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import ClientSecretCredential
from azure.mgmt.network.aio import NetworkManagementClient
from azure.mgmt.subscription.aio import SubscriptionClient

from app.auth.token_encryption import decrypt, encrypt
from app.collectors.delegated_auth_errors import DelegatedAuthRequiredError
from app.config.secrets import SecretProviderError, get_secret_provider
from app.config.settings import get_settings
from app.models.environment_connection import EnvironmentConnection

settings = get_settings()

ARM_SCOPE = "https://management.azure.com/.default"


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


def get_connection_client_secret(connection: EnvironmentConnection) -> str | None:
    """An environment connection may register its own Entra app (optional,
    advanced path) with its secret in Key Vault under this name; falls
    back to NAVIXA's own shared app registration secret when not
    configured."""
    try:
        return get_secret_provider().get_secret(
            f"navixa-connection-{connection.environment}-azure-client-secret"
        )
    except SecretProviderError:
        return settings.entra_client_secret


def build_msal_app(
    connection: EnvironmentConnection, cache: msal.SerializableTokenCache | None = None
) -> msal.ConfidentialClientApplication:
    extra = connection.extra_config or {}
    client_id = extra.get("app_registration_client_id") or settings.entra_client_id
    authority_tenant_id = extra.get("app_registration_tenant_id") or settings.entra_tenant_id
    return msal.ConfidentialClientApplication(
        client_id=client_id,
        client_credential=get_connection_client_secret(connection),
        authority=f"https://login.microsoftonline.com/{authority_tenant_id}",
        token_cache=cache,
    )


class DelegatedMsalCredential(AsyncTokenCredential):
    """Wraps the environment connection's stored MSAL token cache. MSAL
    itself is synchronous, so acquisition runs in a thread; when the cache
    mutates (MSAL rotates refresh tokens on use) the new state is
    re-encrypted and persisted back to the EnvironmentConnection row via a
    short-lived DB session."""

    def __init__(self, connection: EnvironmentConnection | None):
        self._connection = connection

    async def get_token(self, *scopes: str, **kwargs) -> AccessToken:
        return await asyncio.to_thread(self._acquire_sync, list(scopes) or [ARM_SCOPE])

    def _acquire_sync(self, scopes: list[str]) -> AccessToken:
        if self._connection is None or not self._connection.delegated_token_cache:
            raise DelegatedAuthRequiredError(
                self._connection.environment if self._connection else "unknown", "azure"
            )

        cache = msal.SerializableTokenCache()
        cache.deserialize(decrypt(self._connection.delegated_token_cache))
        app = build_msal_app(self._connection, cache=cache)

        accounts = app.get_accounts()
        if not accounts:
            raise DelegatedAuthRequiredError(self._connection.environment, "azure")

        result = app.acquire_token_silent(scopes, account=accounts[0])
        if not result or "access_token" not in result:
            raise DelegatedAuthRequiredError(self._connection.environment, "azure")

        if cache.has_state_changed:
            self._persist_cache(cache)

        expires_on = int(time.time()) + int(result.get("expires_in", 3600))
        return AccessToken(result["access_token"], expires_on)

    def _persist_cache(self, cache: msal.SerializableTokenCache) -> None:
        from app.database.session import SessionLocal

        db = SessionLocal()
        try:
            connection = db.get(EnvironmentConnection, self._connection.id)
            if connection is not None:
                connection.delegated_token_cache = encrypt(cache.serialize())
                db.commit()
        finally:
            db.close()

    async def close(self) -> None:
        return None


def get_scoped_credential(connection: EnvironmentConnection | None) -> AsyncTokenCredential:
    if settings.cloud_auth_mode == "delegated":
        return DelegatedMsalCredential(connection)

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
