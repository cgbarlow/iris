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
    """List current user's bookmarked diagrams and packages."""
    db = request.app.state.db_manager.main_db
    cursor = await db.execute(
        "SELECT diagram_id, package_id, created_at FROM bookmarks "
        "WHERE user_id = ? ORDER BY created_at DESC",
        (current_user["id"],),
    )
    rows = await cursor.fetchall()
    return [
        BookmarkResponse(diagram_id=r[0], package_id=r[1], created_at=r[2])
        for r in rows
    ]


@router.post(
    "/api/diagrams/{diagram_id}/bookmark",
    response_model=BookmarkResponse,
    status_code=201,
)
async def bookmark_diagram(
    diagram_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> BookmarkResponse:
    """Bookmark a diagram for the current user."""
    db = request.app.state.db_manager.main_db
    # Check if already bookmarked
    cursor = await db.execute(
        "SELECT created_at FROM bookmarks WHERE user_id = ? AND diagram_id = ?",
        (current_user["id"], diagram_id),
    )
    existing = await cursor.fetchone()
    if existing:
        raise HTTPException(status_code=409, detail="Already bookmarked")

    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "INSERT INTO bookmarks (user_id, diagram_id, created_at) VALUES (?, ?, ?)",
        (current_user["id"], diagram_id, now),
    )
    await db.commit()
    return BookmarkResponse(diagram_id=diagram_id, created_at=now)


@router.delete("/api/diagrams/{diagram_id}/bookmark", status_code=204)
async def unbookmark_diagram(
    diagram_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> None:
    """Remove a diagram bookmark for the current user."""
    db = request.app.state.db_manager.main_db
    cursor = await db.execute(
        "SELECT 1 FROM bookmarks WHERE user_id = ? AND diagram_id = ?",
        (current_user["id"], diagram_id),
    )
    if await cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    await db.execute(
        "DELETE FROM bookmarks WHERE user_id = ? AND diagram_id = ?",
        (current_user["id"], diagram_id),
    )
    await db.commit()


@router.post(
    "/api/packages/{package_id}/bookmark",
    response_model=BookmarkResponse,
    status_code=201,
)
async def bookmark_package(
    package_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> BookmarkResponse:
    """Bookmark a package for the current user."""
    db = request.app.state.db_manager.main_db
    cursor = await db.execute(
        "SELECT created_at FROM bookmarks WHERE user_id = ? AND package_id = ?",
        (current_user["id"], package_id),
    )
    existing = await cursor.fetchone()
    if existing:
        raise HTTPException(status_code=409, detail="Already bookmarked")

    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "INSERT INTO bookmarks (user_id, package_id, created_at) VALUES (?, ?, ?)",
        (current_user["id"], package_id, now),
    )
    await db.commit()
    return BookmarkResponse(package_id=package_id, created_at=now)


@router.delete("/api/packages/{package_id}/bookmark", status_code=204)
async def unbookmark_package(
    package_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> None:
    """Remove a package bookmark for the current user."""
    db = request.app.state.db_manager.main_db
    cursor = await db.execute(
        "SELECT 1 FROM bookmarks WHERE user_id = ? AND package_id = ?",
        (current_user["id"], package_id),
    )
    if await cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    await db.execute(
        "DELETE FROM bookmarks WHERE user_id = ? AND package_id = ?",
        (current_user["id"], package_id),
    )
    await db.commit()
