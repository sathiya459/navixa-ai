import uuid

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPKMixin

InsightType = Enum(
    "root_cause", "recommendation", "exec_summary", "topology_explanation", name="insight_type"
)
AIProviderName = Enum("claude", "openai", "azure_openai", "gemini", "bedrock", name="ai_provider_name")


class AIInsight(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "ai_insights"

    audit_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audit_jobs.id", ondelete="CASCADE"), nullable=False
    )
    finding_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=True
    )
    insight_type: Mapped[str] = mapped_column(InsightType, nullable=False)
    ai_provider: Mapped[str] = mapped_column(AIProviderName, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
