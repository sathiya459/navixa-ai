import { apiClient } from "./client";
import type { AuditJob, AuditJobListItem, JobStatus, NetworkResource } from "./types";

export async function createAuditJob(
  tenantId: string,
  scopeIds: string[],
  hubSelection?: string[],
): Promise<AuditJob> {
  const { data } = await apiClient.post<AuditJob>("/discover/jobs", {
    tenant_id: tenantId,
    scope_ids: scopeIds,
    hub_selection: hubSelection,
  });
  return data;
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const { data } = await apiClient.get<JobStatus>(`/discover/jobs/${jobId}/status`);
  return data;
}

export async function listAuditJobs(tenantId?: string): Promise<AuditJobListItem[]> {
  const { data } = await apiClient.get<AuditJobListItem[]>("/discover/jobs", {
    params: tenantId ? { tenant_id: tenantId } : undefined,
  });
  return data;
}

export async function deleteAuditJob(jobId: string): Promise<void> {
  await apiClient.delete(`/discover/jobs/${jobId}`);
}

export async function getJobResources(
  jobId: string,
  params?: { resource_type?: string; scope_id?: string },
): Promise<NetworkResource[]> {
  const { data } = await apiClient.get<NetworkResource[]>(`/discover/jobs/${jobId}/resources`, {
    params,
  });
  return data;
}
