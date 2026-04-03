"""Graph API models per SPEC-116-A."""

from __future__ import annotations

from pydantic import BaseModel, Field


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


class GraphDisplaySettings(BaseModel):
    """Full graph display settings including physics multipliers."""

    nodes: dict[str, bool] = Field(default_factory=lambda: {
        "collection": True, "set": True, "package": True, "diagram": True, "element": True
    })
    edges: dict[str, bool] = Field(default_factory=lambda: {
        "collection_membership": True, "set_membership": True, "direct_diagram_links": True,
        "hierarchy": True, "diagram_element": True, "diagram_package": True,
        "diagram_link": True, "package_relationship": True, "element_relationship": True,
    })
    label_density: int = Field(default=10, ge=1, le=50)
    node_spacing: float = Field(default=1.0, ge=0.2, le=3.0)
    size_contrast: float = Field(default=1.0, ge=0.0, le=3.0)
    link_length: float = Field(default=1.0, ge=0.2, le=3.0)


class GraphSettingsResponse(BaseModel):
    """Persisted graph settings for a specific scope."""

    scope_type: str
    scope_id: str
    settings: GraphDisplaySettings
    updated_at: str | None = None
    updated_by: str | None = None


class GraphSettingsUpdate(BaseModel):
    """Payload to create or update graph settings."""

    scope_type: str = "global"
    scope_id: str = "__global__"
    settings: GraphDisplaySettings
