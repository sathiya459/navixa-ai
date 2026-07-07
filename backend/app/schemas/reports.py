import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

ReportTypeLiteral = Literal["executive", "technical", "compliance"]
ReportFormatLiteral = Literal["pdf", "excel", "html"]


class ReportGenerateRequest(BaseModel):
    report_type: ReportTypeLiteral
    format: ReportFormatLiteral


class ReportResponse(BaseModel):
    id: uuid.UUID
    audit_job_id: uuid.UUID
    report_type: ReportTypeLiteral
    format: ReportFormatLiteral
    status: Literal["queued", "completed", "failed"]
    created_at: datetime

    model_config = {"from_attributes": True}


class DiscoveredResourceResponse(BaseModel):
    """One resource from the current discovered inventory (see
    `app/reports/inventory.py` for what "current" means)."""

    id: uuid.UUID
    provider: str
    resource_type: str
    native_id: str
    name: str | None
    attributes: dict[str, Any]
    collected_at: datetime
    audit_job_id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_name: str
    scope_id: uuid.UUID
    scope_type: str
    scope_display_name: str

    model_config = {"from_attributes": True}
