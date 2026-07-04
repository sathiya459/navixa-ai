"""AWS tenant onboarding by picking from the environment connection's own
IAM Identity Center visibility (Section: Tenant Registry AWS auto-discovery).

Unlike Azure AD (one tenant can genuinely contain several subscriptions,
picked independently), AWS's delegated SSO session exposes a flat list of
accounts under a single IAM Identity Center instance - there is no
separate "tenant" concept to pick between. So AWS collapses to **one
CloudTenant per connection** (auto-created on first import, matching the
manual "Add Tenant" dialog's own placeholder of "AWS Organization ID or
root account ID"), with each accessible account imported as a `CloudScope`
(scope_type="account") under that single tenant - mirroring exactly how
`account_sync.py`'s existing "Sync Accounts" feature already treats AWS
accounts as scopes, and reusing that same accounts-as-scopes discovery
call (`list_sso_accounts`) rather than duplicating it.

`discover_available_tenants`/`import_tenants` keep their azure_import.py
-mirroring names (and `AvailableTenant` shape) for symmetry with the
shared `connections.py` routes and `TenantImportDialog` on the frontend,
even though for AWS they operate on accounts-to-become-scopes rather than
tenant candidates.
"""

from dataclasses import dataclass
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.collectors.aws.client import list_sso_accounts
from app.models.cloud_tenant import CloudTenant
from app.models.environment_connection import EnvironmentConnection
from app.schemas.tenant import ScopeCreate, TenantCreate
from app.tenant_registry.service import create_scope, create_tenant, list_scopes, list_tenants


@dataclass
class AvailableTenant:
    tenant_id: str
    display_name: str
    already_added: bool


def _find_tenant_for_connection(
    db: Session, connection: EnvironmentConnection, environment: str
) -> CloudTenant | None:
    for tenant in list_tenants(db, provider="aws", environment=environment):
        if tenant.connection_id == connection.id:
            return tenant
    return None


async def discover_available_tenants(
    connection: EnvironmentConnection, db: Session, environment: str
) -> list[AvailableTenant]:
    """Lists the AWS accounts visible to this connection's SSO session,
    flagging ones already added as a scope under this connection's tenant
    (there is at most one - see module docstring)."""
    candidates = await list_sso_accounts(connection)
    tenant = _find_tenant_for_connection(db, connection, environment)
    existing_ids = (
        {scope.external_scope_id for scope in list_scopes(db, tenant.id)} if tenant else set()
    )
    return [
        AvailableTenant(
            tenant_id=account_id,
            display_name=account_name,
            already_added=account_id in existing_ids,
        )
        for account_id, account_name in candidates
    ]


async def import_tenants(
    connection: EnvironmentConnection,
    db: Session,
    environment: str,
    tenant_ids: list[str],
    created_by: uuid.UUID,
) -> list[CloudTenant]:
    """Imports the selected AWS account IDs as scopes under this
    connection's single tenant, auto-creating that tenant on first import
    (see module docstring - AWS has no separate tenant concept to pick,
    unlike Azure AD)."""
    available = {account_id: account_name for account_id, account_name in await list_sso_accounts(connection)}

    tenant = _find_tenant_for_connection(db, connection, environment)
    if tenant is None:
        try:
            tenant = create_tenant(
                db,
                TenantCreate(
                    provider="aws",
                    environment=environment,
                    tenant_name=connection.name,
                    # Synthetic - AWS's IAM Identity Center ListAccounts API
                    # has no "organization ID" of its own to use here (unlike
                    # Azure AD's real tenant ID). Not a real AWS identifier,
                    # never shown to the cloud provider.
                    external_tenant_id=f"aws-connection:{connection.id}",
                    auth_mode="delegated",
                    connection_id=connection.id,
                ),
                created_by=created_by,
            )
        except IntegrityError:
            # Two near-simultaneous imports for the same connection (e.g. a
            # fast double-click before the "Add Selected" button's disabled
            # state takes effect) can both find no existing tenant and both
            # try to create one - this happened in practice. The DB's
            # partial unique index (migration c3d4e5f6a7b8) on
            # (connection_id) WHERE provider='aws' rejects the loser here;
            # recover by rolling back and using whichever tenant won.
            db.rollback()
            tenant = _find_tenant_for_connection(db, connection, environment)
            if tenant is None:
                raise

    existing_ids = {scope.external_scope_id for scope in list_scopes(db, tenant.id)}
    for account_id in tenant_ids:
        if account_id in existing_ids or account_id not in available:
            continue
        create_scope(
            db,
            tenant.id,
            ScopeCreate(
                scope_type="account",
                external_scope_id=account_id,
                display_name=available[account_id],
            ),
        )

    return [tenant]
