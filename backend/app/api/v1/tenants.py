import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.database.session import get_db
from app.models.role import ADMIN, AUDITOR, VIEWER
from app.models.user import User
from app.schemas.tenant import (
    ScopeCreate,
    ScopeResponse,
    TenantCreate,
    TenantResponse,
    TenantUpdate,
)
from app.tenant_registry import service

router = APIRouter(prefix="/tenants", tags=["Tenants"])


def _get_tenant_or_404(db: Session, tenant_id: uuid.UUID):
    tenant = service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
def create_tenant(
    payload: TenantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ADMIN)),
) -> TenantResponse:
    return service.create_tenant(db, payload, created_by=current_user.id)


@router.get("", response_model=list[TenantResponse])
def list_tenants(
    provider: str | None = None,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN, AUDITOR, VIEWER)),
) -> list[TenantResponse]:
    return service.list_tenants(db, provider)


@router.get("/{tenant_id}", response_model=TenantResponse)
def get_tenant(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN, AUDITOR, VIEWER)),
) -> TenantResponse:
    return _get_tenant_or_404(db, tenant_id)


@router.patch("/{tenant_id}", response_model=TenantResponse)
def update_tenant(
    tenant_id: uuid.UUID,
    payload: TenantUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN)),
) -> TenantResponse:
    tenant = _get_tenant_or_404(db, tenant_id)
    return service.update_tenant(db, tenant, payload)


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tenant(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN)),
) -> None:
    tenant = _get_tenant_or_404(db, tenant_id)
    service.delete_tenant(db, tenant)


@router.post(
    "/{tenant_id}/scopes", response_model=ScopeResponse, status_code=status.HTTP_201_CREATED
)
def create_scope(
    tenant_id: uuid.UUID,
    payload: ScopeCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN)),
) -> ScopeResponse:
    _get_tenant_or_404(db, tenant_id)
    return service.create_scope(db, tenant_id, payload)


@router.get("/{tenant_id}/scopes", response_model=list[ScopeResponse])
def list_scopes(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN, AUDITOR, VIEWER)),
) -> list[ScopeResponse]:
    _get_tenant_or_404(db, tenant_id)
    return service.list_scopes(db, tenant_id)
