"""Pydantic models for entity CRUD operations."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EntityCreate(BaseModel):
    """Request body for creating an entity."""

    entity_type: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    data: dict[str, object] = Field(default_factory=dict)


class EntityUpdate(BaseModel):
    """Request body for updating an entity."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    data: dict[str, object] = Field(default_factory=dict)
    change_summary: str | None = None


class EntityRollback(BaseModel):
    """Request body for rolling back an entity to a previous version."""

    target_version: int = Field(ge=1)


class EntityResponse(BaseModel):
    """Response for a single entity."""

    id: str
    entity_type: str
    current_version: int
    name: str
    description: str | None = None
    data: dict[str, object] = Field(default_factory=dict)
    created_at: str
    created_by: str
    updated_at: str
    is_deleted: bool = False


class EntityVersionResponse(BaseModel):
    """Response for an entity version."""

    entity_id: str
    version: int
    name: str
    description: str | None = None
    data: dict[str, object] = Field(default_factory=dict)
    change_type: str
    change_summary: str | None = None
    rollback_to: int | None = None
    created_at: str
    created_by: str


class EntityListResponse(BaseModel):
    """Paginated list of entities."""

    items: list[EntityResponse]
    total: int
    page: int
    page_size: int
