import uuid

from sqlalchemy.orm import Session

from app.models.audit_job import AuditJob
from app.models.cloud_tenant import CloudScope, CloudTenant
from app.schemas.tenant import ScopeCreate, TenantCreate, TenantUpdate


class TenantHasAuditJobsError(Exception):
    """Raised when deleting a tenant that still has audit jobs referencing
    it - audit history is never cascade-deleted, so the caller must resolve
    this explicitly rather than silently losing records."""

    def __init__(self, job_count: int):
        self.job_count = job_count
        super().__init__(f"Tenant has {job_count} audit job(s) referencing it")


def create_tenant(db: Session, payload: TenantCreate, created_by: uuid.UUID) -> CloudTenant:
    tenant = CloudTenant(**payload.model_dump(), created_by=created_by)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


def list_tenants(db: Session, provider: str | None = None) -> list[CloudTenant]:
    query = db.query(CloudTenant)
    if provider:
        query = query.filter(CloudTenant.provider == provider)
    return query.order_by(CloudTenant.tenant_name).all()


def get_tenant(db: Session, tenant_id: uuid.UUID) -> CloudTenant | None:
    return db.get(CloudTenant, tenant_id)


def update_tenant(db: Session, tenant: CloudTenant, payload: TenantUpdate) -> CloudTenant:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(tenant, field, value)
    db.commit()
    db.refresh(tenant)
    return tenant


def delete_tenant(db: Session, tenant: CloudTenant) -> None:
    job_count = db.query(AuditJob).filter(AuditJob.tenant_id == tenant.id).count()
    if job_count > 0:
        raise TenantHasAuditJobsError(job_count)
    db.delete(tenant)
    db.commit()


def create_scope(db: Session, tenant_id: uuid.UUID, payload: ScopeCreate) -> CloudScope:
    scope = CloudScope(tenant_id=tenant_id, **payload.model_dump())
    db.add(scope)
    db.commit()
    db.refresh(scope)
    return scope


def list_scopes(db: Session, tenant_id: uuid.UUID) -> list[CloudScope]:
    return db.query(CloudScope).filter(CloudScope.tenant_id == tenant_id).all()
