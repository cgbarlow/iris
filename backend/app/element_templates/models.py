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

    ADR-211 (v6.19.0): a template's content can come from any of three
    sources: snapshotting an existing element (``source_element_id`` +
    ``included_fields``), supplying ``template_data`` directly, or just
    carrying a ``markdown_stamp``. At least one must produce non-empty
    content — pure no-op templates are rejected with 422.

    ``set_id`` and ``is_global`` are mutually exclusive — exactly one
    must produce a non-null scope (enforced by the DB CHECK constraint
    and the service layer).
    """

    source_element_id: str | None = Field(default=None, min_length=1)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    included_fields: list[str] = Field(default_factory=list)
    template_data: dict[str, object] | None = None
    markdown_stamp: str | None = None
    set_id: str | None = None
    is_global: bool = False


class ElementTemplateUpdate(BaseModel):
    """Request body for editing an element template.

    All fields optional; absent fields are not touched. ``set_id`` and
    ``is_global`` can be flipped to promote a template global or
    demote it back (the CHECK constraint validates the resulting
    state). ADR-211: ``template_data`` and ``markdown_stamp`` are
    direct-write fields — setting them replaces the existing value.
    """

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    included_fields: list[str] | None = None
    template_data: dict[str, object] | None = None
    markdown_stamp: str | None = None
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
    markdown_stamp: str | None = None
    # ADR-211 v6.19.0: seeded global templates have created_by NULL (no user
    # exists at migration time). Allow nullable for those rows; CRUD-created
    # templates always carry the authoring user.
    created_by: str | None = None
    created_by_username: str = "Unknown"
    created_at: str
    updated_at: str


class ElementTemplateStampResponse(BaseModel):
    """ADR-211: in-scope stamp returned by GET /api/element-templates/stamps.

    ``markdown_stamp`` is pre-resolved — ``{{self:…}}`` placeholders are
    already substituted with ``{{element:<requested-id>:…}}`` so the
    body is ready to paste into the source.
    """

    id: str
    name: str
    description: str | None = None
    set_id: str | None = None
    is_global: bool = False
    markdown_stamp: str


class ElementTemplateStampListResponse(BaseModel):
    """List wrapper for the stamps endpoint."""

    items: list[ElementTemplateStampResponse]


class ElementTemplateListResponse(BaseModel):
    """Paginated list of element templates."""

    items: list[ElementTemplateResponse]
    total: int
    page: int
    page_size: int
