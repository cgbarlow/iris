"""`/api/export/*` routes (ADR-128 / SPEC-128-A).

Headless JSON + Markdown export for diagrams, elements, packages, sets,
and collections. Auth is optional (ADR-123 anonymous read policy).
"""

from __future__ import annotations

import re
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from app.auth.dependencies import get_optional_user
from app.export import markdown as md
from app.export import service as export_service
from app.export.service import ExportNotFoundError, ExportTooLargeError

router = APIRouter(tags=["Export"])

ExportFormat = Literal["json", "markdown"]


def _filename(name: str, entity_id: str, fmt: ExportFormat) -> str:
    """Produce a kebab-cased download filename."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "export"
    ext = "json" if fmt == "json" else "md"
    return f"{slug}-{entity_id}.{ext}"


def _respond(
    bundle_json: Any,
    markdown_text: str,
    entity_id: str,
    name: str,
    fmt: ExportFormat,
) -> Response:
    if fmt == "json":
        return Response(
            content=bundle_json.model_dump_json(by_alias=True),
            media_type="application/json",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{_filename(name, entity_id, fmt)}"'
                ),
            },
        )
    return Response(
        content=markdown_text,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{_filename(name, entity_id, fmt)}"'
            ),
        },
    )


def _handle_errors(exc: Exception) -> Response:
    if isinstance(exc, ExportNotFoundError):
        raise HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ExportTooLargeError):
        raise HTTPException(
            status_code=413,
            detail={
                "message": str(exc),
                "count": exc.count,
                "limit": exc.limit,
                "hint": "Paginate the underlying list endpoints instead.",
            },
        )
    raise exc


async def _build_and_respond(
    builder: Any,
    renderer: Any,
    name_getter: Any,
    request: Request,
    entity_id: str,
    fmt: ExportFormat,
) -> Response:
    db = request.app.state.db_manager.main_db
    try:
        bundle = await builder(db, entity_id)
    except (ExportNotFoundError, ExportTooLargeError) as exc:
        return _handle_errors(exc)
    markdown_text = renderer(bundle) if fmt == "markdown" else ""
    name = name_getter(bundle)
    return _respond(bundle, markdown_text, entity_id, name, fmt)


# --- Endpoints ---------------------------------------------------------------

@router.get(
    "/api/export/diagrams/{diagram_id}",
    summary="Export a diagram as JSON or Markdown",
)
async def export_diagram(
    diagram_id: str,
    request: Request,
    format: ExportFormat = Query(..., description="json or markdown"),
    _user: dict[str, Any] | None = Depends(get_optional_user),
) -> Response:
    return await _build_and_respond(
        export_service.build_diagram_export,
        md.render_diagram,
        lambda b: b.diagram.name,
        request,
        diagram_id,
        format,
    )


@router.get(
    "/api/export/elements/{element_id}",
    summary="Export an element as JSON or Markdown",
)
async def export_element(
    element_id: str,
    request: Request,
    format: ExportFormat = Query(..., description="json or markdown"),
    _user: dict[str, Any] | None = Depends(get_optional_user),
) -> Response:
    return await _build_and_respond(
        export_service.build_element_export,
        md.render_element,
        lambda b: b.element.name,
        request,
        element_id,
        format,
    )


@router.get(
    "/api/export/packages/{package_id}",
    summary="Export a package (and descendants) as JSON or Markdown",
)
async def export_package(
    package_id: str,
    request: Request,
    format: ExportFormat = Query(..., description="json or markdown"),
    _user: dict[str, Any] | None = Depends(get_optional_user),
) -> Response:
    return await _build_and_respond(
        export_service.build_package_export,
        md.render_package,
        lambda b: b.package.name,
        request,
        package_id,
        format,
    )


@router.get(
    "/api/export/sets/{set_id}",
    summary="Export a set as JSON or Markdown",
)
async def export_set(
    set_id: str,
    request: Request,
    format: ExportFormat = Query(..., description="json or markdown"),
    _user: dict[str, Any] | None = Depends(get_optional_user),
) -> Response:
    return await _build_and_respond(
        export_service.build_set_export,
        md.render_set,
        lambda b: b.set_.name,
        request,
        set_id,
        format,
    )


@router.get(
    "/api/export/collections/{collection_id}",
    summary="Export a collection as JSON or Markdown",
)
async def export_collection(
    collection_id: str,
    request: Request,
    format: ExportFormat = Query(..., description="json or markdown"),
    _user: dict[str, Any] | None = Depends(get_optional_user),
) -> Response:
    return await _build_and_respond(
        export_service.build_collection_export,
        md.render_collection,
        lambda b: b.collection.name,
        request,
        collection_id,
        format,
    )
