"""Pydantic models for search."""

from __future__ import annotations

from pydantic import BaseModel


class SearchResult(BaseModel):
    """A single search result."""

    id: str
    result_type: str  # "entity" or "model"
    name: str
    description: str | None = None
    type_detail: str  # entity_type or model_type
    rank: float = 0.0
    deep_link: str


class SearchResponse(BaseModel):
    """Search response with results and metadata."""

    query: str
    results: list[SearchResult]
    total: int
