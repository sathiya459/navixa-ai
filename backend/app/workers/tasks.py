"""Outer Celery orchestration for NAVIXA Discover (Section 10a).

One Celery task per audit job; inside the task, an asyncio event loop drives
concurrent per-scope discovery, each of which internally fans out concurrent
per-resource-type collection.
"""

import asyncio
import uuid
from datetime import datetime, timezone

from app.collectors.discover_service import run_discovery_for_scope
from app.config.rate_limits import MAX_PARALLEL_SCOPES
from app.database.session import SessionLocal
from app.models.audit_job import AuditJob, AuditJobScope
from app.models.cloud_tenant import CloudScope
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

        job_scopes = (
            db.query(AuditJobScope).filter(AuditJobScope.audit_job_id == audit_job_id).all()
        )

        max_parallel = MAX_PARALLEL_SCOPES.get("aws", 5)
        semaphore = asyncio.Semaphore(max_parallel)

        async def _run_one(job_scope: AuditJobScope):
            cloud_scope = db.get(CloudScope, job_scope.cloud_scope_id)
            async with semaphore:
                await run_discovery_for_scope(
                    db, job_scope, cloud_scope.external_scope_id, region="us-east-1"
                )

        await asyncio.gather(*(_run_one(js) for js in job_scopes), return_exceptions=True)

        statuses = {js.status for js in job_scopes}
        audit_job.status = "completed" if statuses == {"success"} else "partial"
        audit_job.completed_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()
