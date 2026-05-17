"""Pydantic models for element templates (ADR-191, issue #153)."""

from __future__ import annotations

from pydantic import BaseModel, Field

# Whitelist of element fields that may be captured into a template.
# Anything outside this set is dropped from `included_fields` at write
# time (so attackers can't smuggle arbitrary keys into `template_data`).
INCLUDED_FIELD_WHITELIST: frozenset[str] = frozenset({
    "name",
    "description",
    "element_type",
    "notation",
    "data",
    "metadata",
    "package_id",
    "tags",
})


class ElementTemplateCreate(BaseModel):
    """Request body for creating an element template.

    ``source_element_id`` is required: v1 templates are always captured
    from an existing element. ``set_id`` and ``is_global`` are
    mutually exclusive — exactly one must produce a non-null scope
    (enforced by the DB CHECK constraint and the service layer).
    """

    source_element_id: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    included_fields: list[str] = Field(min_length=1)
    set_id: str | None = None
    is_global: bool = False


class ElementTemplateUpdate(BaseModel):
    """Request body for editing an element template.

    All fields optional; absent fields are not touched. ``set_id`` and
    ``is_global`` can be flipped to promote a template global or
    demote it back (the CHECK constraint validates the resulting
    state).
    """

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    included_fields: list[str] | None = None
    set_id: str | None = None
    is_global: bool | None = None


class ElementTemplateResponse(BaseModel):
    """Response model for an element template."""

    id: str
    name: str
    description: str | None = None
    set_id: str | None = None
    set_name: str | None = None
    is_global: bool = False
    source_element_id: str | None = None
    source_element_name: str | None = None
    included_fields: list[str]
    template_data: dict[str, object]
    created_by: str
    created_by_username: str = "Unknown"
    created_at: str
    updated_at: str


class ElementTemplateListResponse(BaseModel):
    """Paginated list of element templates."""

    items: list[ElementTemplateResponse]
    total: int
    page: int
    page_size: int
