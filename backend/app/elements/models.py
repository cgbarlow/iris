"""Pydantic models for element CRUD operations."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# Sentinel for tri-state "package_id" on ElementUpdate. We can't use
# ``None`` to mean "do not touch" because callers may legitimately set
# the value to ``None`` to clear membership. The sentinel resolves the
# ambiguity at the model boundary.
_UNSET: Any = object()


class ElementCreate(BaseModel):
    """Request body for creating an element.

    ``template_id`` (v6.8.0, ADR-191) pre-fills any whitelisted fields
    from the named template. Explicit fields on the request always
    win over template defaults.
    """

    element_type: str = Field(default="", min_length=0)
    name: str = Field(default="", min_length=0, max_length=255)
    description: str | None = None
    data: dict[str, object] = Field(default_factory=dict)
    set_id: str | None = None
    package_id: str | None = None
    metadata: dict[str, object] | None = None
    notation: str = "simple"
    template_id: str | None = None


class ElementUpdate(BaseModel):
    """Request body for updating an element.

    ``package_id`` is tri-state: omit the key to leave the column
    untouched, pass ``null`` (JSON) to clear, or pass a string to set.
    The router translates these three states into a kwarg passed to the
    service layer.
    """

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    data: dict[str, object] = Field(default_factory=dict)
    change_summary: str | None = None
    metadata: dict[str, object] | None = None
    package_id: Any = _UNSET


class ElementRollback(BaseModel):
    """Request body for rolling back an element to a previous version."""

    target_version: int = Field(ge=1)


class ElementResponse(BaseModel):
    """Response for a single element."""

    id: str
    element_type: str
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
    relationship_count: int = 0
    diagram_usage_count: int = 0
    set_id: str | None = None
    set_name: str | None = None
    package_id: str | None = None
    package_name: str | None = None
    metadata: dict[str, object] | None = None
    notation: str = "simple"


class ElementVersionResponse(BaseModel):
    """Response for an element version."""

    element_id: str
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


class ElementListResponse(BaseModel):
    """Paginated list of elements."""

    items: list[ElementResponse]
    total: int
    page: int
    page_size: int
