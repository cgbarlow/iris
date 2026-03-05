"""Pydantic models for diagram CRUD operations."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DiagramCreate(BaseModel):
    """Request body for creating a diagram."""

    diagram_type: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    data: dict[str, object] = Field(default_factory=dict)
    parent_package_id: str | None = None
    set_id: str | None = None
    notation: str | None = None
    metadata: dict[str, object] | None = None


class DiagramUpdate(BaseModel):
    """Request body for updating a diagram."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    data: dict[str, object] = Field(default_factory=dict)
    change_summary: str | None = None
    metadata: dict[str, object] | None = None


class DiagramResponse(BaseModel):
    """Response for a single diagram."""

    id: str
    diagram_type: str
    current_version: int
    name: str
    description: str | None = None
    data: dict[str, object] = Field(default_factory=dict)
    created_at: str
    created_by: str
    created_by_username: str = "Unknown"
    updated_at: str
    is_deleted: bool = False
    parent_package_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    set_id: str | None = None
    set_name: str | None = None
    notation: str = "simple"
    detected_notations: list[str] = Field(default_factory=list)
    metadata: dict[str, object] | None = None


class DiagramHierarchyNode(BaseModel):
    """A node in the diagram hierarchy tree (packages and diagrams)."""

    id: str
    name: str
    node_type: str = "diagram"
    diagram_type: str | None = None
    notation: str | None = None
    parent_package_id: str | None = None
    has_content: bool = False
    children: list[DiagramHierarchyNode] = Field(default_factory=list)


class DiagramVersionResponse(BaseModel):
    """Response for a diagram version."""

    diagram_id: str
    version: int
    name: str
    description: str | None = None
    data: dict[str, object] = Field(default_factory=dict)
    change_type: str
    change_summary: str | None = None
    rollback_to: int | None = None
    created_at: str
    created_by: str
    created_by_username: str = "Unknown"
    metadata: dict[str, object] | None = None


class DiagramListResponse(BaseModel):
    """Paginated list of diagrams."""

    items: list[DiagramResponse]
    total: int
    page: int
    page_size: int
