import { apiClient } from "./client";
import type {
  AvailableAccount,
  CloudAuthMode,
  CloudProvider,
  Environment,
  EnvironmentConnection,
  Scope,
  ScopeType,
  Tenant,
} from "./types";

export interface TenantCreatePayload {
  provider: CloudProvider;
  environment?: Environment;
  tenant_name: string;
  external_tenant_id: string;
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

export interface ConnectionUpsertPayload {
  sso_login_url?: string | null;
  region?: string | null;
  extra_config?: Record<string, unknown> | null;
}

export async function listTenants(
  provider?: CloudProvider,
  environment?: Environment,
): Promise<Tenant[]> {
  const { data } = await apiClient.get<Tenant[]>("/tenants", { params: { provider, environment } });
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

export async function listConnections(environment: Environment): Promise<EnvironmentConnection[]> {
  const { data } = await apiClient.get<EnvironmentConnection[]>("/connections", {
    params: { environment },
  });
  return data;
}

export async function upsertConnection(
  environment: Environment,
  provider: CloudProvider,
  payload: ConnectionUpsertPayload,
): Promise<EnvironmentConnection> {
  const { data } = await apiClient.put<EnvironmentConnection>(
    `/connections/${environment}/${provider}`,
    payload,
  );
  return data;
}
