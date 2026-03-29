"""DocRef extension dependency -- gates routes on extension availability."""

from __future__ import annotations

from fastapi import HTTPException, Request

from app.extensions.service import is_extension_enabled

DOCREF_EXTENSION_ID = "docref"


async def require_docref_enabled(request: Request) -> None:
    """Raise 404 if DocRef extension is not installed and enabled."""
    db = request.app.state.db_manager.main_db
    if not await is_extension_enabled(db, DOCREF_EXTENSION_ID):
        raise HTTPException(
            status_code=404, detail="DocRef extension is not available"
        )
