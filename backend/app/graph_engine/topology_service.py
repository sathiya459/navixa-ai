"""Computes NAVIXA Graph's node/edge topology directly from Postgres, with
no separate graph database. Nodes/edges are derived on every request from
the audit job's `NetworkResource` rows (via `attribute_extraction.py`'s
provider-aware peering/ownership extraction), so there is nothing to sync,
back up, or go stale - the topology is always exactly what Discover last
collected.
"""

import uuid
from typing import Any

from app.graph_engine.attribute_extraction import extract_owning_network_id, extract_peering_endpoints
from app.graph_engine.writer import GraphResourceInput
from app.graph_engine.schema import REL_PART_OF, REL_PEERED_WITH, RESOURCE_TYPE_TO_LABEL


def build_topology(
    resources: list[GraphResourceInput],
    hub_ids: list[str] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    hub_id_set = set(hub_ids or [])

    networks = [r for r in resources if r.resource_type == "network"]
    network_native_id_to_id = {r.native_id: str(r.id) for r in networks}

    nodes: dict[str, dict[str, Any]] = {}
    for resource in resources:
        label = RESOURCE_TYPE_TO_LABEL.get(resource.resource_type, "Resource")
        node_id = str(resource.id)
        properties: dict[str, Any] = {
            "native_id": resource.native_id,
            "provider": resource.provider,
            "name": resource.name,
        }
        if resource.resource_type == "network" and resource.native_id in hub_id_set:
            properties["is_hub"] = True
        nodes[node_id] = {"id": node_id, "labels": [label], "properties": properties}

    edges: list[dict[str, Any]] = []

    for resource in resources:
        if resource.resource_type != "peering_connection":
            continue
        source_native_id, target_native_id = extract_peering_endpoints(resource.provider, resource.attributes)
        source_id = network_native_id_to_id.get(source_native_id or "")
        target_id = network_native_id_to_id.get(target_native_id or "")
        if not source_id or not target_id or source_id == target_id:
            continue
        edges.append(
            {
                "id": f"peering:{resource.id}",
                "source": source_id,
                "target": target_id,
                "type": REL_PEERED_WITH,
            }
        )

    for resource in resources:
        if resource.resource_type in ("network", "peering_connection"):
            continue
        owning_network_native_id = extract_owning_network_id(resource.provider, resource.attributes)
        parent_id = network_native_id_to_id.get(owning_network_native_id or "")
        if not parent_id:
            continue
        edges.append(
            {
                "id": f"part_of:{resource.id}",
                "source": str(resource.id),
                "target": parent_id,
                "type": REL_PART_OF,
            }
        )

    return {"nodes": list(nodes.values()), "edges": edges}


def get_job_topology(
    db,
    audit_job_id: uuid.UUID,
) -> dict[str, list[dict[str, Any]]]:
    from app.collectors.job_service import get_audit_job, get_job_network_resources
    from app.graph_engine.writer import resources_to_graph_inputs

    audit_job = get_audit_job(db, audit_job_id)
    resources = get_job_network_resources(db, audit_job_id)
    hub_ids = (audit_job.hub_selection or {}).get("hub_ids", []) if audit_job else []
    return build_topology(resources_to_graph_inputs(resources), hub_ids)
