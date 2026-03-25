"""Pydantic models for Scenia roadmapping entities."""

from __future__ import annotations

from pydantic import BaseModel, Field


# --- Entity request/response models ---


class SceniaEntityCreate(BaseModel):
    """Generic create body for a Scenia entity stored as an Iris element."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    data: dict[str, object] = Field(default_factory=dict)
    set_id: str


class SceniaEntityUpdate(BaseModel):
    """Generic update body for a Scenia entity."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    data: dict[str, object] = Field(default_factory=dict)


class SceniaEntityResponse(BaseModel):
    """Response for a single Scenia entity (backed by an Iris element)."""

    id: str
    element_type: str
    name: str
    description: str | None = None
    data: dict[str, object] = Field(default_factory=dict)
    set_id: str | None = None
    created_at: str
    updated_at: str


class SceniaEntityListResponse(BaseModel):
    """List of Scenia entities."""

    items: list[SceniaEntityResponse]


# --- Dependency (relationship-backed) ---


class SceniaDependencyCreate(BaseModel):
    """Create body for a Scenia dependency (stored as Iris relationship)."""

    source_id: str
    target_id: str
    dependency_type: str = "blocks"
    set_id: str
    data: dict[str, object] = Field(default_factory=dict)


class SceniaDependencyResponse(BaseModel):
    """Response for a Scenia dependency."""

    id: str
    source_id: str
    target_id: str
    dependency_type: str
    set_id: str | None = None
    data: dict[str, object] = Field(default_factory=dict)
    created_at: str


class SceniaDependencyListResponse(BaseModel):
    """List of Scenia dependencies."""

    items: list[SceniaDependencyResponse]


# --- Timeline settings ---


class TimelineSettingsUpdate(BaseModel):
    """Update body for timeline settings."""

    start_date: str | None = None
    end_date: str | None = None
    view_mode: str = "quarterly"
    zoom_level: float = 1.0
    data: dict[str, object] = Field(default_factory=dict)


class TimelineSettingsResponse(BaseModel):
    """Response for timeline settings."""

    id: str
    set_id: str
    start_date: str | None = None
    end_date: str | None = None
    view_mode: str = "quarterly"
    zoom_level: float = 1.0
    data: dict[str, object] = Field(default_factory=dict)
    updated_at: str


# --- Asset categories ---


class AssetCategoryCreate(BaseModel):
    """Create body for an asset category."""

    name: str = Field(min_length=1, max_length=255)
    color: str | None = None
    display_order: int = 0
    set_id: str


class AssetCategoryResponse(BaseModel):
    """Response for an asset category."""

    id: str
    set_id: str
    name: str
    color: str | None = None
    display_order: int = 0


class AssetCategoryListResponse(BaseModel):
    """List of asset categories."""

    items: list[AssetCategoryResponse]


# --- Application statuses ---


class AppStatusCreate(BaseModel):
    """Create body for an application status."""

    name: str = Field(min_length=1, max_length=255)
    color: str | None = None
    display_order: int = 0
    set_id: str


class AppStatusResponse(BaseModel):
    """Response for an application status."""

    id: str
    set_id: str
    name: str
    color: str | None = None
    display_order: int = 0


class AppStatusListResponse(BaseModel):
    """List of application statuses."""

    items: list[AppStatusResponse]


# --- Versions ---


class VersionCreate(BaseModel):
    """Create body for a version snapshot."""

    name: str | None = None
    data: dict[str, object] = Field(default_factory=dict)
    set_id: str


class VersionResponse(BaseModel):
    """Response for a version snapshot."""

    id: str
    set_id: str
    version_number: int
    name: str | None = None
    data: dict[str, object] = Field(default_factory=dict)
    created_at: str
    created_by: str


class VersionListResponse(BaseModel):
    """List of version snapshots."""

    items: list[VersionResponse]


# --- Bulk data (the primary integration point) ---


class SceniaBulkData(BaseModel):
    """Full roadmap data for a set — matches Scenia's getAppData() shape."""

    strategies: list[SceniaEntityResponse] = Field(default_factory=list)
    programmes: list[SceniaEntityResponse] = Field(default_factory=list)
    initiatives: list[SceniaEntityResponse] = Field(default_factory=list)
    assets: list[SceniaEntityResponse] = Field(default_factory=list)
    applications: list[SceniaEntityResponse] = Field(default_factory=list)
    app_segments: list[SceniaEntityResponse] = Field(default_factory=list)
    milestones: list[SceniaEntityResponse] = Field(default_factory=list)
    resources: list[SceniaEntityResponse] = Field(default_factory=list)
    dependencies: list[SceniaDependencyResponse] = Field(default_factory=list)
    asset_categories: list[AssetCategoryResponse] = Field(default_factory=list)
    app_statuses: list[AppStatusResponse] = Field(default_factory=list)
    timeline_settings: TimelineSettingsResponse | None = None
    versions: list[VersionResponse] = Field(default_factory=list)


class SceniaBulkDataWrite(BaseModel):
    """Bulk write payload — atomic save of all Scenia data for a set."""

    strategies: list[SceniaEntityCreate] = Field(default_factory=list)
    programmes: list[SceniaEntityCreate] = Field(default_factory=list)
    initiatives: list[SceniaEntityCreate] = Field(default_factory=list)
    assets: list[SceniaEntityCreate] = Field(default_factory=list)
    applications: list[SceniaEntityCreate] = Field(default_factory=list)
    app_segments: list[SceniaEntityCreate] = Field(default_factory=list)
    milestones: list[SceniaEntityCreate] = Field(default_factory=list)
    resources: list[SceniaEntityCreate] = Field(default_factory=list)
    dependencies: list[SceniaDependencyCreate] = Field(default_factory=list)
    asset_categories: list[AssetCategoryCreate] = Field(default_factory=list)
    app_statuses: list[AppStatusCreate] = Field(default_factory=list)
    timeline_settings: TimelineSettingsUpdate | None = None
