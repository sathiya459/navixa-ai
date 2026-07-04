# pages

One component per route.

## Files

- `LoginPage` — local + SSO login entry.
- `SsoCallbackPage` — handles SSO popup completion.
- `DashboardHomePage` — landing dashboard.
- `TenantsPage` — cloud tenant management. "Add Tenant" opens `TenantImportDialog` (auto-populates from the provider's connection, for AWS and Azure) or a manual entry form (GCP/OCI, and either provider with no connection yet). `TenantImportDialog`'s copy differs per provider (`PROVIDER_IMPORT_COPY`): Azure's picker genuinely picks tenants, while AWS's picks accounts that get grouped as scopes under one auto-created tenant per connection.
- `AuditJobsPage` — list/create discovery jobs. Its `ProgressDialog` polls `GET /discover/jobs/{id}/status` every 2s and shows an overall `LinearProgress` bar ("N of M resource types collected — X resources found", % complete) plus a per-scope breakdown, live while the job is still running.
- `AuditWorkflowPage` — admin-only job creation flow. "Confirm Hub Selection" is always clickable, even with zero VPCs/VNets checked — a hub-and-spoke topology with no designated hub is a valid real-world state (e.g. a flat/mesh network), not an incomplete form; `hub_ids: []` is accepted by `POST /validate` and just yields no hub-bypass-routing findings.
- `ConnectionsPage` — admin-only cloud connection/delegated-auth management.
- `TopologyPage` — renders a `reactflow` hub-and-spoke diagram of discovered network resources for a job, via the co-located helper `topology/buildTopology.ts` (transforms `NetworkResource[]` into ReactFlow `nodes`/`edges`).
