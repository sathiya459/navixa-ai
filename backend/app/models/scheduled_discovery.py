import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPKMixin


class ScheduledDiscovery(Base, UUIDPKMixin, TimestampMixin):
    """NAVIXA Watch groundwork (Section 2, Phase 5): a recurring discovery
    schedule for a tenant/scope selection. A periodic Celery task
    (check_scheduled_discoveries) polls for due schedules rather than
    registering one dynamic Celery Beat entry per schedule, since Celery
    Beat's static schedule is code-defined, not DB-driven, without an
    additional scheduler backend (e.g. django-celery-beat) that this
    platform doesn't otherwise depend on.
    """

    __tablename__ = "scheduled_discoveries"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cloud_tenants.id", ondelete="CASCADE"), nullable=False
    )
    scope_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    hub_selection: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
