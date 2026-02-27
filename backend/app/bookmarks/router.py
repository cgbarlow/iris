"""Bookmark API routes per SPEC-003-A."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.dependencies import get_current_user
from app.bookmarks.models import BookmarkResponse

router = APIRouter(tags=["bookmarks"])


@router.get(
    "/api/bookmarks",
    response_model=list[BookmarkResponse],
)
async def list_bookmarks(
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> list[BookmarkResponse]:
    """List current user's bookmarked models."""
    db = request.app.state.db_manager.main_db
    cursor = await db.execute(
        "SELECT model_id, created_at FROM bookmarks "
        "WHERE user_id = ? ORDER BY created_at DESC",
        (current_user["id"],),
    )
    rows = await cursor.fetchall()
    return [BookmarkResponse(model_id=r[0], created_at=r[1]) for r in rows]


@router.post(
    "/api/models/{model_id}/bookmark",
    response_model=BookmarkResponse,
    status_code=201,
)
async def bookmark_model(
    model_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> BookmarkResponse:
    """Bookmark a model for the current user."""
    db = request.app.state.db_manager.main_db
    # Check if already bookmarked
    cursor = await db.execute(
        "SELECT created_at FROM bookmarks WHERE user_id = ? AND model_id = ?",
        (current_user["id"], model_id),
    )
    existing = await cursor.fetchone()
    if existing:
        raise HTTPException(status_code=409, detail="Already bookmarked")

    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "INSERT INTO bookmarks (user_id, model_id, created_at) VALUES (?, ?, ?)",
        (current_user["id"], model_id, now),
    )
    await db.commit()
    return BookmarkResponse(model_id=model_id, created_at=now)


@router.delete("/api/models/{model_id}/bookmark", status_code=204)
async def unbookmark_model(
    model_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> None:
    """Remove a model bookmark for the current user."""
    db = request.app.state.db_manager.main_db
    cursor = await db.execute(
        "SELECT 1 FROM bookmarks WHERE user_id = ? AND model_id = ?",
        (current_user["id"], model_id),
    )
    if await cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    await db.execute(
        "DELETE FROM bookmarks WHERE user_id = ? AND model_id = ?",
        (current_user["id"], model_id),
    )
    await db.commit()
