# api

The sole HTTP surface of the backend. Mounted in `backend/app/main.py` under the `/api/v1` prefix.

## Files

- `v1/router.py` — aggregates all sub-routers into `api_router`.
- `v1/auth.py` — local JWT login, Entra ID SSO endpoints.
- `v1/tenants.py` — cloud tenant CRUD.
- `v1/connections.py` — root-credential environment connections; also exposes the AWS/Azure tenant auto-discovery endpoints (`/{environment}/{connection_id}/{aws,azure}/available-tenants` + `/import-tenants`) backed by `tenant_registry/aws_import.py` and `azure_import.py`.
- `v1/delegated_auth.py` — delegated cloud-SSO popup/device-code flow.
- `v1/discover.py` — audit job creation and NAVIXA Discover resource fetch; `GET /jobs/{id}/status` also reports live collection progress (resource types expected/completed, items collected, percent complete) computed via `collectors/discover_service.py`'s `expected_resource_types()`.
- `v1/graph.py` — `GET /graph/jobs/{job_id}/topology`, computed live from Postgres by `graph_engine/topology_service.py`.
- `v1/validate.py` — NAVIXA Validate rule-engine/AI validation and findings.
- `v1/pathfinder.py` — NAVIXA Pathfinder internet exposure analysis.
- `v1/insightai.py` — NAVIXA InsightAI provider listing and insight generation.
- `v1/reports.py` — report generation/download, plus `GET /reports/resources` (JSON) and `GET /reports/resources/export` (CSV) for the cross-job discovered-resource inventory backing the frontend's Reports page (filterable by `provider`/`tenant_id`/`scope_id`/`resource_type`).

## Notes

One router module per backend feature area — each corresponds 1:1 with a module documented elsewhere in `docs/backend/`.
