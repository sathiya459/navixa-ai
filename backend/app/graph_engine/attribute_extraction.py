"""Cross-provider extraction of structural relationships (peering endpoints,
owning network, route targets, open ingress) from a resource's raw
`attributes` dict.

Each cloud provider's collector returns attributes in that provider's native
API shape (AWS's `RequesterVpcInfo.VpcId`, Azure's `remoteVirtualNetwork.id`,
etc.) - there is no normalized schema across providers. This module is the
single place that knows how to read those provider-specific shapes, so
`graph_engine/topology_service.py` (topology), `hub_spoke_validator/` (rule
engine), and `ai_engine/deviation_detector.py` (AI summary) all see the
same extraction logic instead of three separately-maintained, AWS-only
copies.
"""

from typing import Any


def extract_peering_endpoints(provider: str, attributes: dict[str, Any]) -> tuple[str | None, str | None]:
    """Returns (source_network_native_id, target_network_native_id) for a
    peering_connection resource's raw attributes, or (None, None) if the
    shape isn't recognized.
    """
    attrs = attributes

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


def extract_owning_network_id(provider: str, attributes: dict[str, Any]) -> str | None:
    """Best-effort extraction of the Network/VPC/VNet a resource belongs to,
    across providers' differing attribute shapes. Returns None when the raw
    attributes carry no reliable owning-network reference (e.g. Azure
    security groups/route tables, which list_all() returns with no VNet
    association) - such resources simply get no PART_OF edge rather than a
    guessed one.
    """
    attrs = attributes

    if provider == "aws":
        if attrs.get("VpcId"):
            return attrs["VpcId"]
        attachments = attrs.get("Attachments") or []
        if isinstance(attachments, list) and attachments:
            return attachments[0].get("VpcId")
        return None

    if provider == "azure":
        # Subnets are sub-resources of a VNet, so the subnet's own resource
        # ID is the VNet's resource ID with a `/subnets/{name}` suffix -
        # stripping that suffix recovers the owning VNet's ID. Other Azure
        # resource types (NSGs, route tables) aren't linked to a VNet in
        # their raw list-all response, so this only resolves for subnets.
        resource_id = attrs.get("id") or ""
        if "/subnets/" in resource_id:
            return resource_id.split("/subnets/")[0]
        return None

    if provider == "gcp":
        return attrs.get("network") or attrs.get("networkUrl")

    if provider == "oci":
        return attrs.get("vcnId") or attrs.get("vcn_id")

    return None


def extract_route_targets(provider: str, route_table_attributes: dict[str, Any]) -> list[str]:
    """Returns the list of gateway/peering/next-hop targets a route table's
    routes point at, across providers' differing route shapes.
    """
    attrs = route_table_attributes

    if provider == "aws":
        return [
            route.get("GatewayId") or route.get("VpcPeeringConnectionId")
            for route in attrs.get("Routes", []) or []
            if route.get("GatewayId") or route.get("VpcPeeringConnectionId")
        ]

    if provider == "azure":
        targets = []
        for route in attrs.get("routes", []) or []:
            target = route.get("nextHopIpAddress") or route.get("nextHopType")
            if target:
                targets.append(target)
        return targets

    return []


def extract_open_ingress(provider: str, security_group_or_nsg_attributes: dict[str, Any]) -> bool:
    """Returns True if the resource has an ingress rule open to the
    internet (0.0.0.0/0 or equivalent), across providers' differing
    security-rule shapes.
    """
    attrs = security_group_or_nsg_attributes

    if provider == "aws":
        return any(
            ip_range.get("CidrIp") == "0.0.0.0/0"
            for perm in attrs.get("IpPermissions", []) or []
            for ip_range in perm.get("IpRanges", []) or []
        )

    if provider == "azure":
        return any(
            rule.get("direction") == "Inbound"
            and rule.get("access") == "Allow"
            and rule.get("destinationAddressPrefix") in ("*", "0.0.0.0/0", "Internet")
            for rule in attrs.get("securityRules", []) or []
        )

    return False
