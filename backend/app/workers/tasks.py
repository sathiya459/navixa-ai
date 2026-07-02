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
from app.collectors.job_service import create_audit_job
from app.config.rate_limits import MAX_PARALLEL_SCOPES
from app.config.settings import get_settings
from app.database.session import SessionLocal
from app.graph_engine.writer import GraphResourceInput, sync_job_to_graph
from app.models.audit_job import AuditJob, AuditJobScope
from app.models.cloud_tenant import CloudScope, CloudTenant
from app.models.network_resource import NetworkResource
from app.schemas.discover import AuditJobCreate
from app.watch.service import get_due_schedules, mark_schedule_run
from app.workers.celery_app import celery_app


settings = get_settings()


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

        # Section 9's region_info is free-form JSONB; a "default_region" key
        # overrides settings.aws_default_region when the tenant specifies
        # one. Previously this was hardcoded to "us-east-1" regardless of
        # the tenant's actual region, which silently discovered whatever
        # resources happened to exist in that region instead of the
        # account's real one - found by running a real discovery job
        # against an ap-south-1 account and getting back us-east-1 data
        # with no error at all.
        region = (tenant.region_info or {}).get("default_region", settings.aws_default_region)

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
                    tenant,
                    cloud_scope.external_scope_id,
                    region=region,
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


@celery_app.task(name="navixa.check_scheduled_discoveries")
def check_scheduled_discoveries() -> None:
    """NAVIXA Watch groundwork: fired every 5 minutes by Celery Beat
    (see celery_app.py). For each due ScheduledDiscovery, enqueues a new
    discovery job and advances next_run_at - it does not itself compute
    diffs; run change detection separately via the /watch API once both
    the new and a prior job have completed.
    """
    db = SessionLocal()
    try:
        for schedule in get_due_schedules(db):
            payload = AuditJobCreate(
                tenant_id=schedule.tenant_id,
                scope_ids=[uuid.UUID(s) for s in schedule.scope_ids],
                hub_selection=schedule.hub_selection,
            )
            audit_job = create_audit_job(db, payload, initiated_by=schedule.created_by)
            run_discovery.delay(str(audit_job.id))
            mark_schedule_run(db, schedule)
    finally:
        db.close()
