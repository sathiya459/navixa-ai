"""Outer Celery orchestration for NAVIXA Discover (Section 10a).

One Celery task per audit job; inside the task, an asyncio event loop drives
concurrent per-scope discovery, each of which internally fans out concurrent
per-resource-type collection.
"""

import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.collectors.discover_service import run_discovery_for_scope
from app.config.rate_limits import MAX_PARALLEL_SCOPES
from app.database.session import SessionLocal
from app.graph_engine.writer import GraphResourceInput, sync_job_to_graph
from app.models.audit_job import AuditJob, AuditJobScope
from app.models.cloud_tenant import CloudScope, CloudTenant
from app.models.network_resource import NetworkResource
from app.workers.celery_app import celery_app


@celery_app.task(name="navixa.run_discovery")
def run_discovery(audit_job_id: str) -> None:
    asyncio.run(_run_discovery_async(uuid.UUID(audit_job_id)))


async def _run_discovery_async(audit_job_id: uuid.UUID) -> None:
    db = SessionLocal()
    try:
        audit_job = db.get(AuditJob, audit_job_id)
        if audit_job is None:
            return

        audit_job.status = "discovering"
        audit_job.started_at = datetime.now(timezone.utc)
        db.commit()

        tenant = db.get(CloudTenant, audit_job.tenant_id)

        job_scopes = (
            db.query(AuditJobScope).filter(AuditJobScope.audit_job_id == audit_job_id).all()
        )

        max_parallel = MAX_PARALLEL_SCOPES.get(tenant.provider, 5)
        semaphore = asyncio.Semaphore(max_parallel)

        async def _run_one(job_scope: AuditJobScope):
            cloud_scope = db.get(CloudScope, job_scope.cloud_scope_id)
            async with semaphore:
                await run_discovery_for_scope(
                    db,
                    job_scope,
                    tenant.provider,
                    cloud_scope.external_scope_id,
                    region="us-east-1",
                )

        await asyncio.gather(*(_run_one(js) for js in job_scopes), return_exceptions=True)

        statuses = {js.status for js in job_scopes}

        if "success" in statuses or "partial" in statuses:
            audit_job.status = "graphing"
            db.commit()
            _sync_graph(db, audit_job_id)

        if statuses == {"success"}:
            audit_job.status = "completed"
        elif statuses == {"failed"}:
            audit_job.status = "failed"
        else:
            audit_job.status = "partial"
        audit_job.completed_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()


def _sync_graph(db: Session, audit_job_id: uuid.UUID) -> None:
    """Mirrors this job's normalized inventory into navixa_graph (Neo4j).

    Best-effort: a graph sync failure degrades the job to "partial" rather
    than failing it outright, since the relational data (findings' source
    of truth) is already durably persisted at this point.
    """
    resources = (
        db.query(NetworkResource)
        .join(AuditJobScope, NetworkResource.audit_job_scope_id == AuditJobScope.id)
        .filter(AuditJobScope.audit_job_id == audit_job_id)
        .all()
    )
    graph_inputs = [
        GraphResourceInput(
            id=r.id,
            resource_type=r.resource_type,
            provider=r.provider,
            native_id=r.native_id,
            name=r.name,
            attributes=r.attributes,
        )
        for r in resources
    ]
    try:
        sync_job_to_graph(graph_inputs, audit_job_id)
    except Exception:  # noqa: BLE001
        pass
