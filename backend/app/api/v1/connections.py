from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.database.session import get_db
from app.models.role import ADMIN
from app.models.user import User
from app.schemas.tenant import EnvironmentConnectionResponse, EnvironmentConnectionUpsert
from app.tenant_registry.connection_service import list_connections, upsert_connection_config

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
