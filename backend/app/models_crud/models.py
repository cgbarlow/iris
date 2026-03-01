"""Pydantic models for model CRUD operations."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ModelCreate(BaseModel):
    """Request body for creating a model."""

    model_type: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    data: dict[str, object] = Field(default_factory=dict)


class ModelUpdate(BaseModel):
    """Request body for updating a model."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    data: dict[str, object] = Field(default_factory=dict)
    change_summary: str | None = None


class ModelResponse(BaseModel):
    """Response for a single model."""

    id: str
    model_type: str
    current_version: int
    name: str
    description: str | None = None
    data: dict[str, object] = Field(default_factory=dict)
    created_at: str
    created_by: str
    created_by_username: str = "Unknown"
    updated_at: str
    is_deleted: bool = False
    tags: list[str] = Field(default_factory=list)


class ModelVersionResponse(BaseModel):
    """Response for a model version."""

    model_id: str
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


class ModelListResponse(BaseModel):
    """Paginated list of models."""

    items: list[ModelResponse]
    total: int
    page: int
    page_size: int
