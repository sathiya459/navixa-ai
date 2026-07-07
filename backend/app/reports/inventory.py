"""Cross-job discovered-resource inventory backing the frontend's Reports
section: "what has NAVIXA Discover found so far", filterable by provider/
tenant/subscription, independent of any single audit job.

Each Discover run creates a fresh `AuditJobScope` (and fresh `NetworkResource`
rows under it) rather than updating previous rows in place - so a cloud
scope (subscription/account/project/compartment) that has been discovered
multiple times has multiple generations of resources in Postgres. "Current
inventory" here means resources from each scope's *most recently created*
audit job only, so re-running Discover naturally supersedes stale data
without deleting the historical record other pages (e.g. audit job history)
still rely on.
"""

import csv
import io
import uuid
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.audit_job import AuditJob, AuditJobScope
from app.models.cloud_tenant import CloudScope, CloudTenant
from app.models.network_resource import NetworkResource
from app.schemas.reports import DiscoveredResourceResponse


def _latest_scope_ids_subquery(db: Session):
    latest_per_scope = (
        db.query(
            AuditJobScope.cloud_scope_id.label("cloud_scope_id"),
            func.max(AuditJob.created_at).label("max_created_at"),
        )
        .join(AuditJob, AuditJobScope.audit_job_id == AuditJob.id)
        .group_by(AuditJobScope.cloud_scope_id)
        .subquery()
    )

    return (
        db.query(AuditJobScope.id)
        .join(AuditJob, AuditJobScope.audit_job_id == AuditJob.id)
        .join(
            latest_per_scope,
            (AuditJobScope.cloud_scope_id == latest_per_scope.c.cloud_scope_id)
            & (AuditJob.created_at == latest_per_scope.c.max_created_at),
        )
    )


def list_discovered_resources(
    db: Session,
    provider: str | None = None,
    tenant_id: uuid.UUID | None = None,
    scope_id: uuid.UUID | None = None,
    resource_type: str | None = None,
) -> list[DiscoveredResourceResponse]:
    latest_scope_ids = _latest_scope_ids_subquery(db)

    query = (
        db.query(
            NetworkResource,
            AuditJobScope.audit_job_id,
            CloudScope.id.label("scope_id"),
            CloudScope.scope_type,
            CloudScope.display_name.label("scope_display_name"),
            CloudTenant.id.label("tenant_id"),
            CloudTenant.tenant_name,
        )
        .join(AuditJobScope, NetworkResource.audit_job_scope_id == AuditJobScope.id)
        .join(CloudScope, AuditJobScope.cloud_scope_id == CloudScope.id)
        .join(CloudTenant, CloudScope.tenant_id == CloudTenant.id)
        .filter(AuditJobScope.id.in_(latest_scope_ids))
    )

    if provider:
        query = query.filter(NetworkResource.provider == provider)
    if tenant_id:
        query = query.filter(CloudTenant.id == tenant_id)
    if scope_id:
        query = query.filter(CloudScope.id == scope_id)
    if resource_type:
        query = query.filter(NetworkResource.resource_type == resource_type)

    query = query.order_by(CloudTenant.tenant_name, CloudScope.display_name, NetworkResource.resource_type)

    return [
        DiscoveredResourceResponse(
            id=row.NetworkResource.id,
            provider=row.NetworkResource.provider,
            resource_type=row.NetworkResource.resource_type,
            native_id=row.NetworkResource.native_id,
            name=row.NetworkResource.name,
            attributes=row.NetworkResource.attributes,
            collected_at=row.NetworkResource.collected_at,
            audit_job_id=row.audit_job_id,
            tenant_id=row.tenant_id,
            tenant_name=row.tenant_name,
            scope_id=row.scope_id,
            scope_type=row.scope_type,
            scope_display_name=row.scope_display_name,
        )
        for row in query.all()
    ]


_CSV_COLUMNS = [
    "provider",
    "resource_type",
    "native_id",
    "name",
    "tenant_name",
    "scope_type",
    "scope_display_name",
    "collected_at",
]


def resources_to_csv(resources: list[DiscoveredResourceResponse]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=_CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for resource in resources:
        row: dict[str, Any] = resource.model_dump()
        row["collected_at"] = resource.collected_at.isoformat()
        writer.writerow(row)
    return buffer.getvalue()
