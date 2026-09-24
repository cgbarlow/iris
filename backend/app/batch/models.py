"""Pydantic models for batch operations."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.elements.models import _UNSET


class BatchIds(BaseModel):
    """Request body with a list of IDs for batch operations."""

    ids: list[str] = Field(min_length=1, max_length=100)


class BatchModifySet(BaseModel):
    """Request body for batch set reassignment."""

    ids: list[str] = Field(min_length=1, max_length=100)
    set_id: str


class BatchModifyTags(BaseModel):
    """Request body for batch tag modification."""

    ids: list[str] = Field(min_length=1, max_length=100)
    add_tags: list[str] = Field(default_factory=list)
    remove_tags: list[str] = Field(default_factory=list)


class BatchResult(BaseModel):
    """Response for batch operations."""

    succeeded: int = 0
    failed: int = 0
    errors: list[str] = Field(default_factory=list)


# ── v6.10.0 / ADR-200 / issue #173 item 6 ────────────────────────────
# Bulk element create + update so MCP clients can ship many items in
# one call. Per-item failure isolation; the response envelope includes
# the ids of items that succeeded so callers can chase up the failures
# by index.


class BatchElementCreateItem(BaseModel):
    """Per-item element create payload for batch create.

    Mirrors ``ElementCreate`` but with all fields optional at the model
    boundary so we can surface validation failures as per-item errors
    rather than rejecting the whole batch on one bad row.
    """

    element_type: str = ""
    name: str = Field(default="", max_length=255)
    description: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    set_id: str | None = None
    package_id: str | None = None
    metadata: dict[str, Any] | None = None
    notation: str = "simple"


class BatchElementsCreate(BaseModel):
    """Request body for POST /api/batch/elements/create."""

    elements: list[BatchElementCreateItem] = Field(min_length=1, max_length=100)


class BatchElementUpdateItem(BaseModel):
    """Per-item element update payload.

    ``element_id`` and ``expected_version`` are the per-item analogues
    of the URL path arg + ``If-Match`` header on the singular endpoint.
    ``package_id`` is tri-state: omit to leave untouched, send null to
    clear, send a UUID to set (uses the same _UNSET sentinel as
    ElementUpdate).
    """

    element_id: str
    expected_version: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    change_summary: str | None = None
    metadata: dict[str, Any] | None = None
    package_id: Any = _UNSET


class BatchElementsUpdate(BaseModel):
    """Request body for POST /api/batch/elements/update."""

    updates: list[BatchElementUpdateItem] = Field(min_length=1, max_length=100)


class BatchResultWithIds(BatchResult):
    """Response for batch operations that return the ids of successful items."""

    ids: list[str] = Field(default_factory=list)


# ── v6.50.0 / ADR-249 / issue #298 ───────────────────────────────────
# Bulk relationship create for MCP / CLI agents.


class BatchRelationshipCreateItem(BaseModel):
    """Per-item relationship create payload for batch create.

    Mirrors ``RelationshipCreate`` plus UML role names, with every field
    optional at the model boundary so a bad row surfaces as a per-item
    error instead of rejecting the whole batch. ``source_role`` /
    ``target_role`` are stored as ``data.sourceRole`` / ``data.targetRole``
    (the canvas / Sparx-importer convention).
    """

    source_element_id: str = ""
    target_element_id: str = ""
    relationship_type: str = ""
    source_role: str | None = None
    target_role: str | None = None
    label: str | None = None
    description: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class BatchRelationshipsCreate(BaseModel):
    """Request body for POST /api/batch/relationships/create."""

    relationships: list[BatchRelationshipCreateItem] = Field(
        min_length=1, max_length=100,
    )
