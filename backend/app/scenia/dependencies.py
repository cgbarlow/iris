"""FastAPI dependencies for Scenia extension gating."""

from __future__ import annotations

from fastapi import HTTPException, Request

from app.extensions.service import is_extension_enabled

SCENIA_EXTENSION_ID = "scenia"


async def require_scenia_enabled(request: Request) -> None:
    """Raise 404 if the Scenia extension is not installed and enabled."""
    db = request.app.state.db_manager.main_db
    if not await is_extension_enabled(db, SCENIA_EXTENSION_ID):
        raise HTTPException(
            status_code=404,
            detail="Scenia extension is not available",
        )
