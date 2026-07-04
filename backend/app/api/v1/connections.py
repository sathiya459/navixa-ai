import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.collectors.delegated_auth_errors import DelegatedAuthRequiredError, build_delegated_auth_detail
from app.database.session import get_db
from app.models.role import ADMIN
from app.models.user import User
from app.schemas.tenant import (
    AvailableTenantResponse,
    ConnectionCreate,
    ConnectionUpdate,
    EnvironmentConnectionResponse,
    ImportTenantsRequest,
    TenantResponse,
)
from app.tenant_registry import aws_import
from app.tenant_registry import azure_import
from app.tenant_registry.connection_service import (
    DuplicateConnectionNameError,
    create_connection,
    delete_connection,
    get_connection_by_id,
    list_connections,
    update_connection_config,
)

router = APIRouter(prefix="/connections", tags=["Connections"])


def _to_response(c) -> EnvironmentConnectionResponse:
    return EnvironmentConnectionResponse(
        id=c.id,
        environment=c.environment,
        provider=c.provider,
        name=c.name,
        sso_login_url=c.sso_login_url,
        region=c.region,
        connected=bool(c.delegated_token_cache),
    )


@router.get("", response_model=list[EnvironmentConnectionResponse])
def get_connections(
    environment: str = "dev",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ADMIN)),
) -> list[EnvironmentConnectionResponse]:
    return [_to_response(c) for c in list_connections(db, environment)]


@router.post("/{environment}/{provider}", response_model=EnvironmentConnectionResponse)
def post_connection(
    environment: str,
    provider: str,
    payload: ConnectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ADMIN)),
) -> EnvironmentConnectionResponse:
    try:
        connection = create_connection(
            db, environment, provider, payload.name, created_by=current_user.id
        )
    except DuplicateConnectionNameError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _to_response(connection)


@router.put("/{environment}/{connection_id}", response_model=EnvironmentConnectionResponse)
def put_connection(
    environment: str,
    connection_id: uuid.UUID,
    payload: ConnectionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ADMIN)),
) -> EnvironmentConnectionResponse:
    connection = update_connection_config(
        db,
        connection_id,
        sso_login_url=payload.sso_login_url,
        region=payload.region,
        extra_config=payload.extra_config,
    )
    if connection is None or connection.environment != environment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")
    return _to_response(connection)


@router.delete("/{environment}/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_connection_endpoint(
    environment: str,
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ADMIN)),
) -> None:
    connection = get_connection_by_id(db, connection_id)
    if connection is None or connection.environment != environment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")
    delete_connection(db, connection_id)


def _get_connection_or_404(db: Session, environment: str, connection_id: uuid.UUID, provider: str):
    connection = get_connection_by_id(db, connection_id)
    if (
        connection is None
        or connection.environment != environment
        or connection.provider != provider
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")
    if not connection.delegated_token_cache:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_delegated_auth_detail(environment, provider),
        )
    return connection


@router.get(
    "/{environment}/{connection_id}/azure/available-tenants",
    response_model=list[AvailableTenantResponse],
)
async def get_azure_available_tenants(
    environment: str,
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN)),
) -> list[AvailableTenantResponse]:
    connection = _get_connection_or_404(db, environment, connection_id, "azure")
    try:
        tenants = await azure_import.discover_available_tenants(connection, db, environment)
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


@router.post(
    "/{environment}/{connection_id}/azure/import-tenants",
    response_model=list[TenantResponse],
)
async def post_azure_import_tenants(
    environment: str,
    connection_id: uuid.UUID,
    payload: ImportTenantsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ADMIN)),
) -> list[TenantResponse]:
    connection = _get_connection_or_404(db, environment, connection_id, "azure")
    try:
        created = await azure_import.import_tenants(
            connection, db, environment, payload.tenant_ids, created_by=current_user.id
        )
    except DelegatedAuthRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_delegated_auth_detail(exc.environment, exc.provider),
        ) from exc
    return created


@router.get(
    "/{environment}/{connection_id}/aws/available-tenants",
    response_model=list[AvailableTenantResponse],
)
async def get_aws_available_tenants(
    environment: str,
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN)),
) -> list[AvailableTenantResponse]:
    connection = _get_connection_or_404(db, environment, connection_id, "aws")
    try:
        tenants = await aws_import.discover_available_tenants(connection, db, environment)
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


@router.post(
    "/{environment}/{connection_id}/aws/import-tenants",
    response_model=list[TenantResponse],
)
async def post_aws_import_tenants(
    environment: str,
    connection_id: uuid.UUID,
    payload: ImportTenantsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ADMIN)),
) -> list[TenantResponse]:
    connection = _get_connection_or_404(db, environment, connection_id, "aws")
    try:
        created = await aws_import.import_tenants(
            connection, db, environment, payload.tenant_ids, created_by=current_user.id
        )
    except DelegatedAuthRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_delegated_auth_detail(exc.environment, exc.provider),
        ) from exc
    return created
