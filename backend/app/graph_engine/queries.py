"""Read-side Cypher queries for NAVIXA Graph API endpoints."""

import uuid
from typing import Any

from neo4j import Driver


def get_job_topology(driver: Driver, audit_job_id: uuid.UUID) -> dict[str, list[dict[str, Any]]]:
    query = """
    MATCH (n) WHERE n.audit_job_id = $audit_job_id
    OPTIONAL MATCH (n)-[r]->(m) WHERE m.audit_job_id = $audit_job_id
    RETURN n, r, m
    """
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []

    with driver.session(database="navixa_graph") as session:
        result = session.run(query, {"audit_job_id": str(audit_job_id)})
        for record in result:
            n = record["n"]
            nodes[n.element_id] = _node_to_dict(n)
            m = record["m"]
            r = record["r"]
            if m is not None and r is not None:
                nodes[m.element_id] = _node_to_dict(m)
                edges.append(
                    {
                        "id": r.element_id,
                        "source": n.element_id,
                        "target": m.element_id,
                        "type": r.type,
                    }
                )

    return {"nodes": list(nodes.values()), "edges": edges}


def get_node_neighbors(driver: Driver, node_id: str, depth: int = 1) -> dict[str, list[dict[str, Any]]]:
    query = f"""
    MATCH (n) WHERE elementId(n) = $node_id
    OPTIONAL MATCH path = (n)-[*1..{depth}]-(neighbor)
    RETURN n, neighbor
    """
    nodes: dict[str, dict[str, Any]] = {}

    with driver.session(database="navixa_graph") as session:
        result = session.run(query, {"node_id": node_id})
        for record in result:
            n = record["n"]
            nodes[n.element_id] = _node_to_dict(n)
            neighbor = record["neighbor"]
            if neighbor is not None:
                nodes[neighbor.element_id] = _node_to_dict(neighbor)

    return {"nodes": list(nodes.values())}


def get_shortest_paths(driver: Driver, source_id: str, target_id: str) -> list[list[dict[str, Any]]]:
    query = """
    MATCH (a), (b) WHERE elementId(a) = $source_id AND elementId(b) = $target_id
    MATCH path = shortestPath((a)-[*..15]-(b))
    RETURN [node IN nodes(path) | node] AS path_nodes
    """
    paths: list[list[dict[str, Any]]] = []

    with driver.session(database="navixa_graph") as session:
        result = session.run(query, {"source_id": source_id, "target_id": target_id})
        for record in result:
            paths.append([_node_to_dict(node) for node in record["path_nodes"]])

    return paths


def _node_to_dict(node) -> dict[str, Any]:
    return {
        "id": node.element_id,
        "labels": list(node.labels),
        "properties": dict(node),
    }
