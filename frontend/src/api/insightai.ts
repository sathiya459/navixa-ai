import { apiClient } from "./client";
import type { AIProviderStatus } from "./types";

export async function listAIProviders(): Promise<AIProviderStatus[]> {
  const { data } = await apiClient.get<AIProviderStatus[]>("/insightai/providers");
  return data;
}
