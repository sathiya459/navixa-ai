import uuid

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPKMixin

CloudProvider = Enum("aws", "azure", "gcp", "oci", name="cloud_provider")


class CloudTenant(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "cloud_tenants"

    provider: Mapped[str] = mapped_column(CloudProvider, nullable=False)
    tenant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    external_tenant_id: Mapped[str] = mapped_column(String(255), nullable=False)
    sso_login_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    region_info: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    scopes: Mapped[list["CloudScope"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )


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
