import uuid

from app.hub_spoke_validator.graph_builder import build_network_graph
from app.internet_path_engine.analyzer import analyze_egress_exposure, analyze_ingress_exposure
from app.models.network_resource import NetworkResource


def _resource(resource_type, native_id, attributes):
    return NetworkResource(
        id=uuid.uuid4(),
        audit_job_scope_id=uuid.uuid4(),
        resource_type=resource_type,
        provider="aws",
        native_id=native_id,
        attributes=attributes,
    )


def test_ingress_exposure_flagged_for_open_ssh_behind_igw():
    resources = [
        _resource("network", "vpc-1", {}),
        _resource("gateway", "igw-1", {"GatewayType": "internet_gateway", "Attachments": [{"VpcId": "vpc-1", "State": "available"}]}),
        _resource(
            "security_group",
            "sg-1",
            {
                "VpcId": "vpc-1",
                "IpPermissions": [
                    {"FromPort": 22, "ToPort": 22, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}
                ],
            },
        ),
    ]
    graph = build_network_graph(resources)
    findings = analyze_ingress_exposure(graph, resources)

    assert len(findings) == 1
    assert findings[0]["finding_type"] == "internet_ingress_exposure"
    assert findings[0]["severity"] == "critical"


def test_ingress_exposure_not_flagged_without_internet_gateway():
    resources = [
        _resource("network", "vpc-1", {}),
        _resource(
            "security_group",
            "sg-1",
            {
                "VpcId": "vpc-1",
                "IpPermissions": [
                    {"FromPort": 22, "ToPort": 22, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}
                ],
            },
        ),
    ]
    graph = build_network_graph(resources)
    findings = analyze_ingress_exposure(graph, resources)
    assert findings == []


def test_ingress_exposure_not_flagged_for_restricted_security_group():
    resources = [
        _resource("network", "vpc-1", {}),
        _resource("gateway", "igw-1", {"GatewayType": "internet_gateway", "Attachments": [{"VpcId": "vpc-1", "State": "available"}]}),
        _resource(
            "security_group",
            "sg-1",
            {
                "VpcId": "vpc-1",
                "IpPermissions": [
                    {"FromPort": 22, "ToPort": 22, "IpRanges": [{"CidrIp": "10.0.0.0/8"}]}
                ],
            },
        ),
    ]
    graph = build_network_graph(resources)
    findings = analyze_ingress_exposure(graph, resources)
    assert findings == []


def test_ingress_exposure_high_severity_for_non_admin_open_port():
    resources = [
        _resource("network", "vpc-1", {}),
        _resource("gateway", "igw-1", {"GatewayType": "internet_gateway", "Attachments": [{"VpcId": "vpc-1", "State": "available"}]}),
        _resource(
            "security_group",
            "sg-1",
            {
                "VpcId": "vpc-1",
                "IpPermissions": [
                    {"FromPort": 443, "ToPort": 443, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}
                ],
            },
        ),
    ]
    graph = build_network_graph(resources)
    findings = analyze_ingress_exposure(graph, resources)
    assert findings[0]["severity"] == "high"


def test_egress_exposure_flagged_for_open_outbound_behind_igw():
    resources = [
        _resource("network", "vpc-1", {}),
        _resource("gateway", "igw-1", {"GatewayType": "internet_gateway", "Attachments": [{"VpcId": "vpc-1", "State": "available"}]}),
        _resource(
            "security_group",
            "sg-1",
            {
                "VpcId": "vpc-1",
                "IpPermissionsEgress": [{"IpRanges": [{"CidrIp": "0.0.0.0/0"}]}],
            },
        ),
    ]
    graph = build_network_graph(resources)
    findings = analyze_egress_exposure(graph, resources)

    assert len(findings) == 1
    assert findings[0]["finding_type"] == "internet_egress_exposure"
