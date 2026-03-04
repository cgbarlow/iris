"""Pydantic models for package CRUD operations."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PackageCreate(BaseModel):
    """Request body for creating a package."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    parent_package_id: str | None = None
    set_id: str | None = None
    metadata: dict[str, object] | None = None


class PackageUpdate(BaseModel):
    """Request body for updating a package."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    change_summary: str | None = None
    metadata: dict[str, object] | None = None


class PackageResponse(BaseModel):
    """Response for a single package."""

    id: str
    current_version: int
    name: str
    description: str | None = None
    created_at: str
    created_by: str
    created_by_username: str = "Unknown"
    updated_at: str
    is_deleted: bool = False
    parent_package_id: str | None = None
    set_id: str | None = None
    set_name: str | None = None
    metadata: dict[str, object] | None = None


class PackageHierarchyNode(BaseModel):
    """A node in the package hierarchy tree."""

    id: str
    name: str
    parent_package_id: str | None = None
    children: list[PackageHierarchyNode] = Field(default_factory=list)


class PackageVersionResponse(BaseModel):
    """Response for a package version."""

    package_id: str
    version: int
    name: str
    description: str | None = None
    data: dict[str, object] = Field(default_factory=dict)
    metadata: dict[str, object] | None = None
    change_type: str
    change_summary: str | None = None
    created_at: str
    created_by: str
    created_by_username: str = "Unknown"


class PackageListResponse(BaseModel):
    """Paginated list of packages."""

    items: list[PackageResponse]
    total: int
    page: int
    page_size: int
