"""View API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.dependencies import get_current_user
from app.views.models import ViewCreate, ViewResponse, ViewUpdate
from app.views.service import create_view, delete_view, get_view, list_views, update_view

router = APIRouter(prefix="/api/views", tags=["views"])


@router.get("", response_model=list[ViewResponse])
async def list_all(
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> list[ViewResponse]:
    """List all views."""
    db = request.app.state.db_manager.main_db
    items = await list_views(db)
    return [ViewResponse(**item) for item in items]


@router.post("", response_model=ViewResponse, status_code=201)
async def create(
    body: ViewCreate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ViewResponse:
    """Create a new view."""
    db = request.app.state.db_manager.main_db
    result = await create_view(
        db,
        name=body.name,
        description=body.description,
        config=body.config.model_dump(),
        created_by=current_user["id"],
    )
    return ViewResponse(**result)


@router.get("/{view_id}", response_model=ViewResponse)
async def get_one(
    view_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ViewResponse:
    """Get a single view by ID."""
    db = request.app.state.db_manager.main_db
    result = await get_view(db, view_id)
    if result is None:
        raise HTTPException(status_code=404, detail="View not found")
    return ViewResponse(**result)


@router.put("/{view_id}", response_model=ViewResponse)
async def update(
    view_id: str,
    body: ViewUpdate,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ViewResponse:
    """Update a view."""
    db = request.app.state.db_manager.main_db
    result = await update_view(
        db, view_id,
        name=body.name,
        description=body.description,
        config=body.config.model_dump(),
    )
    if result is None:
        raise HTTPException(status_code=404, detail="View not found")
    return ViewResponse(**result)


@router.delete("/{view_id}", status_code=204)
async def delete(
    view_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> None:
    """Delete a view (non-default only)."""
    db = request.app.state.db_manager.main_db
    deleted = await delete_view(db, view_id)
    if not deleted:
        raise HTTPException(status_code=403, detail="Cannot delete default views")
