import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, model_validator

AnalysisMode = Literal["rule_engine", "ai"]
AIProviderName = Literal["claude", "openai", "azure_openai", "gemini", "bedrock"]


class ValidateRunRequest(BaseModel):
    hub_ids: list[str]
    analysis_mode: AnalysisMode = "rule_engine"
    provider: AIProviderName | None = None

    @model_validator(mode="after")
    def _require_provider_for_ai_mode(self) -> "ValidateRunRequest":
        if self.analysis_mode == "ai" and self.provider is None:
            raise ValueError("provider is required when analysis_mode is 'ai'")
        return self


class FindingResponse(BaseModel):
    id: uuid.UUID
    audit_job_id: uuid.UUID
    module: str
    finding_type: str
    severity: str
    title: str
    description: str
    affected_resource_ids: list[str]
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
