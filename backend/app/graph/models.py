"""Graph API models per SPEC-116-A."""

from __future__ import annotations

from pydantic import BaseModel


class GraphNode(BaseModel):
    """A node in the knowledge graph."""

    id: str
    name: str
    node_type: str  # 'element', 'diagram', 'package'
    type_detail: str  # element_type, diagram_type, or 'package'
    relationship_count: int = 0


class GraphEdge(BaseModel):
    """An edge in the knowledge graph."""

    id: str
    source: str
    target: str
    relationship_type: str
    label: str | None = None
    edge_type: str  # element_relationship, package_relationship, diagram_link, diagram_element, diagram_package, hierarchy


class GraphResponse(BaseModel):
    """Full graph payload for a scoped set or collection."""

    nodes: list[GraphNode]
    edges: list[GraphEdge]
