"""Pydantic models for collection CRUD operations."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CollectionCreate(BaseModel):
    """Request body for creating a collection."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class CollectionUpdate(BaseModel):
    """Request body for updating a collection."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    thumbnail_source: str | None = None
    thumbnail_diagram_id: str | None = None
    system_prompt: str | None = None
    mcp_system_context: str | None = None


class CollectionResponse(BaseModel):
    """Response for a single collection."""

    id: str
    name: str
    description: str | None = None
    created_at: str
    created_by: str
    updated_at: str
    is_deleted: bool = False
    set_count: int = 0
    diagram_count: int = 0
    element_count: int = 0
    thumbnail_source: str | None = None
    thumbnail_diagram_id: str | None = None
    has_thumbnail_image: bool = False
    thumbnail_diagram_data: dict | None = None
    thumbnail_diagram_type: str | None = None
    system_prompt: str | None = None
    mcp_system_context: str | None = None


class CollectionListResponse(BaseModel):
    """List of collections."""

    items: list[CollectionResponse]
