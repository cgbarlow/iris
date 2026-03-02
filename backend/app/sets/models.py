"""Pydantic models for set CRUD operations."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SetCreate(BaseModel):
    """Request body for creating a set."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class SetUpdate(BaseModel):
    """Request body for updating a set."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    thumbnail_source: str | None = None
    thumbnail_model_id: str | None = None


class SetResponse(BaseModel):
    """Response for a single set."""

    id: str
    name: str
    description: str | None = None
    created_at: str
    created_by: str
    updated_at: str
    is_deleted: bool = False
    model_count: int = 0
    entity_count: int = 0
    thumbnail_source: str | None = None
    thumbnail_model_id: str | None = None
    has_thumbnail_image: bool = False


class SetListResponse(BaseModel):
    """List of sets."""

    items: list[SetResponse]


class SetForceDeleteResponse(BaseModel):
    """Response for force-deleting a set and all its contents."""

    models_deleted: int
    entities_deleted: int
