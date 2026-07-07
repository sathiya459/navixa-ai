# collectors — NAVIXA Discover

Per-cloud-provider async collection of raw network inventory, normalized into NAVIXA's common resource model.

## Files

- `base.py` — `CollectionResult` dataclass shared by all provider collectors, plus `run_collectors_with_progress()`, the shared fan-out helper every orchestrator uses to run its resource-type collectors concurrently and report each one's result as soon as it completes (rather than only after the whole scope finishes).
- `discover_service.py` — persists per-resource-type collection status as each type completes (not in bulk at the end - see "Progress reporting" below), and exposes `expected_resource_types(provider, resource_types)` for computing "N of M collected" progress.
- `job_service.py` — creates and manages `AuditJob` records; `get_job_network_resources()` fetches a job's `NetworkResource` rows and is shared by the Celery Discover task's graph sync and the manual `POST /graph/jobs/{id}/sync` backfill endpoint. `list_audit_jobs()` also surfaces each job's persisted `hub_selection` (set once NAVIXA Validate has run) so the frontend can prefill hub selection without re-asking.
- `normalization.py` — maps raw per-provider API shapes into the common `NetworkResource` model.
- `retry.py` — backoff/throttle handling for cloud API calls.
- `delegated_auth_errors.py` — builds structured 409 responses when a cloud SSO session needs re-auth (popup flow for AWS, device code for Azure).
- `aws/`, `azure/`, `gcp/`, `oci/` — per-provider subpackages, each with an `orchestrator.py`/`client.py`. Each orchestrator exposes `expected_resource_types(...)` (the resource-type set it will run for a given filter) alongside its `discover_*_scope(...)` entrypoint.

## Notes

Two auth modes feed collectors: static root credentials (`tenant_registry/connection_service.py`) and per-user delegated cloud SSO sessions (`auth/token_encryption.py`, `auth/pkce_store.py`). `config/rate_limits.py` caps per-provider/per-resource-type concurrency, and also holds `CREDENTIAL_SETUP_TIMEOUT_SECONDS` (scope credential/session setup) and `AWS_COLLECTOR_CALL_TIMEOUT_SECONDS` (every individual AWS API call) - see "Timeouts" below. Orchestration across scopes/resource types happens in `workers/tasks.py` (`run_discovery` Celery task).

### Progress reporting

Each orchestrator's `discover_*_scope()` takes an optional `on_result` callback, invoked as each resource-type collector finishes. `discover_service.run_discovery_for_scope` uses this to commit a `ResourceCollectionStatusRow` immediately per completed type instead of waiting for `asyncio.gather` on the whole scope to resolve - this is what lets `GET /discover/jobs/{id}/status` report live "N of M resource types collected" / items-found progress while a job is still running, instead of showing nothing until the entire scope completes. A scope that hangs on credential/session setup (no per-type collector has started yet, so there's nothing to report) is bounded by `CREDENTIAL_SETUP_TIMEOUT_SECONDS` and surfaces as a failed `_credentials` pseudo-resource-type rather than blocking the job indefinitely.

Also note: an audit job's "stuck" resource-collection state can mean either of two very different things, both of which look identical from the UI:
1. The Celery worker process isn't running at all (the job sits queued forever) - check `celery -A app.workers.celery_app worker` is actually alive. **Celery does not hot-reload on code changes like uvicorn's `--reload` does** - after editing any collector/discover_service/worker code, the worker (and beat) process must be restarted manually, or it keeps running the old code in memory indefinitely.
2. An unhandled exception occurred inside `run_discovery_for_scope`. `workers/tasks.py` runs every scope under `asyncio.gather(..., return_exceptions=True)`, which silently discards any exception that escapes a scope's discovery coroutine - the scope then stays `"running"` forever with zero status rows, and the job still reaches a terminal status (since the gather itself never raises), producing a "stuck with no error" symptom that's indistinguishable from (1) without checking logs. `run_discovery_for_scope` now wraps its `_discover_by_provider` call in a try/except that logs the exception and marks the scope `"failed"` with a real `error_detail` - this is a last-resort safety net; provider orchestrators should still catch and report specific failures themselves wherever possible (see AWS's credential-setup handling below for why: only catching `TimeoutError` there previously let real AWS errors like `AccessDeniedException` propagate all the way out uncaught).

### AWS: multi-region collection and timeouts

Unlike Azure/GCP/OCI - whose list APIs are subscription/project-wide across every region in one call (e.g. Azure's `virtual_networks.list_all()`) - AWS's EC2 API is inherently regional (`ec2.describe_vpcs()` only returns VPCs in the client's configured region). `aws/orchestrator.py` accounts for this: `_resolve_regions()` enumerates the account's actually-enabled regions via `ec2.describe_regions()` (falling back to the scope's configured/default region if that call fails), and `_collect_across_regions()` fans each resource-type collector out across all of them, merging the per-region results back into a single `CollectionResult` so progress reporting still sees one result per resource type. Each item is tagged with its source region (`_navixa_region`) in `attributes`, since `NetworkResource.attributes` is a free-form JSONB column.

Every individual AWS API call - region enumeration and each per-region collector call - is wrapped in `asyncio.wait_for(..., timeout=AWS_COLLECTOR_CALL_TIMEOUT_SECONDS)`. Without this, a single stalled `ec2.describe_*` call had no bound beyond aioboto3's own defaults and could leave a scope (and the whole audit job) stuck showing "discovering" indefinitely with zero progress and no error. A timed-out region now just contributes a `"failed"` sub-result for that region (surfacing as `"partial"` overall if other regions succeeded), instead of blocking anything.

### AWS: tenant/scope modeling

AWS collapses to **one `CloudTenant` per connection** (auto-created on first import in `tenant_registry/aws_import.py`), with each accessible account imported as a `CloudScope` (`scope_type="account"`) under that single tenant - there is no separate "tenant" concept in AWS's delegated SSO session the way Azure AD has real tenants containing several subscriptions. This mirrors `account_sync.py`'s existing "Sync Accounts" feature, which already treats AWS accounts as scopes; `aws_import.py` reuses the same `list_sso_accounts` discovery call rather than duplicating it. See `tenant_registry.md` for the full picture.
