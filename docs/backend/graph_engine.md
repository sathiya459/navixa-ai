# graph_engine — NAVIXA Graph

Computes the network topology (nodes/edges) for an audit job directly from
Postgres, on every request. There is no separate graph database - nothing
to sync, back up, or go stale.

## Files

- `schema.py` — resource-type-to-label vocabulary and relationship type constants (`PART_OF`, `PEERED_WITH`).
- `writer.py` — `GraphResourceInput` dataclass and `resources_to_graph_inputs()`, converting `NetworkResource` ORM rows into the plain shape `topology_service.py` builds on.
- `attribute_extraction.py` — cross-provider extraction of structural relationships (peering endpoints, owning network, route targets, open ingress) from a resource's raw `attributes`. Shared by `topology_service.py`, `hub_spoke_validator/`, and `ai_engine/deviation_detector.py` so all three read the same provider-shape logic instead of separately-maintained, AWS-only copies.
- `topology_service.py` — `build_topology(resources, hub_ids)` computes nodes/edges in memory; `get_job_topology(db, audit_job_id)` is the DB-backed entry point used by `api/v1/graph.py` and `ai_engine/service.py`.

## Notes

Each node's `id` is the resource's Postgres UUID (`NetworkResource.id`) - globally unique, so no cross-tenant collision handling is needed.

Two kinds of edges are derived, both deterministic (no AI/inference involved):
- A `PART_OF` edge from every non-`network`, non-`peering_connection` resource to its owning `Network`, via `attribute_extraction.py::extract_owning_network_id()` - a best-effort, provider-specific extraction (AWS `VpcId`/`Attachments[].VpcId`; Azure: derived from a subnet's own resource ID path, since Azure subnets are VNet sub-resources; GCP `network`/`networkUrl`; OCI `vcnId`). Resource types where the raw API response carries no reliable network reference (e.g. Azure security groups/route tables, which `list_all()` returns with no VNet association) simply get no `PART_OF` edge rather than a guessed one.
- A `PEERED_WITH` edge between two `Network` nodes via `attribute_extraction.py::extract_peering_endpoints()`, when both endpoints resolve to networks present in the same job.

An `is_hub: true` property is set on `Network` node properties whose `native_id` is in the job's `hub_selection` (persisted on `AuditJob` by `hub_spoke_validator/service.py` once Validate has run).

Because topology is computed live from whatever `NetworkResource` rows already exist for the job, there is no backfill/re-sync endpoint - re-running Discover or re-running Validate (which sets `hub_selection`) is immediately reflected the next time the topology is fetched.
