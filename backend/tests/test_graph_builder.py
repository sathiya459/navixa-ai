import uuid

from app.hub_spoke_validator.graph_builder import build_network_graph
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


def test_builds_attached_to_edge_for_igw_attachment():
    resources = [
        _resource("network", "vpc-1", {}),
        _resource("gateway", "igw-1", {"Attachments": [{"VpcId": "vpc-1", "State": "available"}]}),
    ]
    graph = build_network_graph(resources)
    assert graph.has_edge("vpc-1", "igw-1", key="ATTACHED_TO")


def test_builds_attached_to_edge_for_nat_gateway_direct_vpc_id():
    resources = [
        _resource("network", "vpc-1", {}),
        _resource("gateway", "nat-1", {"VpcId": "vpc-1"}),
    ]
    graph = build_network_graph(resources)
    assert graph.has_edge("vpc-1", "nat-1")


def test_builds_routes_to_edge_from_route_table():
    resources = [
        _resource("network", "vpc-1", {}),
        _resource(
            "route_table",
            "rtb-1",
            {"VpcId": "vpc-1", "Routes": [{"DestinationCidrBlock": "0.0.0.0/0", "GatewayId": "igw-1"}]},
        ),
    ]
    graph = build_network_graph(resources)
    assert any(
        edata.get("relation") == "ROUTES_TO" for edata in graph.get_edge_data("vpc-1", "igw-1").values()
    )


def test_attached_to_and_routes_to_coexist_between_same_vpc_and_gateway():
    """Regression test: a plain DiGraph only keeps one edge per node pair,
    so ROUTES_TO would silently overwrite ATTACHED_TO between the same
    VPC/gateway - MultiDiGraph must preserve both."""
    resources = [
        _resource("network", "vpc-1", {}),
        _resource("gateway", "igw-1", {"Attachments": [{"VpcId": "vpc-1", "State": "available"}]}),
        _resource(
            "route_table",
            "rtb-1",
            {"VpcId": "vpc-1", "Routes": [{"DestinationCidrBlock": "0.0.0.0/0", "GatewayId": "igw-1"}]},
        ),
    ]
    graph = build_network_graph(resources)
    relations = {edata["relation"] for edata in graph.get_edge_data("vpc-1", "igw-1").values()}
    assert relations == {"ATTACHED_TO", "ROUTES_TO"}


def test_builds_bidirectional_peered_with_edges():
    resources = [
        _resource("network", "vpc-a", {}),
        _resource("network", "vpc-b", {}),
        _resource(
            "peering_connection",
            "pcx-1",
            {"RequesterVpcInfo": {"VpcId": "vpc-a"}, "AccepterVpcInfo": {"VpcId": "vpc-b"}},
        ),
    ]
    graph = build_network_graph(resources)
    assert graph.has_edge("vpc-a", "vpc-b")
    assert graph.has_edge("vpc-b", "vpc-a")
