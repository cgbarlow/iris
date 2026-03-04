"""Diagram API routes per SPEC-003-A."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response as FastAPIResponse

from app.auth.dependencies import get_current_user
from app.diagrams.models import (
    DiagramCreate,
    DiagramHierarchyNode,
    DiagramListResponse,
    DiagramResponse,
    DiagramUpdate,
    DiagramVersionResponse,
)
from app.diagrams.service import (
    create_diagram,
    get_diagram,
    get_diagram_ancestors,
    get_diagram_children,
    get_diagram_hierarchy,
    get_diagram_versions,
    list_diagrams,
    set_diagram_parent,
    soft_delete_diagram,
    update_diagram,
)
from app.diagrams.thumbnail import get_thumbnail, regenerate_all_thumbnails

router = APIRouter(prefix="/api/diagrams", tags=["diagrams"])
admin_router = APIRouter(prefix="/api/admin", tags=["admin"])


def _require_admin(current_user: dict[str, Any]) -> None:
    """Raise 403 if not admin."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


@admin_router.post("/thumbnails/regenerate")
async def regenerate_thumbnails(
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, int]:
    """Regenerate PNG thumbnails for all diagrams. Requires admin role."""
    _require_admin(current_user)
    db = request.app.state.db_manager.main_db
    count = await regenerate_all_thumbnails(db)
    return {"count": count}


