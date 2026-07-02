import uuid

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPKMixin

ReportType = Enum("executive", "technical", "compliance", name="report_type")
ReportFormat = Enum("pdf", "excel", "html", name="report_format")
ReportStatus = Enum("queued", "completed", "failed", name="report_status")


class Report(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "reports"

    audit_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audit_jobs.id", ondelete="CASCADE"), nullable=False
    )
    report_type: Mapped[str] = mapped_column(ReportType, nullable=False)
    format: Mapped[str] = mapped_column(ReportFormat, nullable=False)
    status: Mapped[str] = mapped_column(ReportStatus, default="queued", nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    generated_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
