"""Comment API routes per SPEC-003-A."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.dependencies import get_current_user
from app.comments.models import CommentCreate, CommentResponse, CommentUpdate

router = APIRouter(tags=["comments"])


async def _list_comments(
    db: object,
    target_type: str,
    target_id: str,
) -> list[CommentResponse]:
    """List comments for a target."""
    cursor = await db.execute(  # type: ignore[union-attr]
        "SELECT id, target_type, target_id, user_id, content, "
        "created_at, updated_at "
        "FROM comments WHERE target_type = ? AND target_id = ? "
        "AND is_deleted = 0 ORDER BY created_at ASC",
        (target_type, target_id),
    )
    rows = await cursor.fetchall()
    return [
        CommentResponse(
            id=r[0], target_type=r[1], target_id=r[2],
            user_id=r[3], content=r[4], created_at=r[5], updated_at=r[6],
        )
        for r in rows
    ]


# Entity comments
@router.get(
    "/api/entities/{entity_id}/comments",
    response_model=list[CommentResponse],
)
async def list_entity_comments(
    entity_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> list[CommentResponse]:
    """List comments on an entity."""
    db = request.app.state.db_manager.main_db
    return await _list_comments(db, "entity", entity_id)


@router.post(
    "/api/entities/{entity_id}/comments",
    response_model=CommentResponse,
    status_code=201,
)
async def create_entity_comment(
    entity_id: str,
    body: CommentCreate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> CommentResponse:
    """Add a comment on an entity."""
    db = request.app.state.db_manager.main_db
    comment_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "INSERT INTO comments (id, target_type, target_id, user_id, "
        "content, created_at, updated_at) VALUES (?, 'entity', ?, ?, ?, ?, ?)",
        (comment_id, entity_id, current_user["id"], body.content, now, now),
    )
    await db.commit()
    return CommentResponse(
        id=comment_id, target_type="entity", target_id=entity_id,
        user_id=current_user["id"], content=body.content,
        created_at=now, updated_at=now,
    )


# Model comments
@router.get(
    "/api/models/{model_id}/comments",
    response_model=list[CommentResponse],
)
async def list_model_comments(
    model_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> list[CommentResponse]:
    """List comments on a model."""
    db = request.app.state.db_manager.main_db
    return await _list_comments(db, "model", model_id)


@router.post(
    "/api/models/{model_id}/comments",
    response_model=CommentResponse,
    status_code=201,
)
async def create_model_comment(
    model_id: str,
    body: CommentCreate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> CommentResponse:
    """Add a comment on a model."""
    db = request.app.state.db_manager.main_db
    comment_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "INSERT INTO comments (id, target_type, target_id, user_id, "
        "content, created_at, updated_at) VALUES (?, 'model', ?, ?, ?, ?, ?)",
        (comment_id, model_id, current_user["id"], body.content, now, now),
    )
    await db.commit()
    return CommentResponse(
        id=comment_id, target_type="model", target_id=model_id,
        user_id=current_user["id"], content=body.content,
        created_at=now, updated_at=now,
    )


# Shared comment operations
@router.put(
    "/api/comments/{comment_id}",
    response_model=CommentResponse,
)
async def update_comment(
    comment_id: str,
    body: CommentUpdate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> CommentResponse:
    """Update a comment (owner only)."""
    db = request.app.state.db_manager.main_db
    cursor = await db.execute(
        "SELECT id, target_type, target_id, user_id, content, "
        "created_at, updated_at FROM comments "
        "WHERE id = ? AND is_deleted = 0",
        (comment_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    if row[3] != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not comment owner")

    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "UPDATE comments SET content = ?, updated_at = ? WHERE id = ?",
        (body.content, now, comment_id),
    )
    await db.commit()
    return CommentResponse(
        id=row[0], target_type=row[1], target_id=row[2],
        user_id=row[3], content=body.content,
        created_at=row[5], updated_at=now,
    )


@router.delete("/api/comments/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> None:
    """Soft-delete a comment (owner or admin)."""
    db = request.app.state.db_manager.main_db
    cursor = await db.execute(
        "SELECT user_id FROM comments WHERE id = ? AND is_deleted = 0",
        (comment_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    if row[0] != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not comment owner")

    await db.execute(
        "UPDATE comments SET is_deleted = 1 WHERE id = ?", (comment_id,),
    )
    await db.commit()