@router.post("", response_model=DiagramResponse, status_code=201)
async def create(
    body: DiagramCreate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> DiagramResponse:
    """Create a new diagram."""
    db = request.app.state.db_manager.main_db
    result = await create_diagram(
        db,
        diagram_type=body.diagram_type,
        name=body.name,
        description=body.description,
        data=body.data,
        created_by=current_user["id"],
        parent_package_id=body.parent_package_id,
        set_id=body.set_id,
        metadata=body.metadata,
    )
    return DiagramResponse(**result)


@router.get("/hierarchy", response_model=list[DiagramHierarchyNode])
async def hierarchy(
    request: Request,
    root_id: str | None = None,
    set_id: str | None = None,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> list[DiagramHierarchyNode]:
    """Get the diagram hierarchy tree."""
    db = request.app.state.db_manager.main_db
    tree = await get_diagram_hierarchy(db, root_id=root_id, set_id=set_id)
    return [DiagramHierarchyNode(**node) for node in tree]


@router.get("", response_model=DiagramListResponse)
async def list_all(
    request: Request,
    diagram_type: str | None = None,
    set_id: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> DiagramListResponse:
    """List diagrams with optional type/set filter and pagination."""
    db = request.app.state.db_manager.main_db
    items, total = await list_diagrams(
        db, diagram_type=diagram_type, set_id=set_id, page=page, page_size=page_size,
    )
    return DiagramListResponse(
        items=[DiagramResponse(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{diagram_id}", response_model=DiagramResponse)
async def get_one(
    diagram_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> DiagramResponse:
    """Get a single diagram by ID."""
    db = request.app.state.db_manager.main_db
    result = await get_diagram(db, diagram_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Diagram not found")
    return DiagramResponse(**result)


@router.put("/{diagram_id}", response_model=DiagramResponse)
async def update(
    diagram_id: str,
    body: DiagramUpdate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> DiagramResponse:
    """Update a diagram with optimistic concurrency."""
    if_match = request.headers.get("If-Match")
    if if_match is None:
        raise HTTPException(
            status_code=428, detail="If-Match header required"
        )
    try:
        expected_version = int(if_match)
    except ValueError:
        raise HTTPException(  # noqa: B904
            status_code=400, detail="If-Match must be an integer version"
        )

    db = request.app.state.db_manager.main_db
    result = await update_diagram(
        db, diagram_id,
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

    diagram = await get_diagram(db, diagram_id)
    return DiagramResponse(**diagram)  # type: ignore[arg-type]


@router.delete("/{diagram_id}", status_code=204)
async def delete(
    diagram_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> None:
    """Soft-delete a diagram."""
    if_match = request.headers.get("If-Match")
    if if_match is None:
        raise HTTPException(
            status_code=428, detail="If-Match header required"
        )
    try:
        expected_version = int(if_match)
    except ValueError:
        raise HTTPException(  # noqa: B904
            status_code=400, detail="If-Match must be an integer version"
        )

    db = request.app.state.db_manager.main_db
    deleted = await soft_delete_diagram(
        db, diagram_id,
        deleted_by=current_user["id"],
        expected_version=expected_version,
    )
    if not deleted:
        raise HTTPException(status_code=409, detail="Version conflict or not found")


@router.get("/{diagram_id}/ancestors")
async def get_diagram_ancestors_route(
    diagram_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> list[dict[str, Any]]:
    """Get ancestor chain for breadcrumb navigation (root first)."""
    db = request.app.state.db_manager.main_db
    return await get_diagram_ancestors(db, diagram_id)


@router.get("/{diagram_id}/children")
async def get_diagram_children_route(
    diagram_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> list[dict[str, Any]]:
    """Get direct children of a diagram."""
    db = request.app.state.db_manager.main_db
    return await get_diagram_children(db, diagram_id)


@router.put("/{diagram_id}/parent")
async def set_parent(
    diagram_id: str,
    body: dict[str, Any],
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, Any]:
    """Set or unset the parent package for a diagram."""
    db = request.app.state.db_manager.main_db
    parent_id = body.get("parent_package_id")
    result = await set_diagram_parent(
        db, diagram_id, parent_id, updated_by=_current_user["id"],
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Diagram or parent not found")
    if result.get("error") == "cycle":
        raise HTTPException(
            status_code=400, detail="Cannot set parent: would create a cycle"
        )
    return result


@router.get(
    "/{diagram_id}/versions",
    response_model=list[DiagramVersionResponse],
)
async def get_versions(
    diagram_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> list[DiagramVersionResponse]:
    """Get all versions of a diagram."""
    db = request.app.state.db_manager.main_db
    versions = await get_diagram_versions(db, diagram_id)
    if not versions:
        raise HTTPException(status_code=404, detail="Diagram not found")
    return [DiagramVersionResponse(**v) for v in versions]


@router.get("/{diagram_id}/thumbnail")
async def get_diagram_thumbnail(
    diagram_id: str,
    request: Request,
    theme: str = Query(default="dark"),
) -> FastAPIResponse:
    """Get the PNG thumbnail for a diagram."""
    db = request.app.state.db_manager.main_db
    thumbnail = await get_thumbnail(db, diagram_id, theme=theme)
    if thumbnail is None:
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    # Detect if it's SVG or PNG by checking magic bytes
    content_type = "image/png" if thumbnail[:8] == b"\x89PNG\r\n\x1a\n" else "image/svg+xml"
    return FastAPIResponse(
        content=thumbnail,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.post("/{diagram_id}/tags", status_code=201)
async def add_tag(
    diagram_id: str,
    body: dict[str, Any],
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, str]:
    """Add a tag to a diagram."""
    db = request.app.state.db_manager.main_db
    tag = body.get("tag", "").strip()
    if not tag or len(tag) > 50:
        raise HTTPException(status_code=400, detail="Tag must be 1-50 characters")
    now = datetime.now(tz=UTC).isoformat()
    try:
        await db.execute(
            "INSERT INTO diagram_tags (diagram_id, tag, created_at, created_by) "
            "VALUES (?, ?, ?, ?)",
            (diagram_id, tag, now, current_user["id"]),
        )
        await db.commit()
    except Exception:
        raise HTTPException(  # noqa: B904
            status_code=409, detail="Tag already exists"
        )
    return {"diagram_id": diagram_id, "tag": tag, "created_at": now}


@router.delete("/{diagram_id}/tags/{tag}")
async def remove_tag(
    diagram_id: str,
    tag: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, str]:
    """Remove a tag from a diagram."""
    db = request.app.state.db_manager.main_db
    await db.execute(
        "DELETE FROM diagram_tags WHERE diagram_id = ? AND tag = ?",
        (diagram_id, tag),
    )
    await db.commit()
    return {"status": "ok"}
