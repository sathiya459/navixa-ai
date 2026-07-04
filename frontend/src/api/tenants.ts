import { apiClient } from "./client";
import type {
  AvailableAccount,
  AvailableTenant,
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
  connection_id?: string | null;
  app_registration_client_id?: string | null;
  app_registration_tenant_id?: string | null;
  app_registration_redirect_uri?: string | null;
}

export interface ScopeCreatePayload {
  scope_type: ScopeType;
  external_scope_id: string;
  display_name: string;
}

export interface ConnectionUpdatePayload {
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

export async function createConnection(
  environment: Environment,
  provider: CloudProvider,
  name: string,
): Promise<EnvironmentConnection> {
  const { data } = await apiClient.post<EnvironmentConnection>(
    `/connections/${environment}/${provider}`,
    { name },
  );
  return data;
}

export async function updateConnectionConfig(
  environment: Environment,
  connectionId: string,
  payload: ConnectionUpdatePayload,
): Promise<EnvironmentConnection> {
  const { data } = await apiClient.put<EnvironmentConnection>(
    `/connections/${environment}/${connectionId}`,
    payload,
  );
  return data;
}

export async function deleteConnection(environment: Environment, connectionId: string): Promise<void> {
  await apiClient.delete(`/connections/${environment}/${connectionId}`);
}

// Both AWS and Azure connections sign in via the OAuth 2.0 Device
// Authorization Grant - see backend/app/api/v1/delegated_auth.py's module
// docstring for why a popup+redirect flow can't work against a real IAM
// Identity Center instance.
export type DeviceFlowProvider = "aws" | "azure";

export interface DeviceFlowStart {
  flow_id: string;
  user_code: string;
  verification_uri: string;
  expires_in: number;
  interval: number;
  message: string | null;
}

export type DeviceFlowPollStatus = "pending" | "complete" | "error" | "expired";

export interface DeviceFlowPoll {
  status: DeviceFlowPollStatus;
  message?: string;
}

export async function startDeviceFlow(
  environment: Environment,
  connectionId: string,
  provider: DeviceFlowProvider,
): Promise<DeviceFlowStart> {
  const { data } = await apiClient.post<DeviceFlowStart>(
    `/connections/${environment}/${connectionId}/${provider}/delegated-auth/device/start`,
  );
  return data;
}

export async function pollDeviceFlow(
  environment: Environment,
  connectionId: string,
  provider: DeviceFlowProvider,
  flowId: string,
): Promise<DeviceFlowPoll> {
  const { data } = await apiClient.post<DeviceFlowPoll>(
    `/connections/${environment}/${connectionId}/${provider}/delegated-auth/device/poll`,
    { flow_id: flowId },
  );
  return data;
}

export type TenantImportProvider = "aws" | "azure";

export async function getAvailableTenants(
  environment: Environment,
  connectionId: string,
  provider: TenantImportProvider,
): Promise<AvailableTenant[]> {
  const { data } = await apiClient.get<AvailableTenant[]>(
    `/connections/${environment}/${connectionId}/${provider}/available-tenants`,
  );
  return data;
}

export async function importTenants(
  environment: Environment,
  connectionId: string,
  provider: TenantImportProvider,
  tenantIds: string[],
): Promise<Tenant[]> {
  const { data } = await apiClient.post<Tenant[]>(
    `/connections/${environment}/${connectionId}/${provider}/import-tenants`,
    { tenant_ids: tenantIds },
  );
  return data;
}
