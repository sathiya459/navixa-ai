"""Builds an in-memory NetworkX graph from a job's normalized inventory,
per Section 12 ("NetworkX for in-memory algorithms"). This graph is the
input to the Section 13 validation rules; it is deliberately separate
from `graph_engine/topology_service.py`'s topology (computed for display,
not validation) so rules can run entirely from data already loaded for
the job.

PEERED_WITH edges are extracted cross-provider (via
graph_engine/attribute_extraction.py). ATTACHED_TO/ROUTES_TO edge
construction is still AWS-shaped (VpcId, GatewayId, Attachments, Routes)
since deriving gateway ownership and routing reliably needs deeper
provider-specific routing-model heuristics that risk wrong findings in a
security tool - other providers' resources still appear as nodes but won't
contribute ROUTES_TO/ATTACHED_TO edges (and therefore no
hub_bypass_routing findings) until that's tackled separately.
"""

import networkx as nx

from app.graph_engine.attribute_extraction import extract_peering_endpoints
from app.models.network_resource import NetworkResource

REL_ATTACHED_TO = "ATTACHED_TO"
REL_ROUTES_TO = "ROUTES_TO"
REL_PEERED_WITH = "PEERED_WITH"


def build_network_graph(resources: list[NetworkResource]) -> nx.MultiDiGraph:
    # MultiDiGraph: a VPC and a gateway can be connected by both an
    # ATTACHED_TO edge and a ROUTES_TO edge simultaneously - a plain
    # DiGraph only keeps one edge per node pair and would silently drop
    # whichever relation was added second.
    graph = nx.MultiDiGraph()

    networks = {r.native_id: r for r in resources if r.resource_type == "network"}
    gateways = {r.native_id: r for r in resources if r.resource_type == "gateway"}
    route_tables = [r for r in resources if r.resource_type == "route_table"]
    peerings = [r for r in resources if r.resource_type == "peering_connection"]

    for native_id, resource in networks.items():
        graph.add_node(native_id, resource_type="network", attributes=resource.attributes)
    for native_id, resource in gateways.items():
        graph.add_node(native_id, resource_type="gateway", attributes=resource.attributes)

    for native_id, gateway in gateways.items():
        owner_vpc = _gateway_owner_vpc(gateway.attributes)
        if owner_vpc and owner_vpc in networks:
            graph.add_edge(owner_vpc, native_id, key=REL_ATTACHED_TO, relation=REL_ATTACHED_TO)

    for route_table in route_tables:
        vpc_id = route_table.attributes.get("VpcId")
        if vpc_id not in networks:
            continue
        for route in route_table.attributes.get("Routes", []) or []:
            target = route.get("GatewayId") or route.get("VpcPeeringConnectionId")
            if target:
                graph.add_edge(
                    vpc_id,
                    target,
                    key=f"{REL_ROUTES_TO}:{route.get('DestinationCidrBlock')}",
                    relation=REL_ROUTES_TO,
                    destination=route.get("DestinationCidrBlock"),
                )

    for peering in peerings:
        source_id, target_id = extract_peering_endpoints(peering.provider, peering.attributes)
        if source_id in networks and target_id in networks and source_id != target_id:
            graph.add_edge(
                source_id, target_id, key=peering.native_id, relation=REL_PEERED_WITH, native_id=peering.native_id
            )
            graph.add_edge(
                target_id, source_id, key=peering.native_id, relation=REL_PEERED_WITH, native_id=peering.native_id
            )

    return graph


def _gateway_owner_vpc(attributes: dict) -> str | None:
    if attributes.get("VpcId"):
        return attributes["VpcId"]
    for attachment in attributes.get("Attachments", []) or []:
        if attachment.get("State") == "available":
            return attachment.get("VpcId")
    return None
