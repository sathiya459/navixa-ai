export type CloudProvider = "aws" | "azure" | "gcp" | "oci";
export type ScopeType = "account" | "subscription" | "project" | "compartment";
export type UserRole = "admin" | "reader";
export type CloudAuthMode = "delegated" | "app_only";
export type Environment = "dev" | "prod";

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  roles: UserRole[];
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface Tenant {
  id: string;
  provider: CloudProvider;
  environment: Environment;
  tenant_name: string;
  external_tenant_id: string;
  region_info: Record<string, unknown> | null;
  auth_mode: CloudAuthMode;
  connection_id: string | null;
  app_registration_client_id: string | null;
  app_registration_tenant_id: string | null;
  app_registration_redirect_uri: string | null;
}

export interface EnvironmentConnection {
  id: string;
  environment: Environment;
  provider: CloudProvider;
  name: string;
  sso_login_url: string | null;
  region: string | null;
  connected: boolean;
}

export interface Scope {
  id: string;
  tenant_id: string;
  scope_type: ScopeType;
  external_scope_id: string;
  display_name: string;
  is_active: boolean;
}

export interface AvailableAccount {
  external_id: string;
  display_name: string;
  already_added: boolean;
}

export interface AvailableTenant {
  tenant_id: string;
  display_name: string;
  already_added: boolean;
}

export type AuditJobStatus =
  | "queued"
  | "discovering"
  | "graphing"
  | "validating"
  | "pathfinding"
  | "analyzing"
  | "reporting"
  | "completed"
  | "failed"
  | "partial";

export interface AuditJob {
  id: string;
  tenant_id: string;
  status: AuditJobStatus;
  created_at: string;
}

export interface AuditJobListItem {
  id: string;
  tenant_id: string;
  tenant_name: string;
  status: AuditJobStatus;
  created_at: string;
  scope_count: number;
  hub_selection: string[] | null;
}

export interface ResourceStatus {
  resource_type: string;
  status: "success" | "partial" | "failed";
  items_collected: number;
  error_detail: string | null;
}

export interface ScopeStatus {
  scope_id: string;
  status: string;
  resource_statuses: ResourceStatus[];
  resource_types_expected: number;
  resource_types_completed: number;
  items_collected: number;
}

export interface JobStatus {
  status: AuditJobStatus;
  scopes: ScopeStatus[];
  resource_types_expected: number;
  resource_types_completed: number;
  items_collected: number;
  percent_complete: number;
}

export interface NetworkResource {
  id: string;
  resource_type: string;
  provider: CloudProvider;
  native_id: string;
  name: string | null;
  attributes: Record<string, unknown>;
  collected_at: string;
}

export type FindingSeverity = "critical" | "high" | "medium" | "low" | "informational";
export type AnalysisMode = "rule_engine" | "ai";
export type AIProviderName = "claude" | "openai" | "azure_openai" | "gemini" | "bedrock";

export interface AIProviderStatus {
  provider: AIProviderName;
  available: boolean;
  configured: boolean;
}

export interface Finding {
  id: string;
  audit_job_id: string;
  module: "validate" | "pathfinder" | "ai_analysis";
  finding_type: string;
  severity: FindingSeverity;
  title: string;
  description: string;
  affected_resource_ids: string[];
  status: "open" | "acknowledged" | "resolved" | "false_positive";
  created_at: string;
}

export type InsightType = "root_cause" | "recommendation" | "exec_summary" | "topology_explanation";

export interface AIInsight {
  id: string;
  audit_job_id: string;
  finding_id: string | null;
  insight_type: InsightType;
  ai_provider: AIProviderName;
  content: string;
  created_at: string;
}

export interface GraphNode {
  id: string;
  labels: string[];
  properties: Record<string, unknown>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
}

export interface Topology {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface DiscoveredResource {
  id: string;
  provider: CloudProvider;
  resource_type: string;
  native_id: string;
  name: string | null;
  attributes: Record<string, unknown>;
  collected_at: string;
  audit_job_id: string;
  tenant_id: string;
  tenant_name: string;
  scope_id: string;
  scope_type: ScopeType;
  scope_display_name: string;
}
