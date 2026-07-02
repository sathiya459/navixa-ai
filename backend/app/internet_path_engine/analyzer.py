"""NAVIXA Pathfinder (Section 14): internet ingress/egress exposure analysis.

Built on the same NetworkX graph as NAVIXA Validate (Section 12), since a
network's exposure path is fundamentally "does this network route to an
internet-facing gateway, and if so, do its security groups actually allow
traffic through." Full ingress path detail (public IP -> load balancer ->
network interface) is deferred until those resource types are collected
(Section 10 lists Network Interfaces/ALB/NLB, not yet in NAVIXA Discover's
Phase 1 collector scope); this analysis operates one hop back, at the
Gateway + SecurityGroup level, which is what's available today.
"""

import networkx as nx

from app.hub_spoke_validator.graph_builder import REL_ATTACHED_TO, REL_ROUTES_TO
from app.models.network_resource import NetworkResource

OPEN_CIDR = "0.0.0.0/0"
INTERNET_GATEWAY_TYPES = {"internet_gateway", "nat_gateway"}

# Ports where an open (0.0.0.0/0) inbound rule is treated as high severity
# rather than medium - remote administration protocols.
HIGH_RISK_PORTS = {22, 3389}


def _internet_gateways(resources: list[NetworkResource]) -> dict[str, NetworkResource]:
    return {
        r.native_id: r
        for r in resources
        if r.resource_type == "gateway" and r.attributes.get("GatewayType") in INTERNET_GATEWAY_TYPES
    }


def _security_groups_by_vpc(resources: list[NetworkResource]) -> dict[str, list[NetworkResource]]:
    by_vpc: dict[str, list[NetworkResource]] = {}
    for r in resources:
        if r.resource_type != "security_group":
            continue
        vpc_id = r.attributes.get("VpcId")
        if vpc_id:
            by_vpc.setdefault(vpc_id, []).append(r)
    return by_vpc


def _has_open_rule(security_group: NetworkResource, permission_key: str) -> list[dict]:
    open_rules = []
    for permission in security_group.attributes.get(permission_key, []) or []:
        for ip_range in permission.get("IpRanges", []) or []:
            if ip_range.get("CidrIp") == OPEN_CIDR:
                open_rules.append(permission)
                break
    return open_rules


def _severity_for_rules(rules: list[dict]) -> str:
    for rule in rules:
        from_port = rule.get("FromPort")
        to_port = rule.get("ToPort")
        if from_port is None and to_port is None:
            return "critical"  # all ports open
        if from_port is not None and any(
            from_port <= port <= (to_port if to_port is not None else from_port) for port in HIGH_RISK_PORTS
        ):
            return "critical"
    return "high"


def _networks_routed_to_internet(graph: nx.MultiDiGraph, internet_gateway_ids: set[str]) -> dict[str, str]:
    """Returns {network_native_id: gateway_native_id} for networks with a
    ROUTES_TO or ATTACHED_TO edge reaching an internet-facing gateway."""
    routed: dict[str, str] = {}
    for network_id, gateway_id, edata in graph.edges(data=True):
        if gateway_id not in internet_gateway_ids:
            continue
        if edata.get("relation") in (REL_ROUTES_TO, REL_ATTACHED_TO):
            routed[network_id] = gateway_id
    return routed


def analyze_ingress_exposure(graph: nx.MultiDiGraph, resources: list[NetworkResource]) -> list[dict]:
    findings = []
    igws = _internet_gateways(resources)
    sgs_by_vpc = _security_groups_by_vpc(resources)
    routed_networks = _networks_routed_to_internet(graph, set(igws.keys()))

    for network_id, gateway_id in routed_networks.items():
        for sg in sgs_by_vpc.get(network_id, []):
            open_rules = _has_open_rule(sg, "IpPermissions")
            if not open_rules:
                continue
            findings.append(
                {
                    "finding_type": "internet_ingress_exposure",
                    "severity": _severity_for_rules(open_rules),
                    "title": f"Internet-exposed ingress path: {network_id} via {gateway_id}",
                    "description": (
                        f"Network {network_id} routes to internet gateway {gateway_id} "
                        f"and security group {sg.native_id} allows inbound traffic from "
                        f"{OPEN_CIDR}. This represents an internet ingress exposure path."
                    ),
                    "affected_resource_ids": [network_id, gateway_id, sg.native_id],
                }
            )

    return findings


def analyze_egress_exposure(graph: nx.MultiDiGraph, resources: list[NetworkResource]) -> list[dict]:
    findings = []
    igws = _internet_gateways(resources)
    sgs_by_vpc = _security_groups_by_vpc(resources)
    routed_networks = _networks_routed_to_internet(graph, set(igws.keys()))

    for network_id, gateway_id in routed_networks.items():
        for sg in sgs_by_vpc.get(network_id, []):
            open_rules = _has_open_rule(sg, "IpPermissionsEgress")
            if not open_rules:
                continue
            findings.append(
                {
                    "finding_type": "internet_egress_exposure",
                    "severity": "medium",
                    "title": f"Unrestricted egress path: {network_id} via {gateway_id}",
                    "description": (
                        f"Network {network_id} routes to internet gateway {gateway_id} "
                        f"and security group {sg.native_id} allows unrestricted outbound "
                        f"traffic to {OPEN_CIDR}. Combined with internet routing, this "
                        "permits unrestricted egress to the internet."
                    ),
                    "affected_resource_ids": [network_id, gateway_id, sg.native_id],
                }
            )

    return findings
