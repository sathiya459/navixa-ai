import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

InsightType = Literal["root_cause", "recommendation", "exec_summary", "topology_explanation"]
ProviderName = Literal["claude", "openai", "azure_openai", "gemini", "bedrock"]


class InsightGenerateRequest(BaseModel):
    provider: ProviderName
    insight_types: list[InsightType]


class AIInsightResponse(BaseModel):
    id: uuid.UUID
    audit_job_id: uuid.UUID
    finding_id: uuid.UUID | None
    insight_type: InsightType
    ai_provider: ProviderName
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ProviderStatus(BaseModel):
    provider: str
    available: bool
    configured: bool
