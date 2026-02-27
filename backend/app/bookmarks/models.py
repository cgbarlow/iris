"""Pydantic models for bookmarks."""

from __future__ import annotations

from pydantic import BaseModel


class BookmarkResponse(BaseModel):
    """Response for a single bookmark."""

    model_id: str
    created_at: str
