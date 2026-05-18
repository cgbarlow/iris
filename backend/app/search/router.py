"""Search API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from app.auth.dependencies import get_optional_user
from app.search.models import SearchResponse, SearchResult
from app.search.service import search

router = APIRouter(tags=["search"])

_ENTITY_TYPES = ("element", "package", "diagram", "set", "collection")


class EntitySearchResult(BaseModel):
    """One row of the entity-search response (ADR-205)."""

    id: str
    entity_type: str
    name: str


@router.get("/api/search", response_model=SearchResponse)
async def search_endpoint(
    request: Request,
    q: str = Query(min_length=1, max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    set_id: str | None = Query(default=None),
    collection_id: str | None = Query(default=None),
    _current_user: dict[str, Any] | None = Depends(get_optional_user),  # noqa: B008
) -> SearchResponse:
    """Search elements and diagrams by text query."""
    db = request.app.state.db_manager.main_db
    results = await search(db, q, limit=limit, set_id=set_id, collection_id=collection_id)
    return SearchResponse(
        query=q,
        results=[SearchResult(**r) for r in results],
        total=len(results),
    )


@router.get("/api/search/entities", response_model=list[EntitySearchResult])
async def search_entities_endpoint(
    request: Request,
    q: str = Query(min_length=1, max_length=200),
    types: str | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=50),
    _current_user: dict[str, Any] | None = Depends(get_optional_user),  # noqa: B008
) -> list[EntitySearchResult]:
    """Prefix-search entity names across element/package/diagram/set/collection.

    ADR-205 (v6.14.0): drives the Smart Markdown picker's entity step.
    Case-insensitive LIKE prefix match on current-version names; soft-
    deleted rows excluded for entity types that support is_deleted.

    Parameters:
      - q: required, prefix to match
      - types: optional CSV of entity types; default = all five
      - limit: 1..50, default 25 (per type union'd together)
    """
    db = request.app.state.db_manager.main_db
    requested = set(_ENTITY_TYPES)
    if types:
        requested = {t.strip() for t in types.split(",") if t.strip() in _ENTITY_TYPES}
        if not requested:
            return []

    like = f"{q}%"
    rows: list[EntitySearchResult] = []

    if "element" in requested:
        cursor = await db.execute(
            "SELECT e.id, ev.name FROM elements e "
            "JOIN element_versions ev ON e.id = ev.element_id "
            "  AND e.current_version = ev.version "
            "WHERE e.is_deleted = 0 AND LOWER(ev.name) LIKE LOWER(?) "
            "ORDER BY LOWER(ev.name) LIMIT ?",
            (like, limit),
        )
        for r in await cursor.fetchall():
            rows.append(EntitySearchResult(id=r[0], entity_type="element", name=r[1] or ""))

    if "package" in requested:
        cursor = await db.execute(
            "SELECT p.id, pv.name FROM packages p "
            "JOIN package_versions pv ON p.id = pv.package_id "
            "  AND p.current_version = pv.version "
            "WHERE p.is_deleted = 0 AND LOWER(pv.name) LIKE LOWER(?) "
            "ORDER BY LOWER(pv.name) LIMIT ?",
            (like, limit),
        )
        for r in await cursor.fetchall():
            rows.append(EntitySearchResult(id=r[0], entity_type="package", name=r[1] or ""))

    if "diagram" in requested:
        cursor = await db.execute(
            "SELECT d.id, dv.name FROM diagrams d "
            "JOIN diagram_versions dv ON d.id = dv.diagram_id "
            "  AND d.current_version = dv.version "
            "WHERE d.is_deleted = 0 AND LOWER(dv.name) LIKE LOWER(?) "
            "ORDER BY LOWER(dv.name) LIMIT ?",
            (like, limit),
        )
        for r in await cursor.fetchall():
            rows.append(EntitySearchResult(id=r[0], entity_type="diagram", name=r[1] or ""))

    if "set" in requested:
        cursor = await db.execute(
            "SELECT id, name FROM sets "
            "WHERE is_deleted = 0 AND LOWER(name) LIKE LOWER(?) "
            "ORDER BY LOWER(name) LIMIT ?",
            (like, limit),
        )
        for r in await cursor.fetchall():
            rows.append(EntitySearchResult(id=r[0], entity_type="set", name=r[1] or ""))

    if "collection" in requested:
        cursor = await db.execute(
            "SELECT id, name FROM collections "
            "WHERE LOWER(name) LIKE LOWER(?) "
            "ORDER BY LOWER(name) LIMIT ?",
            (like, limit),
        )
        for r in await cursor.fetchall():
            rows.append(EntitySearchResult(id=r[0], entity_type="collection", name=r[1] or ""))

    rows.sort(key=lambda r: r.name.lower())
    return rows[:limit]
