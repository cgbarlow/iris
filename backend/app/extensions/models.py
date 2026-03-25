"""Pydantic models for the extensions registry."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExtensionInstall(BaseModel):
    """Request body for installing an extension."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    version: str = Field(min_length=1, max_length=50)
    config: dict[str, object] = Field(default_factory=dict)


class ExtensionResponse(BaseModel):
    """Response for a single extension."""

    id: str
    name: str
    description: str | None = None
    version: str
    is_enabled: bool = True
    installed_at: str
    installed_by: str
    updated_at: str
    config: dict[str, object] = Field(default_factory=dict)


class ExtensionListResponse(BaseModel):
    """List of extensions."""

    items: list[ExtensionResponse]
