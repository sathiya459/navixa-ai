from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.collectors.delegated_auth_errors import DelegatedAuthRequiredError, build_delegated_auth_detail
from app.database.session import get_db
from app.models.role import ADMIN
from app.models.user import User
from app.schemas.tenant import (
    AvailableTenantResponse,
    EnvironmentConnectionResponse,
    EnvironmentConnectionUpsert,
    ImportTenantsRequest,
    TenantResponse,
)
from app.tenant_registry.azure_import import discover_available_tenants, import_tenants
from app.tenant_registry.connection_service import (
    get_connection,
    list_connections,
    upsert_connection_config,
)

router = APIRouter(prefix="/connections", tags=["Connections"])


@router.get("", response_model=list[EnvironmentConnectionResponse])
def get_connections(
    environment: str = "dev",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ADMIN)),
) -> list[EnvironmentConnectionResponse]:
    connections = list_connections(db, environment)
    return [
        EnvironmentConnectionResponse(
            environment=c.environment or environment,
            provider=c.provider,
            sso_login_url=c.sso_login_url,
            region=c.region,
            connected=bool(c.delegated_token_cache),
        )
        for c in connections
    ]


@router.put("/{environment}/{provider}", response_model=EnvironmentConnectionResponse)
def upsert_connection(
    environment: str,
    provider: str,
    payload: EnvironmentConnectionUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ADMIN)),
) -> EnvironmentConnectionResponse:
    connection = upsert_connection_config(
        db,
        environment,
        provider,
        created_by=current_user.id,
        sso_login_url=payload.sso_login_url,
        region=payload.region,
        extra_config=payload.extra_config,
    )
    return EnvironmentConnectionResponse(
        environment=connection.environment,
        provider=connection.provider,
        sso_login_url=connection.sso_login_url,
        region=connection.region,
        connected=bool(connection.delegated_token_cache),
    )


def _get_azure_connection_or_404(db: Session, environment: str):
    connection = get_connection(db, environment, "azure")
    if connection is None or not connection.delegated_token_cache:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_delegated_auth_detail(environment, "azure"),
        )
    return connection


@router.get("/{environment}/azure/available-tenants", response_model=list[AvailableTenantResponse])
async def get_available_tenants(
    environment: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN)),
) -> list[AvailableTenantResponse]:
    connection = _get_azure_connection_or_404(db, environment)
    try:
        tenants = await discover_available_tenants(connection, db, environment)
    except DelegatedAuthRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_delegated_auth_detail(exc.environment, exc.provider),
        ) from exc
    return [
        AvailableTenantResponse(
            tenant_id=t.tenant_id, display_name=t.display_name, already_added=t.already_added
        )
        for t in tenants
    ]


@router.post("/{environment}/azure/import-tenants", response_model=list[TenantResponse])
async def post_import_tenants(
    environment: str,
    payload: ImportTenantsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ADMIN)),
) -> list[TenantResponse]:
    connection = _get_azure_connection_or_404(db, environment)
    try:
        created = await import_tenants(
            connection, db, environment, payload.tenant_ids, created_by=current_user.id
        )
    except DelegatedAuthRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_delegated_auth_detail(exc.environment, exc.provider),
        ) from exc
    return created
