import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UUIDPKMixin

ResourceType = Enum(
    "network",
    "subnet",
    "route_table",
    "route",
    "gateway",
    "firewall",
    "security_group",
    "network_interface",
    "load_balancer",
    "endpoint",
    "compute_instance",
    "peering_connection",
    "public_ip",
    name="network_resource_type",
)


class NetworkResource(Base, UUIDPKMixin):
    __tablename__ = "network_resources"

    audit_job_scope_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audit_job_scopes.id", ondelete="CASCADE"), nullable=False
    )
    resource_type: Mapped[str] = mapped_column(ResourceType, nullable=False)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    native_id: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attributes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    graph_node_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
