import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.environment_connection import EnvironmentConnection

ALL_PROVIDERS = ("aws", "azure", "gcp", "oci")


class DuplicateConnectionNameError(Exception):
    pass


def get_connection_by_id(db: Session, connection_id: uuid.UUID) -> EnvironmentConnection | None:
    return db.get(EnvironmentConnection, connection_id)


def list_connections(db: Session, environment: str) -> list[EnvironmentConnection]:
    return (
        db.query(EnvironmentConnection)
        .filter(EnvironmentConnection.environment == environment)
        .order_by(EnvironmentConnection.provider, EnvironmentConnection.name)
        .all()
    )


def create_connection(
    db: Session, environment: str, provider: str, name: str, created_by: uuid.UUID
) -> EnvironmentConnection:
    connection = EnvironmentConnection(
        environment=environment, provider=provider, name=name, created_by=created_by
    )
    db.add(connection)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateConnectionNameError(
            f"A {provider} connection named '{name}' already exists for {environment}."
        ) from exc
    db.refresh(connection)
    return connection


def update_connection_config(
    db: Session,
    connection_id: uuid.UUID,
    sso_login_url: str | None,
    region: str | None,
    extra_config: dict | None,
) -> EnvironmentConnection | None:
    connection = get_connection_by_id(db, connection_id)
    if connection is None:
        return None
    connection.sso_login_url = sso_login_url
    connection.region = region
    connection.extra_config = extra_config
    db.commit()
    db.refresh(connection)
    return connection


def rename_connection(db: Session, connection_id: uuid.UUID, name: str) -> EnvironmentConnection | None:
    connection = get_connection_by_id(db, connection_id)
    if connection is None:
        return None
    connection.name = name
    db.commit()
    db.refresh(connection)
    return connection


def delete_connection(db: Session, connection_id: uuid.UUID) -> bool:
    connection = get_connection_by_id(db, connection_id)
    if connection is None:
        return False
    db.delete(connection)
    db.commit()
    return True
