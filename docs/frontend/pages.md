# pages

One component per route.

## Files

- `LoginPage` — local + SSO login entry.
- `SsoCallbackPage` — handles SSO popup completion.
- `DashboardHomePage` — landing dashboard.
- `TenantsPage` — cloud tenant management.
- `AuditJobsPage` — list/create discovery jobs.
- `AuditWorkflowPage` — admin-only job creation flow.
- `ConnectionsPage` — admin-only cloud connection/delegated-auth management.
- `TopologyPage` — renders a `reactflow` hub-and-spoke diagram of discovered network resources for a job, via the co-located helper `topology/buildTopology.ts` (transforms `NetworkResource[]` into ReactFlow `nodes`/`edges`).
