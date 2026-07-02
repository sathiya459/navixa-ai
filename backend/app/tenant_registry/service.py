import uuid

from sqlalchemy.orm import Session

from app.models.cloud_tenant import CloudScope, CloudTenant
from app.schemas.tenant import ScopeCreate, TenantCreate, TenantUpdate


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
