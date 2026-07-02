import uuid
from datetime import datetime
from typing import Literal

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
