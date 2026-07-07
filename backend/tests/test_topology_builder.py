from app.ai_engine.topology_builder import summarize_topology_for_ai
from app.schemas.graph import GraphEdge, GraphNode


def test_summarize_topology_for_ai_with_no_nodes():
    assert summarize_topology_for_ai([], []) == "No topology data available for this job."


def test_summarize_topology_for_ai_counts_labels_hubs_and_edges():
    nodes = [
        GraphNode(id="1", labels=["Network"], properties={"is_hub": True, "name": "hub-vpc"}),
        GraphNode(id="2", labels=["Network"], properties={"native_id": "vpc-2"}),
        GraphNode(id="3", labels=["Subnet"], properties={"native_id": "subnet-1"}),
    ]
    edges = [GraphEdge(id="e1", source="3", target="2", type="PART_OF")]

    summary = summarize_topology_for_ai(nodes, edges)

    assert "Network: 2" in summary
    assert "Subnet: 1" in summary
    assert "hub-vpc" in summary
    assert "PART_OF: 1" in summary
