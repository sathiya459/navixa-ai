# workers

Celery task orchestration.

## Files

- `celery_app.py` — Celery app configured with Redis broker/backend. No beat schedule — all Discover runs are triggered on demand via the API (NAVIXA Watch's scheduled/recurring discovery has been removed).
- `tasks.py` — `run_discovery` task: orchestrates async, concurrent per-scope/per-resource-type Discover collection for a single on-demand audit job. Topology/deviation detection read from Postgres live afterward (`graph_engine/topology_service.py`), no separate sync step needed.
