import uuid

from app.graph_engine.writer import GraphResourceInput, build_statements


def _resource(resource_type, native_id, attributes=None, provider="aws"):
    return GraphResourceInput(
        id=uuid.uuid4(),
        resource_type=resource_type,
        provider=provider,
        native_id=native_id,
        name=None,
        attributes=attributes or {},
    )


def test_build_statements_creates_a_merge_per_resource():
    resources = [_resource("network", "vpc-1"), _resource("subnet", "subnet-1")]
    statements = build_statements(resources, uuid.uuid4())

    node_statements = [s for s in statements if "MERGE (n:" in s[0]]
    assert len(node_statements) == 2
    assert "MERGE (n:Network" in node_statements[0][0]
    assert node_statements[0][1]["native_id"] == "vpc-1"


def test_build_statements_creates_peering_edge_between_known_networks():
    resources = [
        _resource("network", "vpc-a"),
        _resource("network", "vpc-b"),
        _resource(
            "peering_connection",
            "pcx-1",
            attributes={
                "RequesterVpcInfo": {"VpcId": "vpc-a"},
                "AccepterVpcInfo": {"VpcId": "vpc-b"},
            },
        ),
    ]
    statements = build_statements(resources, uuid.uuid4())

    edge_statements = [s for s in statements if "PEERED_WITH" in s[0]]
    assert len(edge_statements) == 1
    assert edge_statements[0][1]["source_id"] == "vpc-a"
    assert edge_statements[0][1]["target_id"] == "vpc-b"


def test_build_statements_skips_peering_to_unknown_network():
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
    statements = build_statements(resources, uuid.uuid4())

    edge_statements = [s for s in statements if "PEERED_WITH" in s[0]]
    assert edge_statements == []


def test_build_statements_skips_self_peering():
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
    statements = build_statements(resources, uuid.uuid4())

    edge_statements = [s for s in statements if "PEERED_WITH" in s[0]]
    assert edge_statements == []


def test_unknown_resource_type_falls_back_to_generic_label():
    resources = [_resource("public_ip", "eip-1")]
    statements = build_statements(resources, uuid.uuid4())
    assert "MERGE (n:PublicIP" in statements[0][0]
