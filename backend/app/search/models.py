"""Pydantic models for search."""

from __future__ import annotations

from pydantic import BaseModel


class SearchResult(BaseModel):
    """A single search result."""

    id: str
    result_type: str  # "element" or "diagram"
    name: str
    description: str | None = None
    type_detail: str  # element_type or diagram_type
    rank: float = 0.0
    deep_link: str
    set_id: str | None = None
    set_name: str | None = None
    collection_name: str | None = None
    package_name: str | None = None


class SearchResponse(BaseModel):
    """Search response with results and metadata."""

    query: str
    results: list[SearchResult]
    total: int
