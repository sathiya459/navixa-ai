"""Persists NAVIXA Discover results: per-resource-type status + normalized inventory."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.collectors.aws.orchestrator import discover_aws_scope
from app.collectors.azure.orchestrator import discover_azure_scope
from app.collectors.base import CollectionResult
from app.collectors.delegated_auth_errors import DelegatedAuthRequiredError
from app.collectors.gcp.orchestrator import discover_gcp_scope
from app.collectors.oci.orchestrator import discover_oci_scope
from app.collectors.normalization import normalize_results
from app.models.audit_job import AuditJobScope, ResourceCollectionStatusRow
from app.models.cloud_tenant import CloudTenant
from app.models.network_resource import NetworkResource
from app.tenant_registry.connection_service import get_connection_by_id


def _overall_status(results: list[CollectionResult]) -> str:
    statuses = {r.status for r in results}
    if statuses == {"success"}:
        return "success"
    if "success" in statuses:
        return "partial"
    return "failed"


async def _discover_by_provider(
    db: Session,
    tenant: CloudTenant,
    external_scope_id: str,
    region: str,
    resource_types: list[str] | None,
) -> list[CollectionResult]:
    provider = tenant.provider
    connection = get_connection_by_id(db, tenant.connection_id) if tenant.connection_id else None
    try:
        if provider == "aws":
            return await discover_aws_scope(connection, external_scope_id, region, resource_types)
        if provider == "azure":
            return await discover_azure_scope(connection, external_scope_id, resource_types)
        if provider == "gcp":
            return await discover_gcp_scope(external_scope_id)
        if provider == "oci":
            return await discover_oci_scope(external_scope_id, region)
    except DelegatedAuthRequiredError as exc:
        return [
            CollectionResult(
                resource_type="_delegated_auth",
                status="failed",
                error_detail=(
                    f"No active SSO session for this tenant's {exc.provider.upper()} "
                    f"connection in the {exc.environment} environment. Reconnect it on "
                    "the Connections page and re-run this audit job."
                ),
            )
        ]
    raise NotImplementedError(f"NAVIXA Discover does not yet support provider: {provider}")


async def run_discovery_for_scope(
    db: Session,
    audit_job_scope: AuditJobScope,
    tenant: CloudTenant,
    external_scope_id: str,
    region: str,
    resource_types: list[str] | None = None,
) -> None:
    audit_job_scope.status = "running"
    audit_job_scope.started_at = datetime.now(timezone.utc)
    db.commit()

    results = await _discover_by_provider(db, tenant, external_scope_id, region, resource_types)

    for result in results:
        db.add(
            ResourceCollectionStatusRow(
                audit_job_scope_id=audit_job_scope.id,
                resource_type=result.resource_type,
                status=result.status,
                error_detail=result.error_detail,
                items_collected=len(result.items),
                duration_ms=result.duration_ms,
            )
        )

    normalized_rows = normalize_results(results, tenant.provider)
    for row in normalized_rows:
        db.add(NetworkResource(audit_job_scope_id=audit_job_scope.id, **row))

    audit_job_scope.status = _overall_status(results)
    audit_job_scope.completed_at = datetime.now(timezone.utc)
    db.commit()
