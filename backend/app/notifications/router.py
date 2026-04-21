"""Public-read system notification banner endpoint (ADR-124 / SPEC-124-A).

The banner is stored in the generic `settings` table under key
`notification_banner_message`. Edits go through the existing admin-gated
`PUT /api/settings/{key}` (DRY — no new write path). This module adds a
single public GET so anonymous visitors (ADR-123) can poll for the
current message.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.settings.service import get_setting

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("/banner")
async def get_banner(request: Request) -> dict[str, str]:
    """Return the current system notification banner text.

    Public — no authentication required so anonymous visitors see the
    banner (ADR-123 / ADR-124). Returns `{"message": ""}` when the
    banner is cleared, so the frontend can render or hide without a
    404 round-trip.
    """
    db = request.app.state.db_manager.main_db
    setting = await get_setting(db, "notification_banner_message")
    return {"message": setting["value"] if setting else ""}
