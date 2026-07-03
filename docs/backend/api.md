# api

The sole HTTP surface of the backend. Mounted in `backend/app/main.py` under the `/api/v1` prefix.

## Files

- `v1/router.py` — aggregates all sub-routers into `api_router`.
- `v1/auth.py` — local JWT login, Entra ID SSO endpoints.
- `v1/tenants.py` — cloud tenant CRUD.
- `v1/connections.py` — root-credential environment connections.
- `v1/delegated_auth.py` — delegated cloud-SSO popup/device-code flow.
- `v1/discover.py` — audit job creation and NAVIXA Discover resource fetch.
- `v1/graph.py` — NAVIXA Graph read endpoints.
- `v1/validate.py` — NAVIXA Validate rule-engine/AI validation and findings.
- `v1/pathfinder.py` — NAVIXA Pathfinder internet exposure analysis.
- `v1/insightai.py` — NAVIXA InsightAI provider listing and insight generation.
- `v1/reports.py` — report generation/download.
- `v1/watch.py` — NAVIXA Watch scheduled discovery and change detection.

## Notes

One router module per backend feature area — each corresponds 1:1 with a module documented elsewhere in `docs/backend/`.
