"""Entity API routes per SPEC-006-A."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.auth.dependencies import get_current_user
from app.entities.models import (
    EntityCreate,
    EntityListResponse,
    EntityResponse,
    EntityRollback,
    EntityUpdate,
    EntityVersionResponse,
)
from app.entities.service import (
    create_entity,
    get_entity,
    get_entity_version,
    get_entity_versions,
    list_entities,
    rollback_entity,
    soft_delete_entity,
    update_entity,
)

router = APIRouter(prefix="/api/entities", tags=["entities"])


@router.post("", response_model=EntityResponse, status_code=201)
async def create(
    body: EntityCreate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> EntityResponse:
    """Create a new entity."""
    db = request.app.state.db_manager.main_db
    result = await create_entity(
        db,
        entity_type=body.entity_type,
        name=body.name,
        description=body.description,
        data=body.data,
        created_by=current_user["id"],
    )
    return EntityResponse(**result)


@router.get("", response_model=EntityListResponse)
async def list_all(
    request: Request,
    entity_type: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> EntityListResponse:
    """List entities with optional type filter and pagination."""
    db = request.app.state.db_manager.main_db
    items, total = await list_entities(
        db, entity_type=entity_type, page=page, page_size=page_size,
    )
    return EntityListResponse(
        items=[EntityResponse(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/tags/all")
async def list_all_tags(
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> list[str]:
    """List all unique tags."""
    db = request.app.state.db_manager.main_db
    cursor = await db.execute("SELECT DISTINCT tag FROM entity_tags ORDER BY tag")
    rows = await cursor.fetchall()
    return [row[0] for row in rows]


@router.get("/{entity_id}", response_model=EntityResponse)
async def get_one(
    entity_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> EntityResponse:
    """Get a single entity by ID."""
    db = request.app.state.db_manager.main_db
    result = await get_entity(db, entity_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    return EntityResponse(**result)


@router.put("/{entity_id}", response_model=EntityResponse)
async def update(
    entity_id: str,
    body: EntityUpdate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> EntityResponse:
    """Update an entity with optimistic concurrency (If-Match header)."""
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
    result = await update_entity(
        db,
        entity_id,
        name=body.name,
        description=body.description,
        data=body.data,
        change_summary=body.change_summary,
        updated_by=current_user["id"],
        expected_version=expected_version,
    )
    if result is None:
        raise HTTPException(status_code=409, detail="Version conflict")

    entity = await get_entity(db, entity_id)
    return EntityResponse(**entity)  # type: ignore[arg-type]


@router.post("/{entity_id}/rollback", response_model=EntityResponse)
async def rollback(
    entity_id: str,
    body: EntityRollback,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> EntityResponse:
    """Rollback an entity to a previous version."""
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
    result = await rollback_entity(
        db,
        entity_id,
        target_version=body.target_version,
        rolled_back_by=current_user["id"],
        expected_version=expected_version,
    )
    if result is None:
        raise HTTPException(status_code=409, detail="Version conflict or not found")

    entity = await get_entity(db, entity_id)
    return EntityResponse(**entity)  # type: ignore[arg-type]


@router.delete("/{entity_id}", status_code=204)
async def delete(
    entity_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> None:
    """Soft-delete an entity."""
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
    deleted = await soft_delete_entity(
        db, entity_id, deleted_by=current_user["id"],
        expected_version=expected_version,
    )
    if not deleted:
        raise HTTPException(status_code=409, detail="Version conflict or not found")


@router.get("/{entity_id}/versions", response_model=list[EntityVersionResponse])
async def get_versions(
    entity_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> list[EntityVersionResponse]:
    """Get all versions of an entity."""
    db = request.app.state.db_manager.main_db
    versions = await get_entity_versions(db, entity_id)
    if not versions:
        raise HTTPException(status_code=404, detail="Entity not found")
    return [EntityVersionResponse(**v) for v in versions]


@router.get(
    "/{entity_id}/versions/{version}",
    response_model=EntityVersionResponse,
)
async def get_version(
    entity_id: str,
    version: int,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> EntityVersionResponse:
    """Get a specific version of an entity."""
    db = request.app.state.db_manager.main_db
    result = await get_entity_version(db, entity_id, version)
    if result is None:
        raise HTTPException(status_code=404, detail="Version not found")
    return EntityVersionResponse(**result)


@router.get("/{entity_id}/models")
async def get_entity_models(
    entity_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> list[dict[str, str]]:
    """Get models that reference this entity."""
    db = request.app.state.db_manager.main_db

    # Check entity exists
    entity = await get_entity(db, entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    # Find models whose latest version data JSON references this entity ID.
    # model_versions.data may contain entity references in placements or nodes.
    cursor = await db.execute(
        "SELECT DISTINCT m.id, mv.name, m.model_type "
        "FROM models m "
        "JOIN model_versions mv ON m.id = mv.model_id AND m.current_version = mv.version "
        "WHERE m.is_deleted = 0 AND mv.data LIKE ?",
        (f"%{entity_id}%",),
    )
    rows = await cursor.fetchall()
    return [
        {"model_id": r[0], "name": r[1], "model_type": r[2]}
        for r in rows
    ]


@router.get("/{entity_id}/stats")
async def get_entity_stats(
    entity_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, int]:
    """Get statistics for an entity (relationship count, model usage count)."""
    db = request.app.state.db_manager.main_db

    # Check entity exists
    entity = await get_entity(db, entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    # Count relationships where this entity is source or target
    rel_cursor = await db.execute(
        "SELECT COUNT(*) FROM relationships "
        "WHERE (source_entity_id = ? OR target_entity_id = ?) AND is_deleted = 0",
        (entity_id, entity_id),
    )
    rel_row = await rel_cursor.fetchone()
    relationship_count: int = rel_row[0]

    # Count models referencing this entity
    model_cursor = await db.execute(
        "SELECT COUNT(DISTINCT m.id) "
        "FROM models m "
        "JOIN model_versions mv ON m.id = mv.model_id AND m.current_version = mv.version "
        "WHERE m.is_deleted = 0 AND mv.data LIKE ?",
        (f"%{entity_id}%",),
    )
    model_row = await model_cursor.fetchone()
    model_usage_count: int = model_row[0]

    return {
        "relationship_count": relationship_count,
        "model_usage_count": model_usage_count,
    }


@router.post("/{entity_id}/tags", status_code=201)
async def add_tag(
    entity_id: str,
    body: dict[str, Any],
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, str]:
    """Add a tag to an entity."""
    db = request.app.state.db_manager.main_db
    tag = body.get("tag", "").strip()
    if not tag or len(tag) > 50:
        raise HTTPException(status_code=400, detail="Tag must be 1-50 characters")
    now = datetime.now(tz=UTC).isoformat()
    try:
        await db.execute(
            "INSERT INTO entity_tags (entity_id, tag, created_at, created_by) "
            "VALUES (?, ?, ?, ?)",
            (entity_id, tag, now, current_user["id"]),
        )
        await db.commit()
    except Exception:
        raise HTTPException(  # noqa: B904
            status_code=409, detail="Tag already exists"
        )
    return {"entity_id": entity_id, "tag": tag, "created_at": now}


@router.delete("/{entity_id}/tags/{tag}")
async def remove_tag(
    entity_id: str,
    tag: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, str]:
    """Remove a tag from an entity."""
    db = request.app.state.db_manager.main_db
    await db.execute(
        "DELETE FROM entity_tags WHERE entity_id = ? AND tag = ?",
        (entity_id, tag),
    )
    await db.commit()
    return {"status": "ok"}
