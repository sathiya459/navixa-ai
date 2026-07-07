# graph_engine — NAVIXA Graph

Persistent topology storage in Neo4j.

## Files

- `schema.py` — resource-type-to-Neo4j-label vocabulary and relationship constants.
- `session.py` — Neo4j driver singleton.
- `writer.py` — builds/executes Cypher `MERGE` statements to sync an audit job's normalized inventory into the `navixa_graph`.
- `attribute_extraction.py` — cross-provider extraction of structural relationships (peering endpoints, owning network, route targets, open ingress) from a resource's raw `attributes`. Shared by `writer.py`, `hub_spoke_validator/`, and `ai_engine/deviation_detector.py` so all three read the same provider-shape logic instead of separately-maintained, AWS-only copies.
- `queries.py` — read-side Cypher backing the Graph API (`api/v1/graph.py`).

## Notes

Consumes `NetworkResource` records produced by `collectors/` (via `normalization.py`) and written after each Discover run (see `workers/tasks.py`).

Nodes are `MERGE`d on `(native_id, provider, tenant_id)` - `tenant_id` is included so cleanup can never cross tenant boundaries. After each run, `writer.py` also prunes stale nodes: for every `(label, provider)` pair actually collected in that run, any existing node of that label/provider/tenant whose `native_id` is absent from the new batch is `DETACH DELETE`d - this represents a resource that was removed from the cloud since the last Discover run. Resource types excluded from a job's scope (`audit_job.resource_types`) are never touched, since no `(label, provider)` pair for them appears in that run's batch.

`writer.py` also builds two more pieces of structure beyond bare nodes, both deterministic (no AI/inference involved):
- A `PART_OF` edge from every non-`Network`, non-`peering_connection` resource to its owning `Network`, via `attribute_extraction.py::extract_owning_network_id()` - a best-effort, provider-specific extraction (AWS `VpcId`/`Attachments[].VpcId`; Azure: derived from a subnet's own resource ID path, since Azure subnets are VNet sub-resources; GCP `network`/`networkUrl`; OCI `vcnId`). Resource types where the raw API response carries no reliable network reference (e.g. Azure security groups/route tables, which `list_all()` returns with no VNet association) simply get no `PART_OF` edge rather than a guessed one.
- An `is_hub: true` property set on `Network` nodes whose `native_id` is in the job's `hub_selection` (persisted on `AuditJob` by `hub_spoke_validator/service.py` once Validate has run). `sync_job_to_graph`/`build_statements` take an optional `hub_ids` argument for this.

`resources_to_graph_inputs()` (also in `writer.py`) and `collectors/job_service.py::get_job_network_resources()` are shared by both the Celery Discover task (`workers/tasks.py::_sync_graph`) and the manual re-sync endpoint (`POST /graph/jobs/{job_id}/sync` in `api/v1/graph.py`) - the latter re-pushes a job's already-collected Postgres inventory into Neo4j on demand, for jobs that predate a `graph_engine` change or were never synced (e.g. Neo4j wasn't reachable at the time).
