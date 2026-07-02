import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPKMixin

AuditJobStatus = Enum(
    "queued",
    "discovering",
    "graphing",
    "validating",
    "pathfinding",
    "analyzing",
    "reporting",
    "completed",
    "failed",
    "partial",
    name="audit_job_status",
)

ScopeJobStatus = Enum("pending", "running", "success", "partial", "failed", name="scope_job_status")

ResourceCollectionStatus = Enum(
    "success", "partial", "failed", name="resource_collection_status"
)


class AuditJob(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "audit_jobs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cloud_tenants.id"), nullable=False
    )
    initiated_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(AuditJobStatus, default="queued", nullable=False)
    hub_selection: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    started_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    job_scopes: Mapped[list["AuditJobScope"]] = relationship(
        back_populates="audit_job", cascade="all, delete-orphan"
    )


class AuditJobScope(Base, UUIDPKMixin):
    __tablename__ = "audit_job_scopes"

    audit_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audit_jobs.id", ondelete="CASCADE"), nullable=False
    )
    cloud_scope_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cloud_scopes.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(ScopeJobStatus, default="pending", nullable=False)
    started_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)

    audit_job: Mapped[AuditJob] = relationship(back_populates="job_scopes")
    resource_statuses: Mapped[list["ResourceCollectionStatusRow"]] = relationship(
        back_populates="audit_job_scope", cascade="all, delete-orphan"
    )


class ResourceCollectionStatusRow(Base, UUIDPKMixin):
    __tablename__ = "resource_collection_status"

    audit_job_scope_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audit_job_scopes.id", ondelete="CASCADE"), nullable=False
    )
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(ResourceCollectionStatus, nullable=False)
    error_detail: Mapped[str | None] = mapped_column(String, nullable=True)
    items_collected: Mapped[int] = mapped_column(default=0, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)

    audit_job_scope: Mapped[AuditJobScope] = relationship(back_populates="resource_statuses")
