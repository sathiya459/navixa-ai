import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.database.session import get_db
from app.models.role import ADMIN, READER
from app.models.user import User
from app.schemas.tenant import (
    AvailableAccountResponse,
    ScopeCreate,
    ScopeResponse,
    TenantCreate,
    TenantResponse,
    TenantUpdate,
)
from app.collectors.delegated_auth_errors import DelegatedAuthRequiredError, build_delegated_auth_detail
from app.tenant_registry import service
from app.tenant_registry.account_sync import UnsupportedProviderError, discover_available_accounts
from app.tenant_registry.service import TenantHasAuditJobsError

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
    environment: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ADMIN, READER)),
) -> list[TenantResponse]:
    # Readers always see Dev, regardless of what they pass - the
    # environment switch is an Admin-only capability, enforced here (not
    # just hidden in the UI).
    if ADMIN not in current_user.role_names:
        environment = "dev"
    return service.list_tenants(db, provider, environment)


@router.get("/{tenant_id}", response_model=TenantResponse)
def get_tenant(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN, READER)),
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
    try:
        service.delete_tenant(db, tenant)
    except TenantHasAuditJobsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot delete tenant '{tenant.tenant_name}': {exc.job_count} audit job(s) "
                "still reference it. Delete those audit jobs first, or keep the tenant for "
                "historical reporting."
            ),
        ) from exc


@router.get("/{tenant_id}/available-accounts", response_model=list[AvailableAccountResponse])
async def get_available_accounts(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN)),
) -> list[AvailableAccountResponse]:
    tenant = _get_tenant_or_404(db, tenant_id)
    try:
        accounts = await discover_available_accounts(tenant, db)
    except UnsupportedProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)
        ) from exc
    except DelegatedAuthRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_delegated_auth_detail(exc.environment, exc.provider),
        ) from exc
    return [
        AvailableAccountResponse(
            external_id=a.external_id, display_name=a.display_name, already_added=a.already_added
        )
        for a in accounts
    ]


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
    _current_user: User = Depends(require_role(ADMIN, READER)),
) -> list[ScopeResponse]:
    _get_tenant_or_404(db, tenant_id)
    return service.list_scopes(db, tenant_id)
