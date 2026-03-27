"""API router for DoView .pptx file import."""

from __future__ import annotations

import contextlib
import os
import tempfile
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile

from app.auth.dependencies import get_current_user
from app.import_pptx.service import import_pptx_file

router = APIRouter(prefix="/api/import", tags=["import"])


@router.post("/pptx")
async def import_pptx(
    file: UploadFile,
    request: Request,
    current_user: dict = Depends(get_current_user),  # noqa: B008
    set_id: str | None = Form(default=None),  # noqa: B008
) -> dict:
    """Import a DoView .pptx file."""
    if not file.filename or not file.filename.endswith(".pptx"):
        raise HTTPException(
            status_code=400, detail="File must have .pptx extension"
        )

    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        db = request.app.state.db_manager.main_db

        # Hold a single pool connection for the entire import to avoid
        # per-execute acquire/release overhead (hundreds of INSERTs).
        from app.db.adapter import SupabaseAdapter  # noqa: PLC0415

        hold_ctx = (
            db.hold_connection()
            if isinstance(db, SupabaseAdapter)
            else contextlib.nullcontext()
        )
        async with hold_ctx:
            # Validate set_id if provided
            if set_id:
                cursor = await db.execute(
                    "SELECT id FROM sets WHERE id = ? AND is_deleted = 0",
                    (set_id,),
                )
                if await cursor.fetchone() is None:
                    raise HTTPException(status_code=400, detail="Invalid set_id")

            try:
                summary = await import_pptx_file(
                    db,
                    tmp_path,
                    imported_by=current_user["id"],
                    set_id=set_id,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

        return {
            "packages_created": summary.packages_created,
            "elements_created": summary.elements_created,
            "relationships_created": summary.relationships_created,
            "diagrams_created": summary.diagrams_created,
            "slides_skipped": summary.slides_skipped,
            "warnings": [
                {"category": w.category, "message": w.message}
                for w in summary.warnings
            ],
        }
    finally:
        os.unlink(tmp_path)


@router.post("/pptx/batch")
async def import_pptx_batch(
    files: list[UploadFile],
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
    set_id: str = Form(),  # noqa: B008
) -> dict:
    """Bulk import multiple DoView .pptx files into a single set."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    # Validate all files before processing any
    for f in files:
        if not f.filename or not f.filename.endswith(".pptx"):
            raise HTTPException(
                status_code=400,
                detail=f"File '{f.filename}' must have .pptx extension",
            )

    db = request.app.state.db_manager.main_db

    # Validate set_id
    cursor = await db.execute(
        "SELECT id FROM sets WHERE id = ? AND is_deleted = 0", (set_id,)
    )
    if await cursor.fetchone() is None:
        raise HTTPException(status_code=400, detail="Invalid set_id")

    from app.db.adapter import SupabaseAdapter  # noqa: PLC0415

    hold_ctx = (
        db.hold_connection()
        if isinstance(db, SupabaseAdapter)
        else contextlib.nullcontext()
    )

    results: list[dict] = []
    totals = {
        "packages": 0, "elements": 0, "relationships": 0,
        "diagrams": 0,
    }

    async with hold_ctx:
        for upload_file in files:
            filename = upload_file.filename or "unknown.pptx"

            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
                content = await upload_file.read()
                tmp.write(content)
                tmp_path = tmp.name

            try:
                summary = await import_pptx_file(
                    db, tmp_path,
                    imported_by=current_user["id"],
                    set_id=set_id,
                )
                result = {
                    "filename": filename,
                    "success": True,
                    "error": None,
                    "packages_created": summary.packages_created,
                    "elements_created": summary.elements_created,
                    "relationships_created": summary.relationships_created,
                    "diagrams_created": summary.diagrams_created,
                    "slides_skipped": summary.slides_skipped,
                    "warnings": [
                        {"category": w.category, "message": w.message}
                        for w in summary.warnings
                    ],
                }
                totals["packages"] += summary.packages_created
                totals["elements"] += summary.elements_created
                totals["relationships"] += summary.relationships_created
                totals["diagrams"] += summary.diagrams_created
            except (ValueError, Exception) as exc:
                result = {
                    "filename": filename,
                    "success": False,
                    "error": str(exc),
                    "packages_created": 0,
                    "elements_created": 0,
                    "relationships_created": 0,
                    "diagrams_created": 0,
                    "slides_skipped": 0,
                    "warnings": [],
                }
            finally:
                os.unlink(tmp_path)

            results.append(result)

    succeeded = sum(1 for r in results if r["success"])
    return {
        "files_processed": len(results),
        "files_succeeded": succeeded,
        "files_failed": len(results) - succeeded,
        "total_packages": totals["packages"],
        "total_elements": totals["elements"],
        "total_relationships": totals["relationships"],
        "total_diagrams": totals["diagrams"],
        "results": results,
    }
