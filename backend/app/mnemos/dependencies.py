"""FastAPI dependencies for MNEMOS extension gating."""

from __future__ import annotations

from fastapi import HTTPException, Request

from app.extensions.service import is_extension_enabled

MNEMOS_EXTENSION_ID = "mnemos"


async def require_mnemos_enabled(request: Request) -> None:
    """Raise 404 if the MNEMOS extension is not installed and enabled."""
    db = request.app.state.db_manager.main_db
    if not await is_extension_enabled(db, MNEMOS_EXTENSION_ID):
        raise HTTPException(
            status_code=404,
            detail="MNEMOS extension is not available",
        )
