"""Phase 1 NAVIXA Validate rule set: unauthorized VPC peering detection.

A peering connection is "unauthorized" if neither side of the peering is one
of the user-designated Hub VPCs — i.e. it represents spoke-to-spoke
connectivity that bypasses the hub, which Hub-and-Spoke architectures are
meant to prevent. Full rule coverage (routing bypass, segmentation
violations) lands in Phase 3 once the Neo4j graph is available (Section 13).
"""

from app.models.network_resource import NetworkResource


def detect_unauthorized_peering(
    peering_resources: list[NetworkResource], hub_vpc_ids: set[str]
) -> list[dict]:
    findings = []

    for resource in peering_resources:
        attrs = resource.attributes
        requester_vpc = attrs.get("RequesterVpcInfo", {}).get("VpcId")
        accepter_vpc = attrs.get("AccepterVpcInfo", {}).get("VpcId")
        peered_vpcs = {v for v in (requester_vpc, accepter_vpc) if v}

        if peered_vpcs and not peered_vpcs & hub_vpc_ids:
            findings.append(
                {
                    "finding_type": "unauthorized_peering",
                    "severity": "high",
                    "title": f"Unauthorized VPC peering: {resource.native_id}",
                    "description": (
                        f"VPC peering connection {resource.native_id} connects "
                        f"{requester_vpc} and {accepter_vpc}, neither of which is a "
                        "designated Hub VPC. This represents spoke-to-spoke "
                        "connectivity bypassing the Hub-and-Spoke architecture."
                    ),
                    "affected_resource_ids": [str(resource.id)],
                }
            )

    return findings
