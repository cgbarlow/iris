"""Artefact download API route (ADR-179, v6.2.0).

Serves rendered artefacts produced by the export / render endpoints
in `app/export/router.py`. Auth-optional (matches `/api/images/{id}`
— artefacts are referenced by URL and the URL is the access control).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.artefacts import service

router = APIRouter(prefix="/api/artefacts", tags=["artefacts"])


@router.get("/{artefact_id}")
async def get_artefact(artefact_id: str, request: Request) -> Response:
    """Serve artefact bytes with Content-Type + Content-Disposition.

    Public — the artefact URL IS the access control (same model as
    /api/images/{id}). Future ADR can tighten with signed URLs if
    needed.
    """
    db = request.app.state.db_manager.main_db
    art = await service.get_artefact(db, artefact_id)
    if art is None:
        raise HTTPException(status_code=404, detail="Artefact not found")
    return Response(
        content=art["bytes"],  # type: ignore[arg-type]
        media_type=str(art["mime"]),
        headers={
            "Content-Disposition": (
                f'attachment; filename="{art["filename"]}"'
            ),
            "Cache-Control": "public, max-age=31536000, immutable",
        },
    )
