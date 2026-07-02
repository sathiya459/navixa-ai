import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ScheduledDiscoveryCreate(BaseModel):
    tenant_id: uuid.UUID
    scope_ids: list[uuid.UUID]
    interval_minutes: int
    hub_selection: list[str] | None = None


class ScheduledDiscoveryResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    scope_ids: list[str]
    interval_minutes: int
    hub_selection: list[str] | None
    is_active: bool
    last_run_at: datetime | None
    next_run_at: datetime

    model_config = {"from_attributes": True}


class ResourceChangeResponse(BaseModel):
    id: uuid.UUID
    audit_job_id: uuid.UUID
    compared_to_audit_job_id: uuid.UUID
    resource_type: str
    native_id: str
    change_type: str
    previous_attributes: dict[str, Any] | None
    current_attributes: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}
