"""Element API routes per SPEC-006-A."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.auth.dependencies import get_current_user
from app.elements.models import (
    ElementCreate,
    ElementListResponse,
    ElementResponse,
    ElementRollback,
    ElementUpdate,
    ElementVersionResponse,
)
from app.elements.service import (
    cascade_delete_element,
    create_element,
    get_element,
    get_element_version,
    get_element_versions,
    list_elements,
    rollback_element,
    soft_delete_element,
    update_element,
)

router = APIRouter(prefix="/api/elements", tags=["elements"])


@router.post("", response_model=ElementResponse, status_code=201)
async def create(
    body: ElementCreate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ElementResponse:
    """Create a new element."""
    db = request.app.state.db_manager.main_db
    result = await create_element(
        db,
        element_type=body.element_type,
        name=body.name,
        description=body.description,
        data=body.data,
        created_by=current_user["id"],
        set_id=body.set_id,
        metadata=body.metadata,
        notation=body.notation,
    )
    return ElementResponse(**result)


@router.get("", response_model=ElementListResponse)
async def list_all(
    request: Request,
    element_type: str | None = None,
    set_id: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ElementListResponse:
    """List elements with optional type/set filter and pagination."""
    db = request.app.state.db_manager.main_db
    items, total = await list_elements(
        db, element_type=element_type, set_id=set_id, page=page, page_size=page_size,
    )
    return ElementListResponse(
        items=[ElementResponse(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/tags/all")
async def list_all_tags(
    request: Request,
    set_id: str | None = None,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> list[str]:
    """List all unique tags from elements and diagrams, optionally scoped by set."""
    db = request.app.state.db_manager.main_db
    if set_id:
        cursor = await db.execute(
            "SELECT DISTINCT tag FROM ("
            "  SELECT et.tag FROM element_tags et"
            "  JOIN elements e ON et.element_id = e.id"
            "  WHERE e.set_id = ? AND e.is_deleted = 0"
            "  UNION"
            "  SELECT dt.tag FROM diagram_tags dt"
            "  JOIN diagrams d ON dt.diagram_id = d.id"
            "  WHERE d.set_id = ? AND d.is_deleted = 0"
            ") ORDER BY tag",
            (set_id, set_id),
        )
    else:
        cursor = await db.execute(
            "SELECT DISTINCT tag FROM ("
            "  SELECT tag FROM element_tags"
            "  UNION"
            "  SELECT tag FROM diagram_tags"
            ") ORDER BY tag"
        )
    rows = await cursor.fetchall()
    return [row[0] for row in rows]


@router.get("/{element_id}", response_model=ElementResponse)
async def get_one(
    element_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ElementResponse:
    """Get a single element by ID."""
    db = request.app.state.db_manager.main_db
    result = await get_element(db, element_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Element not found")
    return ElementResponse(**result)


@router.put("/{element_id}", response_model=ElementResponse)
async def update(
    element_id: str,
    body: ElementUpdate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ElementResponse:
    """Update an element with optimistic concurrency (If-Match header)."""
    if_match = request.headers.get("If-Match")
    if if_match is None:
        raise HTTPException(
            status_code=428, detail="If-Match header required for updates"
        )
    try:
        expected_version = int(if_match)
    except ValueError:
        raise HTTPException(  # noqa: B904
            status_code=400, detail="If-Match must be an integer version"
        )

    db = request.app.state.db_manager.main_db
    result = await update_element(
        db,
        element_id,
        name=body.name,
        description=body.description,
        data=body.data,
        change_summary=body.change_summary,
        updated_by=current_user["id"],
        expected_version=expected_version,
        metadata=body.metadata,
    )
    if result is None:
        raise HTTPException(status_code=409, detail="Version conflict")

    element = await get_element(db, element_id)
    return ElementResponse(**element)  # type: ignore[arg-type]


@router.post("/{element_id}/rollback", response_model=ElementResponse)
async def rollback(
    element_id: str,
    body: ElementRollback,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ElementResponse:
    """Rollback an element to a previous version."""
    if_match = request.headers.get("If-Match")
    if if_match is None:
        raise HTTPException(
            status_code=428, detail="If-Match header required for rollback"
        )
    try:
        expected_version = int(if_match)
    except ValueError:
        raise HTTPException(  # noqa: B904
            status_code=400, detail="If-Match must be an integer version"
        )

    db = request.app.state.db_manager.main_db
    result = await rollback_element(
        db,
        element_id,
        target_version=body.target_version,
        rolled_back_by=current_user["id"],
        expected_version=expected_version,
    )
    if result is None:
        raise HTTPException(status_code=409, detail="Version conflict or not found")

    element = await get_element(db, element_id)
    return ElementResponse(**element)  # type: ignore[arg-type]


@router.delete("/{element_id}", status_code=204)
async def delete(
    element_id: str,
    request: Request,
    cascade: bool = False,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> None:
    """Soft-delete an element. With cascade=true, also removes from all diagram canvases and deletes relationships."""
    if_match = request.headers.get("If-Match")
    if if_match is None:
        raise HTTPException(
            status_code=428, detail="If-Match header required for delete"
        )
    try:
        expected_version = int(if_match)
    except ValueError:
        raise HTTPException(  # noqa: B904
            status_code=400, detail="If-Match must be an integer version"
        )

    db = request.app.state.db_manager.main_db
    if cascade:
        deleted = await cascade_delete_element(
            db, element_id, deleted_by=current_user["id"],
            expected_version=expected_version,
        )
    else:
        deleted = await soft_delete_element(
            db, element_id, deleted_by=current_user["id"],
            expected_version=expected_version,
        )
    if not deleted:
        raise HTTPException(status_code=409, detail="Version conflict or not found")


@router.get("/{element_id}/versions", response_model=list[ElementVersionResponse])
async def get_versions(
    element_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> list[ElementVersionResponse]:
    """Get all versions of an element."""
    db = request.app.state.db_manager.main_db
    versions = await get_element_versions(db, element_id)
    if not versions:
        raise HTTPException(status_code=404, detail="Element not found")
    return [ElementVersionResponse(**v) for v in versions]


@router.get(
    "/{element_id}/versions/{version}",
    response_model=ElementVersionResponse,
)
async def get_version(
    element_id: str,
    version: int,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ElementVersionResponse:
    """Get a specific version of an element."""
    db = request.app.state.db_manager.main_db
    result = await get_element_version(db, element_id, version)
    if result is None:
        raise HTTPException(status_code=404, detail="Version not found")
    return ElementVersionResponse(**result)


@router.get("/{element_id}/diagrams")
async def get_element_diagrams(
    element_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> list[dict[str, str]]:
    """Get diagrams that reference this element."""
    db = request.app.state.db_manager.main_db

    # Check element exists
    element = await get_element(db, element_id)
    if element is None:
        raise HTTPException(status_code=404, detail="Element not found")

    # Find diagrams whose latest version data JSON references this element ID.
    # diagram_versions.data may contain element references in placements or nodes.
    cursor = await db.execute(
        "SELECT DISTINCT d.id, dv.name, d.diagram_type "
        "FROM diagrams d "
        "JOIN diagram_versions dv ON d.id = dv.diagram_id AND d.current_version = dv.version "
        "WHERE d.is_deleted = 0 AND dv.data LIKE ?",
        (f"%{element_id}%",),
    )
    rows = await cursor.fetchall()
    return [
        {"diagram_id": r[0], "name": r[1], "diagram_type": r[2]}
        for r in rows
    ]


@router.get("/{element_id}/stats")
async def get_element_stats(
    element_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, int]:
    """Get statistics for an element (relationship count, diagram usage count)."""
    db = request.app.state.db_manager.main_db

    # Check element exists
    element = await get_element(db, element_id)
    if element is None:
        raise HTTPException(status_code=404, detail="Element not found")

    # Count relationships where this element is source or target
    rel_cursor = await db.execute(
        "SELECT COUNT(*) FROM relationships "
        "WHERE (source_element_id = ? OR target_element_id = ?) AND is_deleted = 0",
        (element_id, element_id),
    )
    rel_row = await rel_cursor.fetchone()
    relationship_count: int = rel_row[0]

    # Count diagrams referencing this element
    diagram_cursor = await db.execute(
        "SELECT COUNT(DISTINCT d.id) "
        "FROM diagrams d "
        "JOIN diagram_versions dv ON d.id = dv.diagram_id AND d.current_version = dv.version "
        "WHERE d.is_deleted = 0 AND dv.data LIKE ?",
        (f"%{element_id}%",),
    )
    diagram_row = await diagram_cursor.fetchone()
    diagram_usage_count: int = diagram_row[0]

    return {
        "relationship_count": relationship_count,
        "diagram_usage_count": diagram_usage_count,
    }


@router.post("/{element_id}/tags", status_code=201)
async def add_tag(
    element_id: str,
    body: dict[str, Any],
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, str]:
    """Add a tag to an element."""
    db = request.app.state.db_manager.main_db
    tag = body.get("tag", "").strip()
    if not tag or len(tag) > 50:
        raise HTTPException(status_code=400, detail="Tag must be 1-50 characters")
    now = datetime.now(tz=UTC).isoformat()
    try:
        await db.execute(
            "INSERT INTO element_tags (element_id, tag, created_at, created_by) "
            "VALUES (?, ?, ?, ?)",
            (element_id, tag, now, current_user["id"]),
        )
        await db.commit()
    except Exception:
        raise HTTPException(  # noqa: B904
            status_code=409, detail="Tag already exists"
        )
    return {"element_id": element_id, "tag": tag, "created_at": now}


@router.delete("/{element_id}/tags/{tag}")
async def remove_tag(
    element_id: str,
    tag: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, str]:
    """Remove a tag from an element."""
    db = request.app.state.db_manager.main_db
    await db.execute(
        "DELETE FROM element_tags WHERE element_id = ? AND tag = ?",
        (element_id, tag),
    )
    await db.commit()
    return {"status": "ok"}
