"""Azure credential broker and async client factory for NAVIXA Discover.

Phase 2 stubs the Entra ID OAuth exchange the same way Phase 1 stubbed AWS
AssumeRole (Section 8): a scoped, short-lived token is assumed here so the
collector pipeline can be built and tested without a live Azure tenant.
Phase 5 replaces `get_scoped_credential` with real Entra ID OAuth via
`azure-identity`, still never persisting long-lived credentials.
"""

from azure.core.credentials_async import AsyncTokenCredential
from azure.core.credentials import AccessToken
from azure.mgmt.network.aio import NetworkManagementClient


class StubAsyncCredential(AsyncTokenCredential):
    """Stand-in for a real Entra ID OAuth token until Phase 5 wiring lands."""

    async def get_token(self, *scopes: str, **kwargs) -> AccessToken:
        return AccessToken("stub-access-token", 9999999999)

    async def close(self) -> None:
        return None


async def get_scoped_credential(external_scope_id: str) -> AsyncTokenCredential:
    """Stub: exchange federated Entra ID identity for a scoped credential."""
    return StubAsyncCredential()


def get_network_client(
    credential: AsyncTokenCredential, subscription_id: str
) -> NetworkManagementClient:
    return NetworkManagementClient(credential, subscription_id)
