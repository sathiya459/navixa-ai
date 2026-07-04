import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.environment_connection import EnvironmentConnection

CloudProvider = Enum("aws", "azure", "gcp", "oci", name="cloud_provider")

# Section 8a: which cloud-auth path NAVIXA Discover uses for this tenant.
# "delegated" authenticates via the environment's own root-credential SSO
# session (see EnvironmentConnection) - one popup login per environment,
# reused across every tenant in it; "app_only" uses an Entra ID App
# Registration (client credentials) for headless/scheduled runs.
CloudAuthMode = Enum("delegated", "app_only", name="cloud_auth_mode")

# Which deployment environment this tenant belongs to - scopes which
# EnvironmentConnection (root credential) is used for its cloud API calls,
# and who can see/manage it (Admins can switch environments; Readers
# always see Dev).
Environment = Enum("dev", "prod", name="tenant_environment")


class CloudTenant(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "cloud_tenants"

    provider: Mapped[str] = mapped_column(CloudProvider, nullable=False)
    environment: Mapped[str] = mapped_column(Environment, default="dev", nullable=False)
    tenant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    external_tenant_id: Mapped[str] = mapped_column(String(255), nullable=False)
    region_info: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    auth_mode: Mapped[str] = mapped_column(CloudAuthMode, default="delegated", nullable=False)
    # Non-sensitive App Registration metadata only (Section 9, app_only
    # mode) - the matching client secret lives in Secret Manager/Key Vault,
    # never here. Delegated mode's SSO details live on EnvironmentConnection
    # instead (one root credential per environment, not per tenant).
    app_registration_client_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    app_registration_tenant_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    app_registration_redirect_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Which named EnvironmentConnection (delegated mode) discovered/owns
    # this tenant - resolves credentials for Sync Accounts and Discover
    # runs. Nullable: app_only-mode tenants don't use a connection at all,
    # and pre-migration delegated tenants are backfilled from the single
    # connection that used to exist for their (environment, provider).
    connection_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("environment_connections.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    scopes: Mapped[list["CloudScope"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    connection: Mapped["EnvironmentConnection | None"] = relationship()


class CloudScope(Base, UUIDPKMixin):
    __tablename__ = "cloud_scopes"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cloud_tenants.id", ondelete="CASCADE"), nullable=False
    )
    scope_type: Mapped[str] = mapped_column(
        Enum("account", "subscription", "project", "compartment", name="cloud_scope_type"),
        nullable=False,
    )
    external_scope_id: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    tenant: Mapped[CloudTenant] = relationship(back_populates="scopes")
