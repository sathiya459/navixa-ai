"""Builds an in-memory NetworkX graph from a job's normalized inventory,
per Section 12 ("NetworkX for in-memory algorithms"). This graph is the
input to the Section 13 validation rules; it is deliberately separate
from the persisted Neo4j graph (navixa_graph) so rules can run entirely
from data already loaded for the job, without a round-trip to Neo4j.

Edge construction is AWS-shaped (VpcId, GatewayId, Attachments, Routes)
since AWS is the only provider with a resource attribute schema rich
enough to derive gateway ownership and routing today; other providers'
resources still appear as nodes but won't contribute ROUTES_TO/ATTACHED_TO
edges until their attribute shapes are mapped similarly.
"""

import networkx as nx

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
        requester = (peering.attributes.get("RequesterVpcInfo") or {}).get("VpcId")
        accepter = (peering.attributes.get("AccepterVpcInfo") or {}).get("VpcId")
        if requester in networks and accepter in networks and requester != accepter:
            graph.add_edge(
                requester, accepter, key=peering.native_id, relation=REL_PEERED_WITH, native_id=peering.native_id
            )
            graph.add_edge(
                accepter, requester, key=peering.native_id, relation=REL_PEERED_WITH, native_id=peering.native_id
            )

    return graph


def _gateway_owner_vpc(attributes: dict) -> str | None:
    if attributes.get("VpcId"):
        return attributes["VpcId"]
    for attachment in attributes.get("Attachments", []) or []:
        if attachment.get("State") == "available":
            return attachment.get("VpcId")
    return None
