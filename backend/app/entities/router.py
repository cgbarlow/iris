"""Entity API routes per SPEC-006-A."""

from __future__ import annotations

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
