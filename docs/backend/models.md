# models

SQLAlchemy ORM models, one file per entity.

## Files

- `user.py` — application users.
- `role.py` — RBAC roles (admin/reader).
- `cloud_tenant.py` — registered cloud tenants and their scopes.
- `environment_connection.py` — delegated SSO sessions per environment/provider.
- `audit_job.py` — a Discover run: job metadata and scope.
- `network_resource.py` — normalized cloud inventory records.
- `resource_change.py` — Watch diffs between snapshots.
- `finding.py` — Validate/Pathfinder findings.
- `ai_insight.py` — InsightAI outputs.
- `report.py` — generated report records.
- `scheduled_discovery.py` — Watch schedule configuration.
