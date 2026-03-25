"""API router for DoView .pptx file import."""

from __future__ import annotations

import contextlib
import os
import tempfile

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
