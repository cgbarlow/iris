"""Pydantic models for relationship CRUD operations."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RelationshipCreate(BaseModel):
    """Request body for creating a relationship."""

    source_element_id: str
    target_element_id: str
    relationship_type: str = Field(min_length=1)
    label: str | None = None
    description: str | None = None
    data: dict[str, object] = Field(default_factory=dict)


class RelationshipUpdate(BaseModel):
    """Request body for updating a relationship.

    ``label`` / ``description`` / ``data`` are full-replace (omitting ``data``
    stores ``{}``), unchanged since SPEC-003-A.

    ADR-249 (v6.50.0): ``relationship_type`` is updatable — omit (or send
    null) to keep the current type. ``source_role`` / ``target_role`` are
    merged into ``data.sourceRole`` / ``data.targetRole`` (the canvas / Sparx
    convention); omit to take ``data`` as sent, send ``""`` to clear.
    """

    label: str | None = None
    description: str | None = None
    data: dict[str, object] = Field(default_factory=dict)
    change_summary: str | None = None
    relationship_type: str | None = Field(default=None, min_length=1)
    source_role: str | None = None
    target_role: str | None = None


class RelationshipResponse(BaseModel):
    """Response for a single relationship."""

    id: str
    source_element_id: str
    target_element_id: str
    relationship_type: str
    current_version: int
    label: str | None = None
    description: str | None = None
    data: dict[str, object] = Field(default_factory=dict)
    created_at: str
    created_by: str
    updated_at: str
    is_deleted: bool = False
    source_element_name: str = ""
    target_element_name: str = ""
    # ADR-249: UML role names, read from data.sourceRole / data.targetRole
    # (the canvas / Sparx-importer convention) so list consumers don't have
    # to know the data keys. ``data`` remains the source of truth.
    source_role: str | None = None
    target_role: str | None = None


class RelationshipVersionResponse(BaseModel):
    """Response for a relationship version."""

    relationship_id: str
    version: int
    label: str | None = None
    description: str | None = None
    data: dict[str, object] = Field(default_factory=dict)
    change_type: str
    change_summary: str | None = None
    rollback_to: int | None = None
    created_at: str
    created_by: str


class RelationshipListResponse(BaseModel):
    """Paginated list of relationships."""

    items: list[RelationshipResponse]
    total: int
    page: int
    page_size: int
