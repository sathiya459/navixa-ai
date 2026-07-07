import { apiClient } from "./client";
import type { CloudProvider, DiscoveredResource } from "./types";

export interface DiscoveredResourceFilters {
  provider?: CloudProvider;
  tenant_id?: string;
  scope_id?: string;
  resource_type?: string;
}

export async function getDiscoveredResources(
  filters: DiscoveredResourceFilters = {},
): Promise<DiscoveredResource[]> {
  const { data } = await apiClient.get<DiscoveredResource[]>("/reports/resources", {
    params: filters,
  });
  return data;
}

/** Triggers a browser download of the filtered inventory as CSV, reusing
 * the authenticated apiClient (a plain <a href> can't attach the bearer
 * token) then handing the blob off via an in-memory object URL. */
export async function exportDiscoveredResources(
  filters: DiscoveredResourceFilters = {},
): Promise<void> {
  const response = await apiClient.get("/reports/resources/export", {
    params: filters,
    responseType: "blob",
  });
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = url;
  link.download = "navixa-discovered-resources.csv";
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
