export type CloudProvider = "aws" | "azure" | "gcp" | "oci";
export type ScopeType = "account" | "subscription" | "project" | "compartment";
export type UserRole = "admin" | "auditor" | "viewer";

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
  tenant_name: string;
  external_tenant_id: string;
  sso_login_url: string | null;
  region_info: Record<string, unknown> | null;
}

export interface Scope {
  id: string;
  tenant_id: string;
  scope_type: ScopeType;
  external_scope_id: string;
  display_name: string;
  is_active: boolean;
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
}

export interface JobStatus {
  status: AuditJobStatus;
  scopes: ScopeStatus[];
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

export interface Finding {
  id: string;
  audit_job_id: string;
  module: "validate" | "pathfinder";
  finding_type: string;
  severity: FindingSeverity;
  title: string;
  description: string;
  affected_resource_ids: string[];
  status: "open" | "acknowledged" | "resolved" | "false_positive";
  created_at: string;
}
