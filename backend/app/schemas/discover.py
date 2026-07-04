import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditJobCreate(BaseModel):
    tenant_id: uuid.UUID
    scope_ids: list[uuid.UUID]
    hub_selection: list[str] | None = None
    resource_types: list[str] | None = None


class AuditJobResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ResourceStatusResponse(BaseModel):
    resource_type: str
    status: str
    items_collected: int
    error_detail: str | None

    model_config = {"from_attributes": True}


class ScopeStatusResponse(BaseModel):
    scope_id: uuid.UUID
    status: str
    resource_statuses: list[ResourceStatusResponse]
    # Resource types this scope is expected to collect vs. how many have
    # reported a status so far, plus total items found across all of
    # them - lets the UI show "3 of 6 resource types collected (48
    # resources found)" while the job is still running, not just after
    # the whole scope finishes.
    resource_types_expected: int
    resource_types_completed: int
    items_collected: int


class JobStatusResponse(BaseModel):
    status: str
    scopes: list[ScopeStatusResponse]
    resource_types_expected: int
    resource_types_completed: int
    items_collected: int
    percent_complete: int


class AuditJobListItem(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_name: str
    status: str
    created_at: datetime
    scope_count: int

    model_config = {"from_attributes": True}


class NetworkResourceResponse(BaseModel):
    id: uuid.UUID
    resource_type: str
    provider: str
    native_id: str
    name: str | None
    attributes: dict[str, Any]
    collected_at: datetime

    model_config = {"from_attributes": True}
