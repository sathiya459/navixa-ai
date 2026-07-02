import { apiClient } from "./client";
import type { AIProviderName, AnalysisMode, Finding } from "./types";

export async function runValidation(
  jobId: string,
  hubIds: string[],
  analysisMode: AnalysisMode = "rule_engine",
  provider?: AIProviderName,
): Promise<{ status: string; analysis_mode: AnalysisMode }> {
  const { data } = await apiClient.post<{ status: string; analysis_mode: AnalysisMode }>(
    `/validate/jobs/${jobId}/run`,
    {
      hub_ids: hubIds,
      analysis_mode: analysisMode,
      provider,
    },
  );
  return data;
}

export async function getFindings(
  jobId: string,
  params?: { severity?: string; finding_type?: string },
): Promise<Finding[]> {
  const { data } = await apiClient.get<Finding[]>(`/validate/jobs/${jobId}/results`, { params });
  return data;
}
