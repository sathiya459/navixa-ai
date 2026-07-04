import uuid
from typing import Literal

from pydantic import BaseModel

CloudProviderLiteral = Literal["aws", "azure", "gcp", "oci"]
ScopeTypeLiteral = Literal["account", "subscription", "project", "compartment"]
CloudAuthModeLiteral = Literal["delegated", "app_only"]
EnvironmentLiteral = Literal["dev", "prod"]


class TenantCreate(BaseModel):
    provider: CloudProviderLiteral
    environment: EnvironmentLiteral = "dev"
    tenant_name: str
    external_tenant_id: str
    region_info: dict | None = None
    auth_mode: CloudAuthModeLiteral = "delegated"
    connection_id: uuid.UUID | None = None
    app_registration_client_id: str | None = None
    app_registration_tenant_id: str | None = None
    app_registration_redirect_uri: str | None = None


class TenantUpdate(BaseModel):
    tenant_name: str | None = None
    region_info: dict | None = None
    auth_mode: CloudAuthModeLiteral | None = None
    app_registration_client_id: str | None = None
    app_registration_tenant_id: str | None = None
    app_registration_redirect_uri: str | None = None


class TenantResponse(BaseModel):
    id: uuid.UUID
    provider: CloudProviderLiteral
    environment: EnvironmentLiteral
    tenant_name: str
    external_tenant_id: str
    region_info: dict | None
    auth_mode: CloudAuthModeLiteral
    connection_id: uuid.UUID | None
    app_registration_client_id: str | None
    app_registration_tenant_id: str | None
    app_registration_redirect_uri: str | None

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


class AvailableAccountResponse(BaseModel):
    external_id: str
    display_name: str
    already_added: bool


class EnvironmentConnectionResponse(BaseModel):
    id: uuid.UUID
    environment: EnvironmentLiteral
    provider: CloudProviderLiteral
    name: str
    sso_login_url: str | None
    region: str | None
    connected: bool

    model_config = {"from_attributes": True}


class ConnectionCreate(BaseModel):
    name: str


class ConnectionUpdate(BaseModel):
    sso_login_url: str | None = None
    region: str | None = None
    extra_config: dict | None = None


class ConnectionRename(BaseModel):
    name: str


class AvailableTenantResponse(BaseModel):
    tenant_id: str
    display_name: str
    already_added: bool


class ImportTenantsRequest(BaseModel):
    tenant_ids: list[str]
