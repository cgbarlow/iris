"""Theme API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.dependencies import get_current_user
from app.themes.models import ThemeCreate, ThemeResponse, ThemeUpdate
from app.themes.service import create_theme, delete_theme, get_theme, list_themes, update_theme

router = APIRouter(prefix="/api/themes", tags=["themes"])


@router.get("", response_model=list[ThemeResponse])
async def list_all(
    request: Request,
    notation: str | None = None,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> list[ThemeResponse]:
    """List all themes, optionally filtered by notation."""
    db = request.app.state.db_manager.main_db
    items = await list_themes(db, notation=notation)
    return [ThemeResponse(**item) for item in items]


@router.post("", response_model=ThemeResponse, status_code=201)
async def create(
    body: ThemeCreate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ThemeResponse:
    """Create a new theme."""
    db = request.app.state.db_manager.main_db
    result = await create_theme(
        db,
        name=body.name,
        description=body.description,
        notation=body.notation,
        config=body.config.model_dump(by_alias=True),
        created_by=current_user["id"],
    )
    return ThemeResponse(**result)


@router.get("/{theme_id}", response_model=ThemeResponse)
async def get_one(
    theme_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ThemeResponse:
    """Get a single theme by ID."""
    db = request.app.state.db_manager.main_db
    result = await get_theme(db, theme_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Theme not found")
    return ThemeResponse(**result)


@router.put("/{theme_id}", response_model=ThemeResponse)
async def update(
    theme_id: str,
    body: ThemeUpdate,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ThemeResponse:
    """Update a theme."""
    db = request.app.state.db_manager.main_db
    result = await update_theme(
        db, theme_id,
        name=body.name,
        description=body.description,
        notation=body.notation,
        config=body.config.model_dump(by_alias=True),
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Theme not found")
    return ThemeResponse(**result)


@router.delete("/{theme_id}", status_code=204)
async def delete(
    theme_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> None:
    """Delete a theme (non-default only)."""
    db = request.app.state.db_manager.main_db
    deleted = await delete_theme(db, theme_id)
    if not deleted:
        raise HTTPException(status_code=403, detail="Cannot delete default themes")
