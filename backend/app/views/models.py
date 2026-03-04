"""Pydantic models for admin-configurable views."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ViewConfig(BaseModel):
    """View configuration controlling UI feature visibility."""

    toolbar: dict[str, object] = Field(default_factory=dict)
    metadata: dict[str, object] = Field(default_factory=dict)
    canvas: dict[str, object] = Field(default_factory=dict)


class ViewCreate(BaseModel):
    """Request body for creating a view."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    config: ViewConfig = Field(default_factory=ViewConfig)


class ViewUpdate(BaseModel):
    """Request body for updating a view."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    config: ViewConfig = Field(default_factory=ViewConfig)


class ViewResponse(BaseModel):
    """Response for a single view."""

    id: str
    name: str
    description: str | None = None
    config: ViewConfig
    is_default: bool = False
    created_by: str | None = None
    created_at: str
    updated_at: str
