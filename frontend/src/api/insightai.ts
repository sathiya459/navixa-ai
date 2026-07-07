import { apiClient } from "./client";
import type { AIInsight, AIProviderName, AIProviderStatus, InsightType } from "./types";

export async function listAIProviders(): Promise<AIProviderStatus[]> {
  const { data } = await apiClient.get<AIProviderStatus[]>("/insightai/providers");
  return data;
}

export async function generateInsights(
  jobId: string,
  provider: AIProviderName,
  insightTypes: InsightType[],
): Promise<{ status: string }> {
  const { data } = await apiClient.post<{ status: string }>(`/insightai/jobs/${jobId}/generate`, {
    provider,
    insight_types: insightTypes,
  });
  return data;
}

export async function getInsights(jobId: string, insightType?: InsightType): Promise<AIInsight[]> {
  const { data } = await apiClient.get<AIInsight[]>(`/insightai/jobs/${jobId}/insights`, {
    params: insightType ? { insight_type: insightType } : undefined,
  });
  return data;
}
