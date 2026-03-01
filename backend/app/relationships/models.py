"""Pydantic models for relationship CRUD operations."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RelationshipCreate(BaseModel):
    """Request body for creating a relationship."""

    source_entity_id: str
    target_entity_id: str
    relationship_type: str = Field(min_length=1)
    label: str | None = None
    description: str | None = None
    data: dict[str, object] = Field(default_factory=dict)


class RelationshipUpdate(BaseModel):
    """Request body for updating a relationship."""

    label: str | None = None
    description: str | None = None
    data: dict[str, object] = Field(default_factory=dict)
    change_summary: str | None = None


class RelationshipResponse(BaseModel):
    """Response for a single relationship."""

    id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type: str
    current_version: int
    label: str | None = None
    description: str | None = None
    data: dict[str, object] = Field(default_factory=dict)
    created_at: str
    created_by: str
    updated_at: str
    is_deleted: bool = False
    source_entity_name: str = ""
    target_entity_name: str = ""


class RelationshipVersionResponse(BaseModel):
    """Response for a relationship version."""

    relationship_id: str
    version: int
    label: str | None = None
    description: str | None = None
    data: dict[str, object] = Field(default_factory=dict)
    change_type: str
    change_summary: str | None = None
    rollback_to: int | None = None
    created_at: str
    created_by: str


class RelationshipListResponse(BaseModel):
    """Paginated list of relationships."""

    items: list[RelationshipResponse]
    total: int
    page: int
    page_size: int
