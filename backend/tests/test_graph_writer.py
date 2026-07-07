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
    statements = build_statements(resources, uuid.uuid4(), uuid.uuid4())

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
    statements = build_statements(resources, uuid.uuid4(), uuid.uuid4())

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
    statements = build_statements(resources, uuid.uuid4(), uuid.uuid4())

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
    statements = build_statements(resources, uuid.uuid4(), uuid.uuid4())

    edge_statements = [s for s in statements if "PEERED_WITH" in s[0]]
    assert edge_statements == []


def test_unknown_resource_type_falls_back_to_generic_label():
    resources = [_resource("public_ip", "eip-1")]
    statements = build_statements(resources, uuid.uuid4(), uuid.uuid4())
    assert "MERGE (n:PublicIP" in statements[0][0]


def test_build_statements_prunes_stale_nodes_per_label_and_provider():
    resources = [_resource("network", "vpc-1"), _resource("subnet", "subnet-1")]
    tenant_id = uuid.uuid4()
    statements = build_statements(resources, uuid.uuid4(), tenant_id)

    cleanup_statements = [s for s in statements if "DETACH DELETE" in s[0]]
    assert len(cleanup_statements) == 2
    by_label = {s[0]: s[1] for s in cleanup_statements}
    network_cleanup = next(p for c, p in cleanup_statements if "Network" in c)
    assert network_cleanup["native_ids"] == ["vpc-1"]
    assert network_cleanup["tenant_id"] == str(tenant_id)


def test_build_statements_scopes_nodes_and_cleanup_by_tenant():
    resources = [_resource("network", "vpc-1")]
    tenant_id = uuid.uuid4()
    statements = build_statements(resources, uuid.uuid4(), tenant_id)

    node_statement = next(s for s in statements if "MERGE (n:Network" in s[0])
    assert node_statement[1]["tenant_id"] == str(tenant_id)


def test_build_statements_creates_part_of_edge_from_subnet_to_network():
    resources = [
        _resource("network", "vpc-1"),
        _resource("subnet", "subnet-1", attributes={"VpcId": "vpc-1"}),
    ]
    statements = build_statements(resources, uuid.uuid4(), uuid.uuid4())

    part_of_statements = [s for s in statements if "PART_OF" in s[0]]
    assert len(part_of_statements) == 1
    assert part_of_statements[0][1]["native_id"] == "subnet-1"
    assert part_of_statements[0][1]["network_id"] == "vpc-1"


def test_build_statements_skips_part_of_when_owning_network_unknown():
    resources = [
        _resource("network", "vpc-1"),
        _resource("subnet", "subnet-1", attributes={"VpcId": "vpc-unknown"}),
        _resource("security_group", "sg-1", attributes={}),
    ]
    statements = build_statements(resources, uuid.uuid4(), uuid.uuid4())

    part_of_statements = [s for s in statements if "PART_OF" in s[0]]
    assert part_of_statements == []


def test_build_statements_sets_is_hub_for_selected_hub_networks():
    resources = [_resource("network", "vpc-1"), _resource("network", "vpc-2")]
    statements = build_statements(resources, uuid.uuid4(), uuid.uuid4(), hub_ids=["vpc-1"])

    hub_statements = [s for s in statements if "is_hub" in s[0]]
    assert len(hub_statements) == 1
    assert hub_statements[0][1]["native_id"] == "vpc-1"
