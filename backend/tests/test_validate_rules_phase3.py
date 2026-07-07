import uuid

from app.hub_spoke_validator.graph_builder import build_network_graph
from app.hub_spoke_validator.rules import (
    detect_hub_bypass_routing,
    detect_segmentation_violations,
    extract_environment_tags,
)
from app.models.network_resource import NetworkResource


def _resource(resource_type, native_id, attributes, provider="aws"):
    return NetworkResource(
        id=uuid.uuid4(),
        audit_job_scope_id=uuid.uuid4(),
        resource_type=resource_type,
        provider=provider,
        native_id=native_id,
        attributes=attributes,
    )


def test_hub_bypass_flags_spoke_with_own_gateway_routed_directly():
    resources = [
        _resource("network", "vpc-hub", {}),
        _resource("network", "vpc-spoke", {}),
        _resource("gateway", "igw-spoke", {"Attachments": [{"VpcId": "vpc-spoke", "State": "available"}]}),
        _resource(
            "route_table",
            "rtb-spoke",
            {"VpcId": "vpc-spoke", "Routes": [{"DestinationCidrBlock": "0.0.0.0/0", "GatewayId": "igw-spoke"}]},
        ),
    ]
    graph = build_network_graph(resources)
    findings = detect_hub_bypass_routing(graph, hub_vpc_ids={"vpc-hub"})

    assert len(findings) == 1
    assert findings[0]["finding_type"] == "hub_bypass_routing"


def test_hub_bypass_does_not_flag_hub_itself():
    resources = [
        _resource("network", "vpc-hub", {}),
        _resource("gateway", "igw-hub", {"Attachments": [{"VpcId": "vpc-hub", "State": "available"}]}),
        _resource(
            "route_table",
            "rtb-hub",
            {"VpcId": "vpc-hub", "Routes": [{"DestinationCidrBlock": "0.0.0.0/0", "GatewayId": "igw-hub"}]},
        ),
    ]
    graph = build_network_graph(resources)
    findings = detect_hub_bypass_routing(graph, hub_vpc_ids={"vpc-hub"})
    assert findings == []


def test_hub_bypass_does_not_flag_spoke_with_no_own_gateway():
    resources = [
        _resource("network", "vpc-hub", {}),
        _resource("network", "vpc-spoke", {}),
        _resource(
            "route_table",
            "rtb-spoke",
            {"VpcId": "vpc-spoke", "Routes": [{"DestinationCidrBlock": "0.0.0.0/0", "GatewayId": "tgw-hub"}]},
        ),
    ]
    graph = build_network_graph(resources)
    findings = detect_hub_bypass_routing(graph, hub_vpc_ids={"vpc-hub"})
    assert findings == []


def test_extract_environment_tags_reads_environment_key_case_insensitive():
    resources = [
        _resource("network", "vpc-prod", {"Tags": [{"Key": "environment", "Value": "prod"}]}),
        _resource("network", "vpc-dev", {"Tags": [{"Key": "Environment", "Value": "dev"}]}),
    ]
    envs = extract_environment_tags(resources)
    assert envs == {"vpc-prod": "prod", "vpc-dev": "dev"}


def test_segmentation_violation_flags_cross_environment_peering():
    resources = [
        _resource("network", "vpc-prod", {"Tags": [{"Key": "Environment", "Value": "prod"}]}),
        _resource("network", "vpc-dev", {"Tags": [{"Key": "Environment", "Value": "dev"}]}),
        _resource(
            "peering_connection",
            "pcx-1",
            {"RequesterVpcInfo": {"VpcId": "vpc-prod"}, "AccepterVpcInfo": {"VpcId": "vpc-dev"}},
        ),
    ]
    graph = build_network_graph(resources)
    envs = extract_environment_tags([r for r in resources if r.resource_type == "network"])
    findings = detect_segmentation_violations(graph, envs)

    assert len(findings) == 1
    assert findings[0]["finding_type"] == "segmentation_violation"


def test_segmentation_violation_does_not_flag_same_environment_peering():
    resources = [
        _resource("network", "vpc-prod-a", {"Tags": [{"Key": "Environment", "Value": "prod"}]}),
        _resource("network", "vpc-prod-b", {"Tags": [{"Key": "Environment", "Value": "PROD"}]}),
        _resource(
            "peering_connection",
            "pcx-1",
            {"RequesterVpcInfo": {"VpcId": "vpc-prod-a"}, "AccepterVpcInfo": {"VpcId": "vpc-prod-b"}},
        ),
    ]
    graph = build_network_graph(resources)
    envs = extract_environment_tags([r for r in resources if r.resource_type == "network"])
    findings = detect_segmentation_violations(graph, envs)
    assert findings == []


def test_segmentation_violation_flags_cross_environment_azure_peering():
    resources = [
        _resource(
            "network", "vnet-spoke1-dev", {"Tags": [{"Key": "Environment", "Value": "prod"}]}, provider="azure"
        ),
        _resource(
            "network", "vnet-spoke2-dev", {"Tags": [{"Key": "Environment", "Value": "dev"}]}, provider="azure"
        ),
        _resource(
            "peering_connection",
            "peer-1",
            {"vnet_id": "vnet-spoke1-dev", "remoteVirtualNetwork": {"id": "vnet-spoke2-dev"}},
            provider="azure",
        ),
    ]
    graph = build_network_graph(resources)
    envs = extract_environment_tags([r for r in resources if r.resource_type == "network"])
    findings = detect_segmentation_violations(graph, envs)

    assert len(findings) == 1
    assert findings[0]["finding_type"] == "segmentation_violation"
