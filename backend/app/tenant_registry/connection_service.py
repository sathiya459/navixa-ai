import uuid

from sqlalchemy.orm import Session

from app.models.environment_connection import EnvironmentConnection

ALL_PROVIDERS = ("aws", "azure", "gcp", "oci")


def get_connection(db: Session, environment: str, provider: str) -> EnvironmentConnection | None:
    return (
        db.query(EnvironmentConnection)
        .filter(
            EnvironmentConnection.environment == environment,
            EnvironmentConnection.provider == provider,
        )
        .first()
    )


def get_or_create_connection(
    db: Session, environment: str, provider: str, created_by: uuid.UUID
) -> EnvironmentConnection:
    connection = get_connection(db, environment, provider)
    if connection is not None:
        return connection
    connection = EnvironmentConnection(
        environment=environment, provider=provider, created_by=created_by
    )
    db.add(connection)
    db.commit()
    db.refresh(connection)
    return connection


def list_connections(db: Session, environment: str) -> list[EnvironmentConnection]:
    existing = {c.provider: c for c in db.query(EnvironmentConnection).filter(
        EnvironmentConnection.environment == environment
    )}
    return [existing.get(provider) for provider in ALL_PROVIDERS if provider in existing] + [
        EnvironmentConnection(environment=environment, provider=provider)
        for provider in ALL_PROVIDERS
        if provider not in existing
    ]


def upsert_connection_config(
    db: Session,
    environment: str,
    provider: str,
    created_by: uuid.UUID,
    sso_login_url: str | None,
    region: str | None,
    extra_config: dict | None,
) -> EnvironmentConnection:
    connection = get_or_create_connection(db, environment, provider, created_by)
    connection.sso_login_url = sso_login_url
    connection.region = region
    connection.extra_config = extra_config
    db.commit()
    db.refresh(connection)
    return connection
