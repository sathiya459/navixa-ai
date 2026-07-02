import uuid

from sqlalchemy.orm import Session

from app.models.audit_job import AuditJob, AuditJobScope
from app.schemas.discover import AuditJobCreate


def create_audit_job(db: Session, payload: AuditJobCreate, initiated_by: uuid.UUID) -> AuditJob:
    audit_job = AuditJob(
        tenant_id=payload.tenant_id,
        initiated_by=initiated_by,
        status="queued",
        hub_selection={"hub_ids": payload.hub_selection} if payload.hub_selection else None,
    )
    db.add(audit_job)
    db.flush()

    for scope_id in payload.scope_ids:
        db.add(AuditJobScope(audit_job_id=audit_job.id, cloud_scope_id=scope_id, status="pending"))

    db.commit()
    db.refresh(audit_job)
    return audit_job


def get_audit_job(db: Session, job_id: uuid.UUID) -> AuditJob | None:
    return db.get(AuditJob, job_id)
