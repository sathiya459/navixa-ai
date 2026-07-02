"""Azure credential broker and async client factory for NAVIXA Discover
(Section 8 / 8a).

Two real modes, selected by `settings.cloud_auth_mode`:
- "delegated": DefaultAzureCredential, which picks up whatever the
  developer already signed into via `az login` on this machine (falls
  through environment vars, managed identity, then the Azure CLI's own
  cached login - no separate flow needed in this backend).
- "app_only": a real Entra ID client-credentials (ClientSecretCredential)
  exchange when `azure_federation_*` settings are configured - the
  platform authenticates as its own registered Entra app, which must be
  granted Reader (or equivalent) access on each target subscription.

Falls back to the Phase 2 stub when the selected mode isn't configured,
so local dev without a real Azure tenant keeps working unchanged.
"""

from azure.core.credentials import AccessToken
from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import ClientSecretCredential, DefaultAzureCredential
from azure.mgmt.network.aio import NetworkManagementClient

from app.config.settings import get_settings

settings = get_settings()


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


async def get_scoped_credential(external_scope_id: str) -> AsyncTokenCredential:
    if settings.cloud_auth_mode == "delegated":
        return DefaultAzureCredential()

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
