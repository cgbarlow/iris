"""Audit log read API per ADR-009 / SPEC-009-A."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.audit.models import AuditEntry, AuditVerifyResult
from app.audit.service import verify_audit_chain
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/audit", tags=["audit"])


def _require_admin(current_user: dict[str, Any]) -> None:
    """Raise 403 if not admin."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("", response_model=dict[str, Any])
async def list_audit_entries(
    request: Request,
    action: str | None = None,
    username: str | None = None,
    target_type: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, Any]:
    """List audit log entries with filtering and pagination (admin only)."""
    _require_admin(current_user)
    db = request.app.state.db_manager.audit_db

    # Build WHERE clauses
    conditions: list[str] = []
    params: list[str] = []

    if action:
        conditions.append("action LIKE ?")
        params.append(f"%{action}%")
    if username:
        conditions.append("username = ?")
        params.append(username)
    if target_type:
        conditions.append("target_type = ?")
        params.append(target_type)
    if from_date:
        conditions.append("timestamp >= ?")
        params.append(from_date)
    if to_date:
        conditions.append("timestamp <= ?")
        params.append(to_date)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Count total
    count_cursor = await db.execute(
        f"SELECT COUNT(*) FROM audit_log WHERE {where_clause}",  # noqa: S608
        params,
    )
    count_row = await count_cursor.fetchone()
    total: int = count_row[0]

    # Fetch page
    offset = (page - 1) * page_size
    cursor = await db.execute(
        f"SELECT id, timestamp, user_id, username, action, target_type, "  # noqa: S608
        f"target_id, detail, ip_address, session_id, previous_hash, entry_hash "
        f"FROM audit_log WHERE {where_clause} "
        f"ORDER BY id DESC LIMIT ? OFFSET ?",
        [*params, page_size, offset],
    )
    rows = await cursor.fetchall()

    items = [
        AuditEntry(
            id=r[0],
            timestamp=r[1],
            user_id=r[2],
            username=r[3],
            action=r[4],
            target_type=r[5],
            target_id=r[6],
            detail=r[7],
            ip_address=r[8],
            session_id=r[9],
            previous_hash=r[10],
            entry_hash=r[11],
        ).model_dump()
        for r in rows
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/verify", response_model=AuditVerifyResult)
async def verify_chain(
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> AuditVerifyResult:
    """Verify audit chain integrity (admin only)."""
    _require_admin(current_user)
    db = request.app.state.db_manager.audit_db
    is_valid, entries_checked = await verify_audit_chain(db)
    return AuditVerifyResult(
        valid=is_valid,
        entries_checked=entries_checked,
        verified_at=datetime.now(tz=UTC).isoformat(),
    )
