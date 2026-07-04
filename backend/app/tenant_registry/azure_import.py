"""Azure tenant onboarding by picking from the environment connection's
own visibility (Section: Tenant Registry Azure auto-discovery) rather than
typing tenant name/ID by hand - mirrors account_sync.py's pattern but for
onboarding whole tenants (with their subscriptions) instead of syncing
scopes onto an already-registered tenant.
"""

from dataclasses import dataclass
import uuid

from sqlalchemy.orm import Session

from app.collectors.azure.client import list_available_tenants, list_subscriptions_for_tenant
from app.models.cloud_tenant import CloudTenant
from app.models.environment_connection import EnvironmentConnection
from app.schemas.tenant import ScopeCreate, TenantCreate
from app.tenant_registry.service import create_scope, create_tenant, list_tenants


@dataclass
class AvailableTenant:
    tenant_id: str
    display_name: str
    already_added: bool


async def discover_available_tenants(
    connection: EnvironmentConnection, db: Session, environment: str
) -> list[AvailableTenant]:
    candidates = await list_available_tenants(connection)
    existing_ids = {
        t.external_tenant_id for t in list_tenants(db, provider="azure", environment=environment)
    }
    return [
        AvailableTenant(
            tenant_id=c["tenant_id"],
            display_name=c["display_name"],
            already_added=c["tenant_id"] in existing_ids,
        )
        for c in candidates
    ]


async def import_tenants(
    connection: EnvironmentConnection,
    db: Session,
    environment: str,
    tenant_ids: list[str],
    created_by: uuid.UUID,
) -> list[CloudTenant]:
    available = {t["tenant_id"]: t for t in await list_available_tenants(connection)}
    existing_ids = {
        t.external_tenant_id for t in list_tenants(db, provider="azure", environment=environment)
    }

    created: list[CloudTenant] = []
    for tenant_id in tenant_ids:
        if tenant_id in existing_ids or tenant_id not in available:
            continue

        tenant = create_tenant(
            db,
            TenantCreate(
                provider="azure",
                environment=environment,
                tenant_name=available[tenant_id]["display_name"],
                external_tenant_id=tenant_id,
                auth_mode="delegated",
                connection_id=connection.id,
            ),
            created_by=created_by,
        )

        for sub in await list_subscriptions_for_tenant(connection, tenant_id):
            create_scope(
                db,
                tenant.id,
                ScopeCreate(
                    scope_type="subscription",
                    external_scope_id=sub["subscription_id"],
                    display_name=sub["display_name"],
                ),
            )

        created.append(tenant)

    return created
