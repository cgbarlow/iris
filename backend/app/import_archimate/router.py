"""API router for ArchiMate Open Exchange XML (OEX) import."""

from __future__ import annotations

import contextlib
import os
import tempfile

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile

from app.auth.dependencies import get_current_user
from app.import_archimate.reader import is_oex_file
from app.import_archimate.service import import_oex_file

router = APIRouter(prefix="/api/import", tags=["import"])

_ACCEPTED_SUFFIXES = (".xml", ".archimate", ".oex")


@router.post("/archimate")
async def import_archimate(
    file: UploadFile,
    request: Request,
    current_user: dict = Depends(get_current_user),  # noqa: B008
    set_id: str | None = Form(default=None),  # noqa: B008
) -> dict:
    """Import an ArchiMate Open Exchange XML file."""
    if not file.filename or not file.filename.lower().endswith(_ACCEPTED_SUFFIXES):
        raise HTTPException(
            status_code=400,
            detail="File must have .xml, .archimate, or .oex extension",
        )

    suffix = os.path.splitext(file.filename)[1].lower() or ".xml"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        if not is_oex_file(tmp_path):
            raise HTTPException(
                status_code=400,
                detail="File is not an ArchiMate Open Exchange XML document.",
            )

        db = request.app.state.db_manager.main_db

        from app.db.adapter import SupabaseAdapter  # noqa: PLC0415

        hold_ctx = (
            db.hold_connection()
            if isinstance(db, SupabaseAdapter)
            else contextlib.nullcontext()
        )
        async with hold_ctx:
            if set_id:
                cursor = await db.execute(
                    "SELECT id FROM sets WHERE id = ? AND is_deleted = 0",
                    (set_id,),
                )
                if await cursor.fetchone() is None:
                    raise HTTPException(status_code=400, detail="Invalid set_id")

            try:
                summary = await import_oex_file(
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
            "elements_skipped": summary.elements_skipped,
            "relationships_created": summary.relationships_created,
            "relationships_skipped": summary.relationships_skipped,
            "diagrams_created": summary.diagrams_created,
            "warnings": [
                {"category": w.category, "message": w.message}
                for w in summary.warnings
            ],
        }
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
