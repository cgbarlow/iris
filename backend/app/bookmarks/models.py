"""Pydantic models for bookmarks."""

from __future__ import annotations

from pydantic import BaseModel


class BookmarkResponse(BaseModel):
    """Response for a single bookmark."""

    diagram_id: str | None = None
    package_id: str | None = None
    created_at: str
