"""API router for Sparx EA native XMI 2.1 (.xml) import (ADR-219)."""

from __future__ import annotations

import contextlib
import os
import tempfile

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile

from app.auth.dependencies import get_current_user
from app.import_sparx_xml.reader import is_sparx_xmi_file
from app.import_sparx_xml.service import import_sparx_xml_file

router = APIRouter(prefix="/api/import", tags=["import"])


@router.post("/sparx-xml")
async def import_sparx_xml(
    file: UploadFile,
    request: Request,
    current_user: dict = Depends(get_current_user),  # noqa: B008
    set_id: str | None = Form(default=None),  # noqa: B008
) -> dict:
    """Import a Sparx EA native XMI 2.1 (.xml) export."""
    if not file.filename or not file.filename.lower().endswith(".xml"):
        raise HTTPException(
            status_code=400,
            detail="File must have a .xml extension",
        )

    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as tmp:
        while chunk := await file.read(1024 * 1024):
            tmp.write(chunk)
        tmp_path = tmp.name

    try:
        if not is_sparx_xmi_file(tmp_path):
            raise HTTPException(
                status_code=400,
                detail="File is not a Sparx EA native XMI export.",
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
                summary = await import_sparx_xml_file(
                    db,
                    tmp_path,
                    imported_by=current_user["id"],
                    set_id=set_id,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

        return {
            "packages_created": summary.packages_created,
            "packages_skipped": summary.packages_skipped,
            "elements_created": summary.elements_created,
            "elements_skipped": summary.elements_skipped,
            "relationships_created": summary.relationships_created,
            "diagrams_created": summary.diagrams_created,
            "diagrams_updated": summary.diagrams_updated,
            "diagrams_skipped": summary.diagrams_skipped,
            "connectors_skipped": summary.connectors_skipped,
            "package_relationships_created": summary.package_relationships_created,
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
