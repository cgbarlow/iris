"""API router for SparxEA .qea and .eap file import."""

from __future__ import annotations

import os
import tempfile

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile

from app.auth.dependencies import get_current_user
from app.import_sparx.eap_converter import convert_eap_to_sqlite
from app.import_sparx.service import import_sparx_file

router = APIRouter(prefix="/api/import", tags=["import"])


@router.post("/sparx")
async def import_sparx(
    file: UploadFile,
    request: Request,
    current_user: dict = Depends(get_current_user),  # noqa: B008
    set_id: str | None = Form(default=None),  # noqa: B008
) -> dict:
    """Import a SparxEA .qea or .eap file."""
    if not file.filename or not file.filename.endswith((".qea", ".eap")):
        raise HTTPException(
            status_code=400, detail="File must have .qea or .eap extension"
        )

    is_eap = file.filename.endswith(".eap")
    suffix = ".eap" if is_eap else ".qea"

    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    sqlite_path: str | None = None
    try:
        db = request.app.state.db_manager.main_db
        # Validate set_id if provided
        if set_id:
            cursor = await db.execute(
                "SELECT id FROM sets WHERE id = ? AND is_deleted = 0",
                (set_id,),
            )
            if await cursor.fetchone() is None:
                raise HTTPException(status_code=400, detail="Invalid set_id")

        # Convert EAP to SQLite if needed
        if is_eap:
            try:
                sqlite_path = await convert_eap_to_sqlite(tmp_path)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            except RuntimeError as exc:
                raise HTTPException(status_code=500, detail=str(exc)) from exc
            import_path = sqlite_path
        else:
            import_path = tmp_path

        summary = await import_sparx_file(
            db, import_path, imported_by=current_user["id"], set_id=set_id,
        )
        return {
            "packages_created": summary.packages_created,
            "packages_skipped": summary.packages_skipped,
            "elements_created": summary.elements_created,
            "relationships_created": summary.relationships_created,
            "diagrams_created": summary.diagrams_created,
            "diagrams_skipped": summary.diagrams_skipped,
            "elements_skipped": summary.elements_skipped,
            "connectors_skipped": summary.connectors_skipped,
            "package_relationships_created": summary.package_relationships_created,
            "warnings": [
                {"category": w.category, "message": w.message} for w in summary.warnings
            ],
        }
    finally:
        os.unlink(tmp_path)
        if sqlite_path:
            os.unlink(sqlite_path)
