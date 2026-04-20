"""DocRef legislation API routes (ADR-112)."""

from __future__ import annotations

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
)
async def import_document(
    document_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> DocRefImportResponse:
    """Import a document's chunked CSV from DocRef."""
    db = request.app.state.db_manager.main_db
    try:
        result = await service.import_document(
            db, document_id, imported_by=current_user["id"]
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Import failed: {exc}"
        ) from exc
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
