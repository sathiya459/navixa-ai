import { apiClient } from "./client";
import type { Finding } from "./types";

export async function runValidation(jobId: string, hubIds: string[]): Promise<{ status: string }> {
  const { data } = await apiClient.post<{ status: string }>(`/validate/jobs/${jobId}/run`, {
    hub_ids: hubIds,
  });
  return data;
}

export async function getFindings(
  jobId: string,
  params?: { severity?: string; finding_type?: string },
): Promise<Finding[]> {
  const { data } = await apiClient.get<Finding[]>(`/validate/jobs/${jobId}/results`, { params });
  return data;
}
