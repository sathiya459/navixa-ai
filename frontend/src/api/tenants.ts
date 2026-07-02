import { apiClient } from "./client";
import type {
  AvailableAccount,
  CloudAuthMode,
  CloudProvider,
  Scope,
  ScopeType,
  Tenant,
} from "./types";

export interface TenantCreatePayload {
  provider: CloudProvider;
  tenant_name: string;
  external_tenant_id: string;
  sso_login_url?: string | null;
  region_info?: Record<string, unknown> | null;
  auth_mode?: CloudAuthMode;
  app_registration_client_id?: string | null;
  app_registration_tenant_id?: string | null;
  app_registration_redirect_uri?: string | null;
}

export interface ScopeCreatePayload {
  scope_type: ScopeType;
  external_scope_id: string;
  display_name: string;
}

export async function listTenants(provider?: CloudProvider): Promise<Tenant[]> {
  const { data } = await apiClient.get<Tenant[]>("/tenants", { params: { provider } });
  return data;
}

export async function createTenant(payload: TenantCreatePayload): Promise<Tenant> {
  const { data } = await apiClient.post<Tenant>("/tenants", payload);
  return data;
}

export async function deleteTenant(tenantId: string): Promise<void> {
  await apiClient.delete(`/tenants/${tenantId}`);
}

export async function listScopes(tenantId: string): Promise<Scope[]> {
  const { data } = await apiClient.get<Scope[]>(`/tenants/${tenantId}/scopes`);
  return data;
}

export async function createScope(tenantId: string, payload: ScopeCreatePayload): Promise<Scope> {
  const { data } = await apiClient.post<Scope>(`/tenants/${tenantId}/scopes`, payload);
  return data;
}

export async function getAvailableAccounts(tenantId: string): Promise<AvailableAccount[]> {
  const { data } = await apiClient.get<AvailableAccount[]>(
    `/tenants/${tenantId}/available-accounts`,
  );
  return data;
}
