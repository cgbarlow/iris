"""Pydantic models for set CRUD operations."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ADR-202 (v6.13.0): per-set hierarchy sort preference. Pydantic
# ``Literal`` enforces the enum at the API boundary so the DB column
# stays a plain TEXT (keeps SQLite ↔ Supabase migration syntax
# identical, Protocol §15).
HierarchySort = Literal["manual", "alpha", "newest", "oldest"]

# ADR-204 (v6.14.0): per-set tab defaults — which tab opens by
# default on the Packages and Views screens for a given set. Same
# Pydantic-Literal-in-TEXT-column pattern as HierarchySort.
PackageTabDefault = Literal["relationships", "details"]
ViewTabDefault = Literal["canvas", "relationships", "details"]


class SetCreate(BaseModel):
    """Request body for creating a set."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    collection_id: str | None = None


class SetUpdate(BaseModel):
    """Request body for updating a set."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    thumbnail_source: str | None = None
    thumbnail_diagram_id: str | None = None
    collection_id: str | None = None
    system_prompt: str | None = None
    mcp_system_context: str | None = None
    # None means "don't change" — preserves the existing value. Matches
    # the MCP _put_merge_partial contract and keeps existing PUT
    # clients (frontend / MCP) from accidentally resetting the field
    # when they omit it.
    hierarchy_sort: HierarchySort | None = None
    # ADR-204: per-set tab defaults; same None="leave alone" contract.
    package_tab_default: PackageTabDefault | None = None
    view_tab_default: ViewTabDefault | None = None


class SetResponse(BaseModel):
    """Response for a single set."""

    id: str
    name: str
    description: str | None = None
    created_at: str
    created_by: str
    updated_at: str
    is_deleted: bool = False
    collection_id: str | None = None
    collection_name: str | None = None
    diagram_count: int = 0
    element_count: int = 0
    # ADR-158 (v5.13.0): structural breadth signals for MCP clients.
    package_count: int = 0
    package_count_root: int = 0
    thumbnail_source: str | None = None
    thumbnail_diagram_id: str | None = None
    has_thumbnail_image: bool = False
    thumbnail_diagram_data: dict | None = None
    thumbnail_diagram_type: str | None = None
    system_prompt: str | None = None
    mcp_system_context: str | None = None
    # ADR-202 (v6.13.0): always returned, defaults to 'manual' for
    # both newly-created and pre-migration sets.
    hierarchy_sort: HierarchySort = "manual"
    # ADR-204 (v6.14.0): always returned. Defaults match the new
    # column defaults so existing rows + pre-migration callers see
    # the desired "Relationships / Canvas first" behaviour.
    package_tab_default: PackageTabDefault = "relationships"
    view_tab_default: ViewTabDefault = "canvas"


class SetListResponse(BaseModel):
    """List of sets."""

    items: list[SetResponse]


class SetForceDeleteResponse(BaseModel):
    """Response for force-deleting a set and all its contents."""

    diagrams_deleted: int
    elements_deleted: int
