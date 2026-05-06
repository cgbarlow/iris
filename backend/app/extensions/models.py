"""Pydantic models for the extensions registry."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExtensionInstall(BaseModel):
    """Request body for installing an extension."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    version: str = Field(min_length=1, max_length=50)
    config: dict[str, object] = Field(default_factory=dict)
    # v5.5.0 (issue #48): source tracking — optional in the request body
    # so existing clients keep working; defaults are populated server-side
    # from the sources.json registry.
    source_method: str | None = None
    source_url: str | None = None


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
    # v5.5.0 (issue #48): source-of-truth fields. `latest_version` is
    # populated by the check-update endpoint and the daily scanner.
    source_method: str = "local"
    source_url: str | None = None
    latest_version: str | None = None
    latest_version_checked_at: str | None = None


class ExtensionListResponse(BaseModel):
    """List of extensions."""

    items: list[ExtensionResponse]


class CheckUpdateResponse(BaseModel):
    """Response for POST /api/extensions/{id}/check-update."""

    id: str
    installed_version: str
    latest_version: str | None
    latest_version_checked_at: str
    update_available: bool
    source_url: str | None = None
