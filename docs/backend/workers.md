# workers

Celery task orchestration.

## Files

- `celery_app.py` — Celery app configured with Redis broker/backend.
- `tasks.py` — `run_discovery` task: orchestrates async, concurrent per-scope/per-resource-type Discover collection, then syncs results into `graph_engine/`.
