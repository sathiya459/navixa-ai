import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditJobCreate(BaseModel):
    tenant_id: uuid.UUID
    scope_ids: list[uuid.UUID]
    hub_selection: list[str] | None = None


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


class JobStatusResponse(BaseModel):
    status: str
    scopes: list[ScopeStatusResponse]


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
