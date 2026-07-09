import { apiClient } from "./client";
import type { Topology } from "./types";

export async function getJobTopology(jobId: string): Promise<Topology> {
  const { data } = await apiClient.get<Topology>(`/graph/jobs/${jobId}/topology`);
  return data;
}
