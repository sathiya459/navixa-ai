"""Persists NAVIXA Discover results: per-resource-type status + normalized inventory."""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.collectors.aws.orchestrator import discover_aws_scope
from app.collectors.aws.orchestrator import expected_resource_types as _aws_expected_types
from app.collectors.azure.orchestrator import discover_azure_scope
from app.collectors.azure.orchestrator import expected_resource_types as _azure_expected_types
from app.collectors.base import CollectionResult
from app.collectors.delegated_auth_errors import DelegatedAuthRequiredError
from app.collectors.gcp.orchestrator import discover_gcp_scope
from app.collectors.gcp.orchestrator import expected_resource_types as _gcp_expected_types
from app.collectors.oci.orchestrator import discover_oci_scope
from app.collectors.oci.orchestrator import expected_resource_types as _oci_expected_types
from app.collectors.normalization import normalize_results
from app.models.audit_job import AuditJobScope, ResourceCollectionStatusRow
from app.models.cloud_tenant import CloudTenant
from app.models.network_resource import NetworkResource
from app.tenant_registry.connection_service import get_connection_by_id

logger = logging.getLogger(__name__)


def _overall_status(results: list[CollectionResult]) -> str:
    statuses = {r.status for r in results}
    if statuses == {"success"}:
        return "success"
    if "success" in statuses:
        return "partial"
    return "failed"


def expected_resource_types(provider: str, resource_types: list[str] | None) -> set[str]:
    """The resource-type set a scope's discovery run is expected to
    collect, used to compute "N of M collected" progress before (and
    while) the scope is still running. GCP/OCI don't support the
    `resource_types` filter yet, so it's ignored for them."""
    if provider == "aws":
        return _aws_expected_types(resource_types)
    if provider == "azure":
        return _azure_expected_types(resource_types)
    if provider == "gcp":
        return _gcp_expected_types()
    if provider == "oci":
        return _oci_expected_types()
    return set()


async def _discover_by_provider(
    db: Session,
    tenant: CloudTenant,
    external_scope_id: str,
    region: str,
    resource_types: list[str] | None,
    on_result,
) -> list[CollectionResult]:
    provider = tenant.provider
    connection = get_connection_by_id(db, tenant.connection_id) if tenant.connection_id else None
    try:
        if provider == "aws":
            return await discover_aws_scope(
                connection, external_scope_id, region, resource_types, on_result=on_result
            )
        if provider == "azure":
            return await discover_azure_scope(
                connection, external_scope_id, resource_types, on_result=on_result
            )
        if provider == "gcp":
            return await discover_gcp_scope(external_scope_id, on_result=on_result)
        if provider == "oci":
            return await discover_oci_scope(external_scope_id, region, on_result=on_result)
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

    # Persisted as each resource type finishes (rather than in bulk after
    # the whole scope completes) so a job's progress - resource types
    # collected so far, resources found so far - is visible on the
    # Audit Jobs page's status poll while collection is still running,
    # instead of the UI showing nothing until the entire scope is done.
    persisted_types: set[str] = set()

    def _persist(result: CollectionResult) -> None:
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
        db.commit()
        persisted_types.add(result.resource_type)

    async def _on_result(result: CollectionResult) -> None:
        _persist(result)

    # `workers/tasks.py` runs every scope's `run_discovery_for_scope` under
    # `asyncio.gather(..., return_exceptions=True)`, which means an
    # exception here would otherwise be silently discarded - the scope
    # would stay at "running" forever with zero status rows, no error
    # anywhere, and the job would still reach a terminal status (since the
    # gather itself doesn't propagate). This has actually happened in
    # practice: an unhandled exception from credential setup (anything
    # other than the timeout each orchestrator explicitly catches - e.g. a
    # real AWS AccessDenied/permission-set-name-mismatch error) looked
    # exactly like a scope stuck "running" indefinitely with no VPCs and
    # no visible error. So *every* failure mode from here down must land
    # in a "failed" scope with a real error_detail, not propagate.
    try:
        results = await _discover_by_provider(
            db, tenant, external_scope_id, region, resource_types, on_result=_on_result
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Unexpected error discovering scope %s (tenant %s, provider %s)",
            audit_job_scope.id,
            tenant.id,
            tenant.provider,
        )
        results = [
            CollectionResult(resource_type="_unexpected_error", status="failed", error_detail=str(exc))
        ]

    # Failures that short-circuit before any per-type collector runs (e.g.
    # DelegatedAuthRequiredError, credential-setup timeout/error) return a
    # synthetic result that bypasses `_on_result` above - persist those too
    # so the error still surfaces in the status API instead of silently
    # vanishing.
    for result in results:
        if result.resource_type not in persisted_types:
            _persist(result)

    normalized_rows = normalize_results(results, tenant.provider)
    for row in normalized_rows:
        db.add(NetworkResource(audit_job_scope_id=audit_job_scope.id, **row))

    audit_job_scope.status = _overall_status(results)
    audit_job_scope.completed_at = datetime.now(timezone.utc)
    db.commit()
