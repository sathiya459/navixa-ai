"""Tenant account/subscription discovery ("Sync Accounts"): given an already
registered cloud tenant, ask the cloud provider directly which
accounts/subscriptions actually exist under it, and diff that against what's
already registered as a CloudScope - so a new account added on the cloud
side doesn't require manually typing its ID into NAVIXA.

Reuses the exact per-tenant delegated-SSO credential resolution NAVIXA
Discover itself uses (app/collectors/aws/client.py,
app/collectors/azure/client.py) rather than inventing a separate auth path -
if there's no valid cached SSO session for the tenant, this raises
DelegatedAuthRequiredError just like a Discover job would, so the same
popup-login flow applies here too.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.cloud_tenant import CloudTenant
from app.tenant_registry.service import list_scopes


class UnsupportedProviderError(Exception):
    """Raised for providers without an account-discovery implementation yet
    (GCP, OCI) - matches the project's earlier explicit decision to
    deprioritize those two providers."""


@dataclass
class AvailableAccount:
    external_id: str
    display_name: str
    already_added: bool


async def discover_available_accounts(
    tenant: CloudTenant, db: Session
) -> list[AvailableAccount]:
    if tenant.provider == "aws":
        candidates = await _discover_aws_accounts(tenant)
    elif tenant.provider == "azure":
        candidates = await _discover_azure_subscriptions(tenant)
    else:
        raise UnsupportedProviderError(
            f"Account sync is not yet supported for provider '{tenant.provider}'"
        )

    existing_ids = {scope.external_scope_id for scope in list_scopes(db, tenant.id)}
    return [
        AvailableAccount(
            external_id=external_id,
            display_name=display_name,
            already_added=external_id in existing_ids,
        )
        for external_id, display_name in candidates
    ]


async def _discover_aws_accounts(tenant: CloudTenant) -> list[tuple[str, str]]:
    from app.collectors.aws.client import list_sso_accounts

    return await list_sso_accounts(tenant)


async def _discover_azure_subscriptions(tenant: CloudTenant) -> list[tuple[str, str]]:
    from app.collectors.azure.client import get_scoped_credential, get_subscription_client

    credential = get_scoped_credential(tenant)
    client = get_subscription_client(credential)
    try:
        subscriptions = []
        async for sub in client.subscriptions.list():
            subscriptions.append((sub.subscription_id, sub.display_name or sub.subscription_id))
        return subscriptions
    finally:
        await client.close()
        await credential.close()
