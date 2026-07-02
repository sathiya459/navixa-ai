"""Builds and executes the Cypher statements that sync NAVIXA Discover's
normalized inventory into `navixa_graph` (Neo4j) for one audit job.

Statement *building* is pure and unit-testable without a live Neo4j
instance; `sync_job_to_graph` is the thin execution wrapper around it.
"""

import uuid
from dataclasses import dataclass
from typing import Any

from app.graph_engine.schema import REL_PEERED_WITH, RESOURCE_TYPE_TO_LABEL


@dataclass
class GraphResourceInput:
    id: uuid.UUID
    resource_type: str
    provider: str
    native_id: str
    name: str | None
    attributes: dict[str, Any]


def build_statements(
    resources: list[GraphResourceInput], audit_job_id: uuid.UUID
) -> list[tuple[str, dict[str, Any]]]:
    """Returns a list of (cypher, params) pairs. Node writes come first,
    then relationship writes, so relationships can always MATCH existing
    nodes within the same transaction batch.
    """
    statements: list[tuple[str, dict[str, Any]]] = []

    for resource in resources:
        label = RESOURCE_TYPE_TO_LABEL.get(resource.resource_type, "Resource")
        statements.append(
            (
                f"""
                MERGE (n:{label} {{native_id: $native_id, provider: $provider}})
                SET n.name = $name,
                    n.audit_job_id = $audit_job_id,
                    n.postgres_id = $postgres_id
                """,
                {
                    "native_id": resource.native_id,
                    "provider": resource.provider,
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
        if resource.resource_type != "peering_connection":
            continue
        source_id, target_id = _extract_peering_endpoints(resource)
        if not source_id or not target_id:
            continue
        if source_id not in network_native_ids or target_id not in network_native_ids:
            continue
        if source_id == target_id:
            continue

        statements.append(
            (
                f"""
                MATCH (a:Network {{native_id: $source_id, provider: $provider}})
                MATCH (b:Network {{native_id: $target_id, provider: $provider}})
                MERGE (a)-[r:{REL_PEERED_WITH}]->(b)
                SET r.native_id = $peering_native_id
                """,
                {
                    "source_id": source_id,
                    "target_id": target_id,
                    "provider": resource.provider,
                    "peering_native_id": resource.native_id,
                },
            )
        )

    return statements


def _extract_peering_endpoints(resource: GraphResourceInput) -> tuple[str | None, str | None]:
    """Best-effort extraction across providers' differing peering attribute
    shapes (mirrors frontend/src/pages/topology/buildTopology.ts)."""
    attrs = resource.attributes

    requester = attrs.get("RequesterVpcInfo")
    accepter = attrs.get("AccepterVpcInfo")
    if requester or accepter:
        return (requester or {}).get("VpcId"), (accepter or {}).get("VpcId")

    if attrs.get("vnet_id") or attrs.get("remoteVirtualNetwork"):
        remote = attrs.get("remoteVirtualNetwork") or {}
        return attrs.get("vnet_id"), remote.get("id")

    if attrs.get("network"):
        return attrs.get("network"), attrs.get("networkUrl") or attrs.get("network")

    return None, None


def sync_job_to_graph(resources: list[GraphResourceInput], audit_job_id: uuid.UUID) -> None:
    from app.config.settings import get_settings
    from app.graph_engine.session import get_driver

    statements = build_statements(resources, audit_job_id)
    driver = get_driver()
    with driver.session(database=get_settings().neo4j_database) as session:
        for cypher, params in statements:
            session.run(cypher, params)
