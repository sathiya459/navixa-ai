import uuid

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPKMixin

FindingModule = Enum("validate", "pathfinder", name="finding_module")
FindingSeverity = Enum("critical", "high", "medium", "low", "informational", name="finding_severity")
FindingStatus = Enum("open", "acknowledged", "resolved", "false_positive", name="finding_status")


class Finding(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "findings"

    audit_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audit_jobs.id", ondelete="CASCADE"), nullable=False
    )
    module: Mapped[str] = mapped_column(FindingModule, nullable=False)
    finding_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(FindingSeverity, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    affected_resource_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(FindingStatus, default="open", nullable=False)
