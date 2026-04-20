"""Hourly background task to refresh DocRef document index (ADR-112)."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

log = logging.getLogger("app.docref.scheduler")

REFRESH_INTERVAL_SECONDS = 3600  # 1 hour


async def start_docref_refresh_loop(app: FastAPI) -> None:
    """Periodically refresh the DocRef document index.

    Runs every hour. Checks extension state each cycle so it becomes
    a no-op if docref is disabled or uninstalled.
    """
    while True:
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)
        try:
            from app.extensions.service import is_extension_enabled

            db = app.state.db_manager.main_db
            if await is_extension_enabled(db, "docref"):
                from app.docref.service import refresh_document_index

                result = await refresh_document_index(db)
                log.info(
                    "[DocRef] Index refreshed: %d found, %d new, %d updated",
                    result["documents_found"],
                    result["new_documents"],
                    result["updated_documents"],
                )
        except Exception:
            log.exception("[DocRef] Index refresh failed")
