# collectors — NAVIXA Discover

Per-cloud-provider async collection of raw network inventory, normalized into NAVIXA's common resource model.

## Files

- `base.py` — `CollectionResult` dataclass shared by all provider collectors.
- `discover_service.py` — persists per-resource-type collection status.
- `job_service.py` — creates and manages `AuditJob` records.
- `normalization.py` — maps raw per-provider API shapes into the common `NetworkResource` model.
- `retry.py` — backoff/throttle handling for cloud API calls.
- `delegated_auth_errors.py` — builds structured 409 responses when a cloud SSO session needs re-auth (popup flow for AWS, device code for Azure).
- `aws/`, `azure/`, `gcp/`, `oci/` — per-provider subpackages, each with an `orchestrator.py`/`client.py`.

## Notes

Two auth modes feed collectors: static root credentials (`tenant_registry/connection_service.py`) and per-user delegated cloud SSO sessions (`auth/token_encryption.py`, `auth/pkce_store.py`). `config/rate_limits.py` caps per-provider/per-resource-type concurrency. Orchestration across scopes/resource types happens in `workers/tasks.py` (`run_discovery` Celery task).
