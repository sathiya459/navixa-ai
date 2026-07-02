import uuid
from datetime import datetime

from pydantic import BaseModel


class ValidateRunRequest(BaseModel):
    hub_ids: list[str]


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
