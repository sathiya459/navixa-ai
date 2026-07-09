import uuid

from app.graph_engine.topology_service import build_topology
from app.graph_engine.writer import GraphResourceInput


def _resource(resource_type, native_id, attributes=None, provider="aws"):
    return GraphResourceInput(
        id=uuid.uuid4(),
        resource_type=resource_type,
        provider=provider,
        native_id=native_id,
        name=None,
        attributes=attributes or {},
    )


def test_build_topology_creates_a_node_per_resource():
    resources = [_resource("network", "vpc-1"), _resource("subnet", "subnet-1")]
    topology = build_topology(resources)

    assert len(topology["nodes"]) == 2
    network_node = next(n for n in topology["nodes"] if n["labels"] == ["Network"])
    assert network_node["properties"]["native_id"] == "vpc-1"


def test_build_topology_creates_peering_edge_between_known_networks():
    vpc_a = _resource("network", "vpc-a")
    vpc_b = _resource("network", "vpc-b")
    resources = [
        vpc_a,
        vpc_b,
        _resource(
            "peering_connection",
            "pcx-1",
            attributes={
                "RequesterVpcInfo": {"VpcId": "vpc-a"},
                "AccepterVpcInfo": {"VpcId": "vpc-b"},
            },
        ),
    ]
    topology = build_topology(resources)

    edges = [e for e in topology["edges"] if e["type"] == "PEERED_WITH"]
    assert len(edges) == 1
    assert edges[0]["source"] == str(vpc_a.id)
    assert edges[0]["target"] == str(vpc_b.id)


def test_build_topology_skips_peering_to_unknown_network():
    resources = [
        _resource("network", "vpc-a"),
        _resource(
            "peering_connection",
            "pcx-1",
            attributes={
                "RequesterVpcInfo": {"VpcId": "vpc-a"},
                "AccepterVpcInfo": {"VpcId": "vpc-unknown"},
            },
        ),
    ]
    topology = build_topology(resources)

    assert [e for e in topology["edges"] if e["type"] == "PEERED_WITH"] == []


def test_build_topology_skips_self_peering():
    resources = [
        _resource("network", "vpc-a"),
        _resource(
            "peering_connection",
            "pcx-1",
            attributes={
                "RequesterVpcInfo": {"VpcId": "vpc-a"},
                "AccepterVpcInfo": {"VpcId": "vpc-a"},
            },
        ),
    ]
    topology = build_topology(resources)

    assert [e for e in topology["edges"] if e["type"] == "PEERED_WITH"] == []


def test_unknown_resource_type_falls_back_to_generic_label():
    resources = [_resource("public_ip", "eip-1")]
    topology = build_topology(resources)
    assert topology["nodes"][0]["labels"] == ["PublicIP"]


def test_build_topology_creates_part_of_edge_from_subnet_to_network():
    vpc = _resource("network", "vpc-1")
    subnet = _resource("subnet", "subnet-1", attributes={"VpcId": "vpc-1"})
    resources = [vpc, subnet]
    topology = build_topology(resources)

    part_of_edges = [e for e in topology["edges"] if e["type"] == "PART_OF"]
    assert len(part_of_edges) == 1
    assert part_of_edges[0]["source"] == str(subnet.id)
    assert part_of_edges[0]["target"] == str(vpc.id)


def test_build_topology_skips_part_of_when_owning_network_unknown():
    resources = [
        _resource("network", "vpc-1"),
        _resource("subnet", "subnet-1", attributes={"VpcId": "vpc-unknown"}),
        _resource("security_group", "sg-1", attributes={}),
    ]
    topology = build_topology(resources)

    assert [e for e in topology["edges"] if e["type"] == "PART_OF"] == []


def test_build_topology_sets_is_hub_for_selected_hub_networks():
    resources = [_resource("network", "vpc-1"), _resource("network", "vpc-2")]
    topology = build_topology(resources, hub_ids=["vpc-1"])

    hub_nodes = [n for n in topology["nodes"] if n["properties"].get("is_hub")]
    assert len(hub_nodes) == 1
    assert hub_nodes[0]["properties"]["native_id"] == "vpc-1"
