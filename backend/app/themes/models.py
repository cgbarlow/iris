"""Pydantic models for the visual theme system."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ThemeConfig(BaseModel):
    """Theme configuration with element defaults and stereotype overrides."""

    model_config = {"populate_by_name": True}

    element_defaults: dict[str, dict[str, object]] = Field(default_factory=dict)
    stereotype_overrides: dict[str, dict[str, object]] = Field(default_factory=dict)
    edge_defaults: dict[str, dict[str, object]] = Field(default_factory=dict)
    global_defaults: dict[str, object] = Field(default_factory=dict, alias="global")


class ThemeCreate(BaseModel):
    """Request body for creating a theme."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    notation: str = Field(min_length=1, max_length=50)
    config: ThemeConfig = Field(default_factory=ThemeConfig)


class ThemeUpdate(BaseModel):
    """Request body for updating a theme."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    notation: str = Field(min_length=1, max_length=50)
    config: ThemeConfig = Field(default_factory=ThemeConfig)


class ThemeResponse(BaseModel):
    """Response for a single theme."""

    id: str
    name: str
    description: str | None = None
    notation: str
    config: ThemeConfig
    is_default: bool = False
    created_by: str | None = None
    created_at: str
    updated_at: str
