import { apiClient } from "./client";
import type { CloudProvider, Scope, Tenant } from "./types";

export async function listTenants(provider?: CloudProvider): Promise<Tenant[]> {
  const { data } = await apiClient.get<Tenant[]>("/tenants", { params: { provider } });
  return data;
}

export async function listScopes(tenantId: string): Promise<Scope[]> {
  const { data } = await apiClient.get<Scope[]>(`/tenants/${tenantId}/scopes`);
  return data;
}
