import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.audit_job import AuditJob, AuditJobScope
from app.models.cloud_tenant import CloudTenant
from app.schemas.discover import AuditJobCreate, AuditJobListItem


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


def list_audit_jobs(db: Session, tenant_id: uuid.UUID | None = None) -> list[AuditJobListItem]:
    query = (
        db.query(
            AuditJob.id,
            AuditJob.tenant_id,
            CloudTenant.tenant_name,
            AuditJob.status,
            AuditJob.created_at,
            func.count(AuditJobScope.id).label("scope_count"),
        )
        .join(CloudTenant, CloudTenant.id == AuditJob.tenant_id)
        .outerjoin(AuditJobScope, AuditJobScope.audit_job_id == AuditJob.id)
        .group_by(AuditJob.id, CloudTenant.tenant_name)
        .order_by(AuditJob.created_at.desc())
    )
    if tenant_id is not None:
        query = query.filter(AuditJob.tenant_id == tenant_id)

    return [
        AuditJobListItem(
            id=row.id,
            tenant_id=row.tenant_id,
            tenant_name=row.tenant_name,
            status=row.status,
            created_at=row.created_at,
            scope_count=row.scope_count,
        )
        for row in query.all()
    ]


def delete_audit_job(db: Session, job: AuditJob) -> None:
    db.delete(job)
    db.commit()
