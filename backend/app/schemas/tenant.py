import uuid
from typing import Literal

from pydantic import BaseModel

CloudProviderLiteral = Literal["aws", "azure", "gcp", "oci"]
ScopeTypeLiteral = Literal["account", "subscription", "project", "compartment"]


class TenantCreate(BaseModel):
    provider: CloudProviderLiteral
    tenant_name: str
    external_tenant_id: str
    sso_login_url: str | None = None
    region_info: dict | None = None


class TenantUpdate(BaseModel):
    tenant_name: str | None = None
    sso_login_url: str | None = None
    region_info: dict | None = None


class TenantResponse(BaseModel):
    id: uuid.UUID
    provider: CloudProviderLiteral
    tenant_name: str
    external_tenant_id: str
    sso_login_url: str | None
    region_info: dict | None

    model_config = {"from_attributes": True}


class ScopeCreate(BaseModel):
    scope_type: ScopeTypeLiteral
    external_scope_id: str
    display_name: str


class ScopeResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    scope_type: ScopeTypeLiteral
    external_scope_id: str
    display_name: str
    is_active: bool

    model_config = {"from_attributes": True}
