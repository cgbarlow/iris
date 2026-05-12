"""Pydantic models for search."""

from __future__ import annotations

from pydantic import BaseModel


class SearchResult(BaseModel):
    """A single search result.

    v5.14.0 (ADR-159): Set/Collection hits now carry their
    `mcp_system_context` so an MCP client model sees the scope's
    orient guidance immediately on a search match — no follow-up
    `get_set` / `get_collection` call needed for the context to land.
    """

    id: str
    result_type: str  # "element" | "diagram" | "package" | "set" | "collection"
    name: str
    description: str | None = None
    type_detail: str  # element_type or diagram_type
    rank: float = 0.0
    deep_link: str
    set_id: str | None = None
    set_name: str | None = None
    collection_name: str | None = None
    package_name: str | None = None
    # Only populated for set / collection hits (ADR-159).
    mcp_system_context: str | None = None


class SearchResponse(BaseModel):
    """Search response with results and metadata."""

    query: str
    results: list[SearchResult]
    total: int
