"""Search API routes."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.auth.dependencies import get_optional_user
from app.search.models import SearchResponse, SearchResult
from app.search.service import search

router = APIRouter(tags=["search"])

_ENTITY_TYPES = ("element", "package", "diagram", "set", "collection")
_BROWSE_BUCKET_TYPES = ("element", "package", "diagram")


class EntitySearchResult(BaseModel):
    """One row of the entity-search response (ADR-205)."""

    id: str
    entity_type: str
    name: str


class BrowseBreadcrumb(BaseModel):
    """One breadcrumb step in the picker browse response (ADR-206)."""

    label: str
    scope: Literal["collection", "set", "set_bucket"] | None = None
    id: str | None = None
    entity_type: Literal["element", "package", "diagram"] | None = None


class BrowseCounts(BaseModel):
    """Per-bucket counts returned for scope=set (ADR-206)."""

    packages: int
    diagrams: int
    elements: int


class BrowseResponse(BaseModel):
    """Uniform browse response (ADR-206)."""

    breadcrumb: list[BrowseBreadcrumb]
    items: list[EntitySearchResult]
    counts: BrowseCounts | None = None


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
    set_id: str | None = Query(default=None),
    collection_id: str | None = Query(default=None),
    _current_user: dict[str, Any] | None = Depends(get_optional_user),  # noqa: B008
) -> list[EntitySearchResult]:
    """Substring-search entity names across element/package/diagram/set/collection.

    ADR-205 (v6.14.0): drives the Smart Markdown picker.
    ADR-206 (v6.15.0): substring (was prefix) plus optional scope.

    Parameters:
      - q: required, substring to match (case-insensitive)
      - types: optional CSV of entity types; default = all five
      - limit: 1..50, default 25 (per type union'd together)
      - set_id: if given, restricts elements/packages/diagrams to
        rows with matching set_id; sets and collections excluded
      - collection_id: if given, restricts sets to that collection
        and elements/packages/diagrams to any set under that
        collection. Ignored when set_id is also set.
    """
    db = request.app.state.db_manager.main_db
    requested = set(_ENTITY_TYPES)
    if types:
        requested = {t.strip() for t in types.split(",") if t.strip() in _ENTITY_TYPES}
        if not requested:
            return []

    like = f"%{q}%"
    rows: list[EntitySearchResult] = []

    # When set_id is set, exclude sets and collections regardless of `types`.
    # When collection_id is set without set_id, elements/packages/diagrams
    # are filtered to the collection's set subtree.
    if set_id:
        requested = requested - {"set", "collection"}

    if "element" in requested:
        sql = (
            "SELECT e.id, ev.name FROM elements e "
            "JOIN element_versions ev ON e.id = ev.element_id "
            "  AND e.current_version = ev.version "
            "WHERE e.is_deleted = 0 AND LOWER(ev.name) LIKE LOWER(?) "
        )
        params: list[Any] = [like]
        if set_id:
            sql += "AND e.set_id = ? "
            params.append(set_id)
        elif collection_id:
            sql += (
                "AND e.set_id IN (SELECT id FROM sets WHERE collection_id = ?) "
            )
            params.append(collection_id)
        sql += "ORDER BY LOWER(ev.name) LIMIT ?"
        params.append(limit)
        cursor = await db.execute(sql, tuple(params))
        for r in await cursor.fetchall():
            rows.append(EntitySearchResult(id=r[0], entity_type="element", name=r[1] or ""))

    if "package" in requested:
        sql = (
            "SELECT p.id, pv.name FROM packages p "
            "JOIN package_versions pv ON p.id = pv.package_id "
            "  AND p.current_version = pv.version "
            "WHERE p.is_deleted = 0 AND LOWER(pv.name) LIKE LOWER(?) "
        )
        params = [like]
        if set_id:
            sql += "AND p.set_id = ? "
            params.append(set_id)
        elif collection_id:
            sql += (
                "AND p.set_id IN (SELECT id FROM sets WHERE collection_id = ?) "
            )
            params.append(collection_id)
        sql += "ORDER BY LOWER(pv.name) LIMIT ?"
        params.append(limit)
        cursor = await db.execute(sql, tuple(params))
        for r in await cursor.fetchall():
            rows.append(EntitySearchResult(id=r[0], entity_type="package", name=r[1] or ""))

    if "diagram" in requested:
        sql = (
            "SELECT d.id, dv.name FROM diagrams d "
            "JOIN diagram_versions dv ON d.id = dv.diagram_id "
            "  AND d.current_version = dv.version "
            "WHERE d.is_deleted = 0 AND LOWER(dv.name) LIKE LOWER(?) "
        )
        params = [like]
        if set_id:
            sql += "AND d.set_id = ? "
            params.append(set_id)
        elif collection_id:
            sql += (
                "AND d.set_id IN (SELECT id FROM sets WHERE collection_id = ?) "
            )
            params.append(collection_id)
        sql += "ORDER BY LOWER(dv.name) LIMIT ?"
        params.append(limit)
        cursor = await db.execute(sql, tuple(params))
        for r in await cursor.fetchall():
            rows.append(EntitySearchResult(id=r[0], entity_type="diagram", name=r[1] or ""))

    if "set" in requested:
        sql = (
            "SELECT id, name FROM sets "
            "WHERE is_deleted = 0 AND LOWER(name) LIKE LOWER(?) "
        )
        params = [like]
        if collection_id:
            sql += "AND collection_id = ? "
            params.append(collection_id)
        sql += "ORDER BY LOWER(name) LIMIT ?"
        params.append(limit)
        cursor = await db.execute(sql, tuple(params))
        for r in await cursor.fetchall():
            rows.append(EntitySearchResult(id=r[0], entity_type="set", name=r[1] or ""))

    if "collection" in requested:
        # Collections live above all set/collection scoping; only
        # included when neither set_id nor collection_id is given.
        if not set_id and not collection_id:
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


async def _fetch_collection_name(db: Any, collection_id: str) -> str | None:
    cursor = await db.execute(
        "SELECT name FROM collections WHERE id = ?", (collection_id,),
    )
    row = await cursor.fetchone()
    return row[0] if row else None


async def _fetch_set_row(db: Any, set_id: str) -> tuple[str, str | None] | None:
    """Return (set_name, collection_id) or None if missing/deleted."""
    cursor = await db.execute(
        "SELECT name, collection_id FROM sets "
        "WHERE id = ? AND is_deleted = 0",
        (set_id,),
    )
    row = await cursor.fetchone()
    if not row:
        return None
    return (row[0], row[1])


async def _build_breadcrumb_for_set(
    db: Any, set_id: str, set_name: str, collection_id: str | None,
    extra: BrowseBreadcrumb | None = None,
) -> list[BrowseBreadcrumb]:
    crumbs = [BrowseBreadcrumb(label="Root")]
    if collection_id:
        coll_name = await _fetch_collection_name(db, collection_id)
        if coll_name:
            crumbs.append(BrowseBreadcrumb(
                label=coll_name, scope="collection", id=collection_id,
            ))
    crumbs.append(BrowseBreadcrumb(label=set_name, scope="set", id=set_id))
    if extra is not None:
        crumbs.append(extra)
    return crumbs


@router.get(
    "/api/picker/browse",
    response_model=BrowseResponse,
    response_model_exclude_none=True,
)
async def picker_browse_endpoint(
    request: Request,
    scope: Literal["root", "collection", "set", "set_bucket"],
    collection_id: str | None = Query(default=None),
    set_id: str | None = Query(default=None),
    entity_type: Literal["element", "package", "diagram"] | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    _current_user: dict[str, Any] | None = Depends(get_optional_user),  # noqa: B008
) -> BrowseResponse:
    """Hierarchical browse for the Smart Markdown picker (ADR-206).

    Scopes:
      - root → list of collections
      - collection (collection_id required) → sets in that collection
      - set (set_id required) → empty items; counts per bucket
      - set_bucket (set_id + entity_type required) → entities in that
        set of that type
    """
    db = request.app.state.db_manager.main_db

    if scope == "root":
        cursor = await db.execute(
            "SELECT id, name FROM collections ORDER BY LOWER(name) LIMIT ?",
            (limit,),
        )
        items = [
            EntitySearchResult(id=r[0], entity_type="collection", name=r[1] or "")
            for r in await cursor.fetchall()
        ]
        return BrowseResponse(
            breadcrumb=[BrowseBreadcrumb(label="Root")], items=items,
        )

    if scope == "collection":
        if not collection_id:
            raise HTTPException(
                status_code=422,
                detail="collection_id is required for scope=collection",
            )
        coll_name = await _fetch_collection_name(db, collection_id)
        if coll_name is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        cursor = await db.execute(
            "SELECT id, name FROM sets "
            "WHERE is_deleted = 0 AND collection_id = ? "
            "ORDER BY LOWER(name) LIMIT ?",
            (collection_id, limit),
        )
        items = [
            EntitySearchResult(id=r[0], entity_type="set", name=r[1] or "")
            for r in await cursor.fetchall()
        ]
        return BrowseResponse(
            breadcrumb=[
                BrowseBreadcrumb(label="Root"),
                BrowseBreadcrumb(
                    label=coll_name, scope="collection", id=collection_id,
                ),
            ],
            items=items,
        )

    if scope == "set":
        if not set_id:
            raise HTTPException(
                status_code=422, detail="set_id is required for scope=set",
            )
        row = await _fetch_set_row(db, set_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Set not found")
        set_name, coll_id = row
        # Counts for the three buckets.
        ec = await db.execute(
            "SELECT COUNT(*) FROM elements WHERE set_id = ? AND is_deleted = 0",
            (set_id,),
        )
        elements_count = (await ec.fetchone())[0]
        pc = await db.execute(
            "SELECT COUNT(*) FROM packages WHERE set_id = ? AND is_deleted = 0",
            (set_id,),
        )
        packages_count = (await pc.fetchone())[0]
        dc = await db.execute(
            "SELECT COUNT(*) FROM diagrams WHERE set_id = ? AND is_deleted = 0",
            (set_id,),
        )
        diagrams_count = (await dc.fetchone())[0]
        return BrowseResponse(
            breadcrumb=await _build_breadcrumb_for_set(
                db, set_id, set_name, coll_id,
            ),
            items=[],
            counts=BrowseCounts(
                packages=packages_count,
                diagrams=diagrams_count,
                elements=elements_count,
            ),
        )

    # scope == "set_bucket"
    if not set_id:
        raise HTTPException(
            status_code=422, detail="set_id is required for scope=set_bucket",
        )
    if entity_type not in _BROWSE_BUCKET_TYPES:
        raise HTTPException(
            status_code=422, detail="entity_type required: element|package|diagram",
        )
    row = await _fetch_set_row(db, set_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Set not found")
    set_name, coll_id = row

    if entity_type == "element":
        cursor = await db.execute(
            "SELECT e.id, ev.name FROM elements e "
            "JOIN element_versions ev ON e.id = ev.element_id "
            "  AND e.current_version = ev.version "
            "WHERE e.set_id = ? AND e.is_deleted = 0 "
            "ORDER BY LOWER(ev.name) LIMIT ?",
            (set_id, limit),
        )
        items = [
            EntitySearchResult(id=r[0], entity_type="element", name=r[1] or "")
            for r in await cursor.fetchall()
        ]
        bucket_label = "Elements"
    elif entity_type == "package":
        cursor = await db.execute(
            "SELECT p.id, pv.name FROM packages p "
            "JOIN package_versions pv ON p.id = pv.package_id "
            "  AND p.current_version = pv.version "
            "WHERE p.set_id = ? AND p.is_deleted = 0 "
            "ORDER BY LOWER(pv.name) LIMIT ?",
            (set_id, limit),
        )
        items = [
            EntitySearchResult(id=r[0], entity_type="package", name=r[1] or "")
            for r in await cursor.fetchall()
        ]
        bucket_label = "Packages"
    else:  # diagram
        cursor = await db.execute(
            "SELECT d.id, dv.name FROM diagrams d "
            "JOIN diagram_versions dv ON d.id = dv.diagram_id "
            "  AND d.current_version = dv.version "
            "WHERE d.set_id = ? AND d.is_deleted = 0 "
            "ORDER BY LOWER(dv.name) LIMIT ?",
            (set_id, limit),
        )
        items = [
            EntitySearchResult(id=r[0], entity_type="diagram", name=r[1] or "")
            for r in await cursor.fetchall()
        ]
        bucket_label = "Diagrams"

    return BrowseResponse(
        breadcrumb=await _build_breadcrumb_for_set(
            db, set_id, set_name, coll_id,
            extra=BrowseBreadcrumb(
                label=bucket_label, scope="set_bucket", id=set_id,
                entity_type=entity_type,
            ),
        ),
        items=items,
    )
