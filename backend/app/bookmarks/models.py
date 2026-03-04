"""Pydantic models for bookmarks."""

from __future__ import annotations

from pydantic import BaseModel


class BookmarkResponse(BaseModel):
    """Response for a single bookmark."""

    diagram_id: str
    created_at: str
