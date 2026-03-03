"""Pydantic models for model CRUD operations."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ModelCreate(BaseModel):
    """Request body for creating a model."""

    model_type: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    data: dict[str, object] = Field(default_factory=dict)
    parent_model_id: str | None = None
    set_id: str | None = None
    metadata: dict[str, object] | None = None


class ModelUpdate(BaseModel):
    """Request body for updating a model."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    data: dict[str, object] = Field(default_factory=dict)
    change_summary: str | None = None
    metadata: dict[str, object] | None = None


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
    parent_model_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    set_id: str | None = None
    set_name: str | None = None
    metadata: dict[str, object] | None = None


class ModelHierarchyNode(BaseModel):
    """A node in the model hierarchy tree."""

    id: str
    name: str
    model_type: str
    parent_model_id: str | None = None
    has_content: bool = False
    children: list[ModelHierarchyNode] = Field(default_factory=list)


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
    metadata: dict[str, object] | None = None


class ModelListResponse(BaseModel):
    """Paginated list of models."""

    items: list[ModelResponse]
    total: int
    page: int
    page_size: int
