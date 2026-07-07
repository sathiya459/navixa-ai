"""Builds and executes the Cypher statements that sync NAVIXA Discover's
normalized inventory into `navixa_graph` (Neo4j) for one audit job.

Statement *building* is pure and unit-testable without a live Neo4j
instance; `sync_job_to_graph` is the thin execution wrapper around it.
"""

import uuid
from dataclasses import dataclass
from typing import Any

from app.graph_engine.attribute_extraction import extract_owning_network_id, extract_peering_endpoints
from app.graph_engine.schema import REL_PART_OF, REL_PEERED_WITH, RESOURCE_TYPE_TO_LABEL


@dataclass
class GraphResourceInput:
    id: uuid.UUID
    resource_type: str
    provider: str
    native_id: str
    name: str | None
    attributes: dict[str, Any]


def build_statements(
    resources: list[GraphResourceInput],
    audit_job_id: uuid.UUID,
    tenant_id: uuid.UUID,
    hub_ids: list[str] | None = None,
) -> list[tuple[str, dict[str, Any]]]:
    """Returns a list of (cypher, params) pairs. Node writes come first, then
    relationship writes (so relationships can always MATCH existing nodes
    within the same transaction batch), then cleanup deletes for resources
    that no longer exist in the cloud.

    Nodes are scoped by `tenant_id` (in addition to `native_id`/`provider`)
    so cleanup for one tenant can never touch another tenant's nodes.
    """
    statements: list[tuple[str, dict[str, Any]]] = []
    tenant_id_str = str(tenant_id)
    hub_id_set = set(hub_ids or [])

    for resource in resources:
        label = RESOURCE_TYPE_TO_LABEL.get(resource.resource_type, "Resource")
        statements.append(
            (
                f"""
                MERGE (n:{label} {{native_id: $native_id, provider: $provider, tenant_id: $tenant_id}})
                SET n.name = $name,
                    n.audit_job_id = $audit_job_id,
                    n.postgres_id = $postgres_id
                """,
                {
                    "native_id": resource.native_id,
                    "provider": resource.provider,
                    "tenant_id": tenant_id_str,
                    "name": resource.name,
                    "audit_job_id": str(audit_job_id),
                    "postgres_id": str(resource.id),
                },
            )
        )

    network_native_ids = {
        r.native_id for r in resources if r.resource_type == "network"
    }

    for resource in resources:
        if resource.resource_type != "network" or resource.native_id not in hub_id_set:
            continue
        statements.append(
            (
                """
                MATCH (n:Network {native_id: $native_id, provider: $provider, tenant_id: $tenant_id})
                SET n.is_hub = true
                """,
                {
                    "native_id": resource.native_id,
                    "provider": resource.provider,
                    "tenant_id": tenant_id_str,
                },
            )
        )

    for resource in resources:
        if resource.resource_type != "peering_connection":
            continue
        source_id, target_id = extract_peering_endpoints(resource.provider, resource.attributes)
        if not source_id or not target_id:
            continue
        if source_id not in network_native_ids or target_id not in network_native_ids:
            continue
        if source_id == target_id:
            continue

        statements.append(
            (
                f"""
                MATCH (a:Network {{native_id: $source_id, provider: $provider, tenant_id: $tenant_id}})
                MATCH (b:Network {{native_id: $target_id, provider: $provider, tenant_id: $tenant_id}})
                MERGE (a)-[r:{REL_PEERED_WITH}]->(b)
                SET r.native_id = $peering_native_id
                """,
                {
                    "source_id": source_id,
                    "target_id": target_id,
                    "provider": resource.provider,
                    "tenant_id": tenant_id_str,
                    "peering_native_id": resource.native_id,
                },
            )
        )

    for resource in resources:
        if resource.resource_type in ("network", "peering_connection"):
            continue
        owning_network_id = extract_owning_network_id(resource.provider, resource.attributes)
        if not owning_network_id or owning_network_id not in network_native_ids:
            continue

        label = RESOURCE_TYPE_TO_LABEL.get(resource.resource_type, "Resource")
        statements.append(
            (
                f"""
                MATCH (child:{label} {{native_id: $native_id, provider: $provider, tenant_id: $tenant_id}})
                MATCH (parent:Network {{native_id: $network_id, provider: $provider, tenant_id: $tenant_id}})
                MERGE (child)-[:{REL_PART_OF}]->(parent)
                """,
                {
                    "native_id": resource.native_id,
                    "network_id": owning_network_id,
                    "provider": resource.provider,
                    "tenant_id": tenant_id_str,
                },
            )
        )

    # Prune nodes for (label, provider) pairs that were actually collected
    # this run but whose native_id is no longer present - these are
    # resources that were deleted in the cloud since the last Discover run.
    # Only pairs present in `resources` are considered, so resource types
    # excluded from this job's scope (audit_job.resource_types) are left
    # untouched rather than being wrongly wiped out.
    seen_native_ids: dict[tuple[str, str], set[str]] = {}
    for resource in resources:
        label = RESOURCE_TYPE_TO_LABEL.get(resource.resource_type, "Resource")
        seen_native_ids.setdefault((label, resource.provider), set()).add(resource.native_id)

    for (label, provider), native_ids in seen_native_ids.items():
        statements.append(
            (
                f"""
                MATCH (n:{label} {{provider: $provider, tenant_id: $tenant_id}})
                WHERE NOT n.native_id IN $native_ids
                DETACH DELETE n
                """,
                {
                    "provider": provider,
                    "tenant_id": tenant_id_str,
                    "native_ids": list(native_ids),
                },
            )
        )

    return statements


def resources_to_graph_inputs(resources: list[Any]) -> list[GraphResourceInput]:
    """Converts `NetworkResource` ORM rows into `GraphResourceInput`s. Shared
    by the Celery Discover task and the manual graph re-sync endpoint so
    both build the graph from the exact same Postgres data.
    """
    return [
        GraphResourceInput(
            id=r.id,
            resource_type=r.resource_type,
            provider=r.provider,
            native_id=r.native_id,
            name=r.name,
            attributes=r.attributes,
        )
        for r in resources
    ]


def sync_job_to_graph(
    resources: list[GraphResourceInput],
    audit_job_id: uuid.UUID,
    tenant_id: uuid.UUID,
    hub_ids: list[str] | None = None,
) -> None:
    from app.config.settings import get_settings
    from app.graph_engine.session import get_driver

    statements = build_statements(resources, audit_job_id, tenant_id, hub_ids)
    driver = get_driver()
    with driver.session(database=get_settings().neo4j_database) as session:
        for cypher, params in statements:
            session.run(cypher, params)
