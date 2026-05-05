"""DocRef legislation API routes (ADR-112)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.dependencies import get_current_user
from app.docref.dependencies import require_docref_enabled
from app.docref.models import (
    DocRefDocument,
    DocRefDocumentListResponse,
    DocRefImportResponse,
    DocRefRefreshResponse,
)
from app.docref import service

log = logging.getLogger("app.docref.router")

router = APIRouter(
    prefix="/api/docref",
    tags=["docref"],
    dependencies=[Depends(require_docref_enabled)],
)


@router.post("/refresh", response_model=DocRefRefreshResponse)
async def refresh_index(
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> DocRefRefreshResponse:
    """Refresh the document index from legislation.docref.nz. Admin only."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    db = request.app.state.db_manager.main_db
    result = await service.refresh_document_index(db)
    return DocRefRefreshResponse(**result)


@router.get("/documents", response_model=DocRefDocumentListResponse)
async def list_documents(
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),
) -> DocRefDocumentListResponse:
    """List all known DocRef documents with their import status."""
    db = request.app.state.db_manager.main_db
    items = await service.list_documents(db)
    return DocRefDocumentListResponse(items=[DocRefDocument(**item) for item in items])


@router.post(
    "/documents/{document_id}/import",
    response_model=DocRefImportResponse,
    status_code=202,
)
async def import_document(
    document_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> DocRefImportResponse:
    """Kick off a DocRef document import.

    Issue #27: large CSVs can take well over a minute to download +
    insert, and edge proxies (Render, Cloudflare) close the request
    before the backend finishes — the user sees "Import failed" but
    the import actually completes a moment later. We now mark the
    document `importing` synchronously, schedule the actual work as a
    background task, and return 202 immediately. The frontend polls
    `/documents` and reflects the real status.
    """
    db = request.app.state.db_manager.main_db
    try:
        result = await service.start_import_document(db, document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    user_id = current_user["id"]

    async def _run() -> None:
        try:
            await service.import_document(db, document_id, imported_by=user_id)
        except Exception as exc:  # noqa: BLE001
            log.warning("DocRef import failed for %s: %s", document_id, exc)

    asyncio.create_task(_run())
    return DocRefImportResponse(**result)


@router.delete("/documents/{document_id}/chunks", status_code=204)
async def delete_chunks(
    document_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> None:
    """Remove imported chunks and reset document status. Admin only."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    db = request.app.state.db_manager.main_db
    removed = await service.delete_document_chunks(db, document_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Document not found")
