"""Edit lock API routes (ADR-080)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.auth.dependencies import get_current_user
from app.locks.models import (
    LockAcquireRequest,
    LockCheckResponse,
    LockListResponse,
    LockResponse,
)
from app.locks.service import (
    acquire_lock,
    check_lock,
    force_release_lock,
    heartbeat_lock,
    list_active_locks,
    release_lock,
)

router = APIRouter(prefix="/api/locks", tags=["locks"])
admin_router = APIRouter(prefix="/api/admin", tags=["admin"])


def _require_admin(current_user: dict[str, Any]) -> None:
    """Raise 403 if not admin."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


@router.post("", response_model=LockResponse, status_code=200)
async def acquire(
    body: LockAcquireRequest,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> LockResponse:
    """Acquire an edit lock. Returns 200 with lock or 409 with holder info."""
    db = request.app.state.db_manager.main_db
    result = await acquire_lock(
        db,
        target_type=body.target_type,
        target_id=body.target_id,
        user_id=current_user["id"],
        username=current_user["username"],
    )
    if result.get("conflict"):
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Resource is locked by another user",
                "lock": result["lock"],
            },
        )
    return LockResponse(**result["lock"])


@router.get("/check", response_model=LockCheckResponse)
async def check(
    request: Request,
    target_type: str = Query(...),
    target_id: str = Query(...),
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> LockCheckResponse:
    """Check if a target is locked."""
    db = request.app.state.db_manager.main_db
    result = await check_lock(
        db,
        target_type=target_type,
        target_id=target_id,
        user_id=current_user["id"],
    )
    lock = LockResponse(**result["lock"]) if result["lock"] else None
    return LockCheckResponse(
        locked=result["locked"],
        lock=lock,
        is_owner=result["is_owner"],
    )


@router.put("/{lock_id}/heartbeat", response_model=LockResponse)
async def heartbeat(
    lock_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> LockResponse:
    """Extend a lock's expiry."""
    db = request.app.state.db_manager.main_db
    result = await heartbeat_lock(db, lock_id, current_user["id"])
    if result is None:
        raise HTTPException(status_code=404, detail="Lock not found or not owned")
    return LockResponse(**result)


@router.delete("/{lock_id}", status_code=204)
async def release(
    lock_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> None:
    """Release an edit lock (owner only)."""
    db = request.app.state.db_manager.main_db
    released = await release_lock(db, lock_id, current_user["id"])
    if not released:
        raise HTTPException(status_code=404, detail="Lock not found or not owned")


@router.post("/{lock_id}/release", status_code=204)
async def release_via_post(
    lock_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> None:
    """Release an edit lock via POST (for sendBeacon compatibility)."""
    db = request.app.state.db_manager.main_db
    released = await release_lock(db, lock_id, current_user["id"])
    if not released:
        raise HTTPException(status_code=404, detail="Lock not found or not owned")


@router.get("", response_model=LockListResponse)
async def list_locks(
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> LockListResponse:
    """List all active locks."""
    db = request.app.state.db_manager.main_db
    items = await list_active_locks(db)
    return LockListResponse(
        items=[LockResponse(**item) for item in items],
        total=len(items),
    )


@admin_router.delete("/locks/{lock_id}", status_code=204)
async def admin_force_release(
    lock_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> None:
    """Force-release a lock (admin only)."""
    _require_admin(current_user)
    db = request.app.state.db_manager.main_db
    released = await force_release_lock(db, lock_id)
    if not released:
        raise HTTPException(status_code=404, detail="Lock not found")
