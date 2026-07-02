from typing import Any

from pydantic import BaseModel


class GraphNode(BaseModel):
    id: str
    labels: list[str]
    properties: dict[str, Any]


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str


class TopologyResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class SubgraphResponse(BaseModel):
    nodes: list[GraphNode]


class PathResponse(BaseModel):
    nodes: list[GraphNode]
