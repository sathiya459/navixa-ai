import uuid

import sqlalchemy as sa
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPKMixin
from app.models.cloud_tenant import CloudProvider, Environment


class EnvironmentConnection(Base, UUIDPKMixin, TimestampMixin):
    """One root-credential SSO connection per (environment, provider) -
    e.g. Dev+Azure is authenticated once (sathiya.moorthi@smcloudsec.in
    completing the delegated-auth popup), and that session is reused for
    every Dev-environment tenant/subscription of that provider, rather
    than one popup per tenant.
    """

    __tablename__ = "environment_connections"
    __table_args__ = (UniqueConstraint("environment", "provider", name="uq_env_connection"),)

    environment: Mapped[str] = mapped_column(Environment, nullable=False)
    provider: Mapped[str] = mapped_column(CloudProvider, nullable=False)
    sso_login_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    region: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Provider-specific extras that don't warrant their own column (e.g. an
    # Azure app registration client/tenant ID override for this
    # environment's connection).
    extra_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Encrypted (app/auth/token_encryption.py) session state: an MSAL
    # serialized token cache for Azure, or an AWS SSO OIDC client
    # registration + token for AWS. Never stored in plaintext.
    delegated_token_cache: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
