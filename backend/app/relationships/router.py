"""Relationship API routes per SPEC-003-A."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.auth.dependencies import get_current_user
from app.relationships.models import (
    RelationshipCreate,
    RelationshipListResponse,
    RelationshipResponse,
    RelationshipUpdate,
)
from app.relationships.service import (
    create_relationship,
    get_relationship,
    list_relationships,
    soft_delete_relationship,
    update_relationship,
)

router = APIRouter(prefix="/api/relationships", tags=["relationships"])


@router.post("", response_model=RelationshipResponse, status_code=201)
async def create(
    body: RelationshipCreate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> RelationshipResponse:
    """Create a new relationship between entities."""
    db = request.app.state.db_manager.main_db
    result = await create_relationship(
        db,
        source_entity_id=body.source_entity_id,
        target_entity_id=body.target_entity_id,
        relationship_type=body.relationship_type,
        label=body.label,
        description=body.description,
        data=body.data,
        created_by=current_user["id"],
    )
    return RelationshipResponse(**result)


@router.get("", response_model=RelationshipListResponse)
async def list_all(
    request: Request,
    entity_id: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> RelationshipListResponse:
    """List relationships, optionally filtered by entity."""
    db = request.app.state.db_manager.main_db
    items, total = await list_relationships(
        db, entity_id=entity_id, page=page, page_size=page_size,
    )
    return RelationshipListResponse(
        items=[RelationshipResponse(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{rel_id}", response_model=RelationshipResponse)
async def get_one(
    rel_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> RelationshipResponse:
    """Get a single relationship by ID."""
    db = request.app.state.db_manager.main_db
    result = await get_relationship(db, rel_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Relationship not found")
    return RelationshipResponse(**result)


@router.put("/{rel_id}", response_model=RelationshipResponse)
async def update(
    rel_id: str,
    body: RelationshipUpdate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> RelationshipResponse:
    """Update a relationship with optimistic concurrency."""
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
    result = await update_relationship(
        db, rel_id,
        label=body.label,
        description=body.description,
        data=body.data,
        change_summary=body.change_summary,
        updated_by=current_user["id"],
        expected_version=expected_version,
    )
    if result is None:
        raise HTTPException(status_code=409, detail="Version conflict")

    rel = await get_relationship(db, rel_id)
    return RelationshipResponse(**rel)  # type: ignore[arg-type]


@router.delete("/{rel_id}", status_code=204)
async def delete(
    rel_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> None:
    """Soft-delete a relationship."""
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
    deleted = await soft_delete_relationship(
        db, rel_id,
        deleted_by=current_user["id"],
        expected_version=expected_version,
    )
    if not deleted:
        raise HTTPException(status_code=409, detail="Version conflict or not found")
