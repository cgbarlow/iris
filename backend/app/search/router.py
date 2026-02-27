"""Search API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from app.auth.dependencies import get_current_user
from app.search.models import SearchResponse, SearchResult
from app.search.service import search

router = APIRouter(tags=["search"])


@router.get("/api/search", response_model=SearchResponse)
async def search_endpoint(
    request: Request,
    q: str = Query(min_length=1, max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> SearchResponse:
    """Search entities and models by text query."""
    db = request.app.state.db_manager.main_db
    results = await search(db, q, limit=limit)
    return SearchResponse(
        query=q,
        results=[SearchResult(**r) for r in results],
        total=len(results),
    )
