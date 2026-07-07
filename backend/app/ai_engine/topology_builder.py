"""Summarizes a job's NAVIXA Graph topology for the `topology_explanation`
NAVIXA InsightAI insight type (see ai_engine/service.py).

Deliberately narration-only: the AI is given the graph's already-built
nodes/edges (deterministic, from graph_engine/writer.py) and asked only to
describe their shape in plain language - it never proposes or infers
relationships itself, since this is a security-relevant graph and an LLM
guessing at connectivity would be actively misleading.
"""

from app.schemas.graph import GraphEdge, GraphNode


def summarize_topology_for_ai(nodes: list[GraphNode], edges: list[GraphEdge]) -> str:
    if not nodes:
        return "No topology data available for this job."

    label_counts: dict[str, int] = {}
    hub_names: list[str] = []
    for node in nodes:
        label = node.labels[0] if node.labels else "Resource"
        label_counts[label] = label_counts.get(label, 0) + 1
        if node.properties.get("is_hub"):
            hub_names.append(
                node.properties.get("name") or node.properties.get("native_id", "unknown")
            )

    edge_type_counts: dict[str, int] = {}
    for edge in edges:
        edge_type_counts[edge.type] = edge_type_counts.get(edge.type, 0) + 1

    lines = ["Resource counts by type:"]
    lines += [f"  - {label}: {count}" for label, count in label_counts.items()]
    lines.append(
        f"\nDesignated hub network(s): {', '.join(hub_names) if hub_names else 'none designated'}"
    )
    lines.append("\nRelationship counts by type:")
    lines += [f"  - {edge_type}: {count}" for edge_type, count in edge_type_counts.items()]
    if not edge_type_counts:
        lines.append("  - none")

    return "\n".join(lines)
