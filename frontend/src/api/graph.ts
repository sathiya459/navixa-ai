import { apiClient } from "./client";
import type { Topology } from "./types";

export async function getJobTopology(jobId: string): Promise<Topology> {
  const { data } = await apiClient.get<Topology>(`/graph/jobs/${jobId}/topology`);
  return data;
}

export async function syncJobTopology(jobId: string): Promise<Topology> {
  const { data } = await apiClient.post<Topology>(`/graph/jobs/${jobId}/sync`);
  return data;
}
