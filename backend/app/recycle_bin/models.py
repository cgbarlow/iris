"""Pydantic models for the recycle bin."""

from __future__ import annotations

from pydantic import BaseModel


class DeletedItemResponse(BaseModel):
    """A soft-deleted item in the recycle bin."""

    id: str
    item_type: str  # 'package' | 'diagram' | 'element'
    name: str
    description: str | None = None
    deleted_at: str
    deleted_by_username: str | None = None
    deleted_group_id: str | None = None
    set_id: str | None = None
    set_name: str | None = None
    diagram_type: str | None = None
    element_type: str | None = None


class DeletedItemListResponse(BaseModel):
    """Paginated list of deleted items."""

    items: list[DeletedItemResponse]
    total: int
    page: int
    page_size: int
