import uuid

import sqlalchemy as sa
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPKMixin
from app.models.cloud_tenant import CloudProvider, Environment


class EnvironmentConnection(Base, UUIDPKMixin, TimestampMixin):
    """A named root-credential SSO connection for (environment, provider) -
    e.g. Dev+Azure may have several connections, one per signed-in account
    (sathiya.moorthi@smcloudsec.in, example2@xyz.com, ...), each
    authenticated independently via its own delegated-auth popup/device
    flow. Every tenant/subscription discovered through a connection is
    tied back to it (CloudTenant.connection_id) so NAVIXA Discover always
    uses the right account's credentials.
    """

    __tablename__ = "environment_connections"
    __table_args__ = (
        UniqueConstraint("environment", "provider", "name", name="uq_env_connection_name"),
    )

    environment: Mapped[str] = mapped_column(Environment, nullable=False)
    provider: Mapped[str] = mapped_column(CloudProvider, nullable=False)
    # User-facing label - typically the signed-in account's email/UPN,
    # auto-filled from the ID token after a successful Azure device-code
    # login and editable thereafter. Required at creation time for AWS
    # since there's no token claim to backfill it from.
    name: Mapped[str] = mapped_column(String(255), nullable=False)
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
