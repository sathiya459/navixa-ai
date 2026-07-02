import uuid

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPKMixin

ChangeType = Enum("added", "removed", "modified", name="resource_change_type")


class ResourceChange(Base, UUIDPKMixin, TimestampMixin):
    """NAVIXA Watch groundwork: one detected drift entry between two audit
    jobs for the same tenant/scope (Section 2 "Change detection / Drift
    analysis"). Alert generation on top of these rows is future scope, not
    implemented here.
    """

    __tablename__ = "resource_changes"

    audit_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audit_jobs.id", ondelete="CASCADE"), nullable=False
    )
    compared_to_audit_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audit_jobs.id", ondelete="CASCADE"), nullable=False
    )
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    native_id: Mapped[str] = mapped_column(String(255), nullable=False)
    change_type: Mapped[str] = mapped_column(ChangeType, nullable=False)
    previous_attributes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    current_attributes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
