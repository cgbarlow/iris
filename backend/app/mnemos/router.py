"""MNEMOS extension API routes (ADR-111).

Admin routes for MNEMOS status, config, and reindex — gated by extension.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.dependencies import get_current_user
from app.extensions.service import get_extension
from app.mnemos.dependencies import require_mnemos_enabled
from app.mnemos.models import MnemosConfigUpdate, MnemosReindexResponse, MnemosStatusResponse

log = logging.getLogger("app.mnemos")

router = APIRouter(
    prefix="/api/mnemos",
    tags=["mnemos"],
    dependencies=[Depends(require_mnemos_enabled)],
)


@router.get("/status", response_model=MnemosStatusResponse)
async def get_status(
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> MnemosStatusResponse:
    """Check MNEMOS connection status."""
    db = request.app.state.db_manager.main_db
    ext = await get_extension(db, "mnemos")
    if ext is None:
        return MnemosStatusResponse(enabled=False, connected=False)

    config = ext.get("config", {})
    url = config.get("url", "http://localhost:8700") if isinstance(config, dict) else "http://localhost:8700"

    try:
        from app.mnemos.adapter import check_mnemos_health

        healthy = await check_mnemos_health(str(url))
        return MnemosStatusResponse(
            enabled=bool(ext["is_enabled"]),
            connected=healthy,
            url=str(url),
        )
    except Exception as exc:  # noqa: BLE001
        return MnemosStatusResponse(
            enabled=bool(ext["is_enabled"]),
            connected=False,
            url=str(url),
            error=str(exc),
        )


@router.put("/config", response_model=MnemosStatusResponse)
async def update_config(
    body: MnemosConfigUpdate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> MnemosStatusResponse:
    """Update MNEMOS connection config. Admin only."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    db = request.app.state.db_manager.main_db
    ext = await get_extension(db, "mnemos")
    if ext is None:
        raise HTTPException(status_code=404, detail="MNEMOS extension not installed")

    new_config = {
        "url": body.url,
        "timeout_ms": body.timeout_ms,
        "max_results": body.max_results,
    }

    from datetime import UTC, datetime

    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "UPDATE extensions SET config = ?, updated_at = ? WHERE id = ?",
        (json.dumps(new_config), now, "mnemos"),
    )
    await db.commit()

    return MnemosStatusResponse(
        enabled=True,
        connected=False,
        url=body.url,
    )


@router.post("/reindex", response_model=MnemosReindexResponse)
async def reindex(
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> MnemosReindexResponse:
    """Bulk reindex all Iris entities into MNEMOS. Admin only."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    db = request.app.state.db_manager.main_db

    from app.mnemos.setup import ensure_sdk_importable
    from app.mnemos.sync import bulk_reindex

    ensure_sdk_importable()
    result = await bulk_reindex(db)
    return MnemosReindexResponse(**result)
