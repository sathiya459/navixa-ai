"""NAVIXA Validate rule set (Section 13): Hub-and-Spoke compliance checks.

- unauthorized_peering: VPC peering where neither side is a designated Hub.
- hub_bypass_routing: a spoke has its own internet/NAT gateway rather than
  routing egress/ingress through the hub (uses the NetworkX graph built by
  graph_builder.py from ATTACHED_TO/ROUTES_TO edges).
- segmentation_violation: two directly-peered networks carry different
  "Environment" tag values (e.g. prod peered directly to dev), regardless
  of hub involvement, since that peering itself is the segmentation risk.
"""

import networkx as nx

from app.graph_engine.attribute_extraction import extract_peering_endpoints
from app.hub_spoke_validator.graph_builder import REL_ATTACHED_TO, REL_PEERED_WITH, REL_ROUTES_TO
from app.models.network_resource import NetworkResource


def detect_unauthorized_peering(
    peering_resources: list[NetworkResource], hub_vpc_ids: set[str]
) -> list[dict]:
    findings = []

    for resource in peering_resources:
        source_id, target_id = extract_peering_endpoints(resource.provider, resource.attributes)
        peered_vpcs = {v for v in (source_id, target_id) if v}

        if peered_vpcs and not peered_vpcs & hub_vpc_ids:
            findings.append(
                {
                    "finding_type": "unauthorized_peering",
                    "severity": "high",
                    "title": f"Unauthorized VPC peering: {resource.native_id}",
                    "description": (
                        f"VPC peering connection {resource.native_id} connects "
                        f"{source_id} and {target_id}, neither of which is a "
                        "designated Hub VPC. This represents spoke-to-spoke "
                        "connectivity bypassing the Hub-and-Spoke architecture."
                    ),
                    "affected_resource_ids": [str(resource.id)],
                }
            )

    return findings


def detect_hub_bypass_routing(graph: nx.DiGraph, hub_vpc_ids: set[str]) -> list[dict]:
    findings = []

    spokes = [
        n for n, d in graph.nodes(data=True)
        if d.get("resource_type") == "network" and n not in hub_vpc_ids
    ]

    for spoke in spokes:
        own_gateways = {
            target
            for _, target, edata in graph.out_edges(spoke, data=True)
            if edata.get("relation") == REL_ATTACHED_TO
        }
        if not own_gateways:
            continue

        routed_gateways = {
            target
            for _, target, edata in graph.out_edges(spoke, data=True)
            if edata.get("relation") == REL_ROUTES_TO and target in own_gateways
        }

        for gateway_id in routed_gateways:
            findings.append(
                {
                    "finding_type": "hub_bypass_routing",
                    "severity": "high",
                    "title": f"Spoke {spoke} routes directly through its own gateway {gateway_id}",
                    "description": (
                        f"Spoke VPC {spoke} has a route table entry targeting gateway "
                        f"{gateway_id}, which is attached directly to the spoke rather "
                        "than the hub. This bypasses centralized hub inspection/egress "
                        "control expected in a Hub-and-Spoke architecture."
                    ),
                    "affected_resource_ids": [spoke, gateway_id],
                }
            )

    return findings


def detect_segmentation_violations(
    graph: nx.DiGraph, environment_by_native_id: dict[str, str]
) -> list[dict]:
    findings = []
    seen_pairs: set[tuple[str, str]] = set()

    for source, target, edata in graph.edges(data=True):
        if edata.get("relation") != REL_PEERED_WITH:
            continue

        pair = tuple(sorted((source, target)))
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)

        source_env = environment_by_native_id.get(source)
        target_env = environment_by_native_id.get(target)
        if source_env and target_env and source_env.lower() != target_env.lower():
            findings.append(
                {
                    "finding_type": "segmentation_violation",
                    "severity": "critical",
                    "title": f"Cross-environment peering: {source} ({source_env}) <-> {target} ({target_env})",
                    "description": (
                        f"Network {source} (Environment={source_env}) is directly peered "
                        f"with {target} (Environment={target_env}). Direct connectivity "
                        "between different environments violates segmentation "
                        "boundaries and should route through controlled hub inspection, "
                        "if permitted at all."
                    ),
                    "affected_resource_ids": [source, target],
                }
            )

    return findings


def extract_environment_tags(network_resources: list[NetworkResource]) -> dict[str, str]:
    """Reads the "Environment" tag (case-insensitive key) off each network
    resource, e.g. {"Key": "Environment", "Value": "prod"} in AWS's Tags
    list, returning {native_id: environment_value}.
    """
    environments: dict[str, str] = {}
    for resource in network_resources:
        for tag in resource.attributes.get("Tags", []) or []:
            if tag.get("Key", "").lower() == "environment" and tag.get("Value"):
                environments[resource.native_id] = tag["Value"]
                break
    return environments
