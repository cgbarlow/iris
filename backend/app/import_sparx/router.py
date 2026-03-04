"""API router for SparxEA .qea file import."""

from __future__ import annotations

import os
import tempfile

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile

from app.auth.dependencies import get_current_user
from app.import_sparx.service import import_sparx_file

router = APIRouter(prefix="/api/import", tags=["import"])


@router.post("/sparx")
async def import_sparx(
    file: UploadFile,
    request: Request,
    current_user: dict = Depends(get_current_user),  # noqa: B008
    set_id: str | None = Form(default=None),  # noqa: B008
) -> dict:
    """Import a SparxEA .qea file."""
    if not file.filename or not file.filename.endswith(".qea"):
        raise HTTPException(status_code=400, detail="File must have .qea extension")

    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix=".qea", delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

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
        summary = await import_sparx_file(
            db, tmp_path, imported_by=current_user["id"], set_id=set_id,
        )
        return {
            "packages_created": summary.packages_created,
            "elements_created": summary.elements_created,
            "relationships_created": summary.relationships_created,
            "diagrams_created": summary.diagrams_created,
            "elements_skipped": summary.elements_skipped,
            "connectors_skipped": summary.connectors_skipped,
            "package_relationships_created": summary.package_relationships_created,
            "warnings": [
                {"category": w.category, "message": w.message} for w in summary.warnings
            ],
        }
    finally:
        os.unlink(tmp_path)
