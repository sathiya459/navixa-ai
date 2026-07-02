"""Persists NAVIXA Discover results: per-resource-type status + normalized inventory."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.collectors.aws.orchestrator import discover_aws_scope
from app.collectors.base import CollectionResult
from app.collectors.normalization import normalize_aws_results
from app.models.audit_job import AuditJobScope, ResourceCollectionStatusRow
from app.models.network_resource import NetworkResource


def _overall_status(results: list[CollectionResult]) -> str:
    statuses = {r.status for r in results}
    if statuses == {"success"}:
        return "success"
    if "success" in statuses:
        return "partial"
    return "failed"


async def run_discovery_for_scope(
    db: Session, audit_job_scope: AuditJobScope, external_scope_id: str, region: str
) -> None:
    audit_job_scope.status = "running"
    audit_job_scope.started_at = datetime.now(timezone.utc)
    db.commit()

    results = await discover_aws_scope(external_scope_id, region)

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

    normalized_rows = normalize_aws_results(results)
    for row in normalized_rows:
        db.add(NetworkResource(audit_job_scope_id=audit_job_scope.id, **row))

    audit_job_scope.status = _overall_status(results)
    audit_job_scope.completed_at = datetime.now(timezone.utc)
    db.commit()
