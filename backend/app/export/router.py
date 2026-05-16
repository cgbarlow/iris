"""`/api/export/*` routes (ADR-128 / SPEC-128-A, plus ADR-179 v6.2.0).

Headless JSON + Markdown export for diagrams, elements, packages, sets,
and collections. Auth is optional (ADR-123 anonymous read policy).

v6.2.0 (ADR-179) adds POST endpoints for rendered md/docx/pdf
artefacts stored in the `artefacts` table and returned as download URLs.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel

from app.artefacts import service as artefact_service
from app.artefacts.models import ArtefactResponse
from app.auth.dependencies import get_current_user, get_optional_user
from app.export import markdown as md
from app.export import renderers
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


# --- Renderer endpoints (ADR-179, v6.2.0) ------------------------------

RenderFormat = Literal["md", "docx", "pdf"]


class RenderDiagramRequest(BaseModel):
    format: RenderFormat


class RenderMarkdownRequest(BaseModel):
    markdown: str
    title: str
    format: RenderFormat


def _diagram_to_markdown(bundle: Any) -> tuple[str, str]:
    """Return (markdown_source, title) for a diagram bundle.

    For markdown-content diagrams (notation='markdown'), use the
    stored `data.content` directly. For visual diagrams, fall back to
    the existing markdown bundle renderer so the artefact is at
    least navigable text.
    """
    diagram = bundle.diagram
    title = diagram.name or "Untitled diagram"
    data = diagram.data if isinstance(diagram.data, dict) else {}
    if diagram.notation == "markdown":
        content = data.get("content")
        if isinstance(content, str) and content.strip():
            return content, title
    # Fall back to the structured bundle render for visual diagrams.
    return md.render_diagram(bundle), title


@router.post(
    "/api/export/diagram/{diagram_id}",
    response_model=ArtefactResponse,
    summary="Render a diagram to md/docx/pdf and store as an artefact",
)
async def render_diagram_to_artefact(
    diagram_id: str,
    body: RenderDiagramRequest,
    request: Request,
    user: dict[str, Any] | None = Depends(get_optional_user),  # noqa: B008
) -> ArtefactResponse:
    """ADR-179, v6.2.0. Render the diagram to the chosen format and
    persist as an artefact. Returns the artefact metadata + URL.

    Auth-optional; matches the existing /api/export/* read endpoints.
    """
    db = request.app.state.db_manager.main_db
    try:
        bundle = await export_service.build_diagram_export(db, diagram_id)
    except ExportNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ExportTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc

    markdown_source, title = _diagram_to_markdown(bundle)
    try:
        data, filename, mime = renderers.render(markdown_source, title, body.format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        meta = await artefact_service.create_artefact(
            db,
            data=data,
            mime=mime,
            filename=filename,
            source_kind="export_diagram",
            source_ref=diagram_id,
            created_by=(user or {}).get("id"),
        )
    except ValueError as exc:
        # Renderer produced output that failed validation (oversize or
        # invalid magic). Surface as 500 — internal renderer fault, not
        # caller's fault.
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return ArtefactResponse(**meta)


@router.post(
    "/api/export/markdown",
    response_model=ArtefactResponse,
    summary="Render ad-hoc markdown to md/docx/pdf and store as an artefact",
)
async def render_markdown_to_artefact(
    body: RenderMarkdownRequest,
    request: Request,
    user: dict[str, Any] | None = Depends(get_optional_user),  # noqa: B008
) -> ArtefactResponse:
    """ADR-179, v6.2.0. Render ad-hoc markdown content (e.g. a cascade
    draft not yet saved to a diagram) to the chosen format.
    """
    db = request.app.state.db_manager.main_db
    try:
        data, filename, mime = renderers.render(body.markdown, body.title, body.format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        meta = await artefact_service.create_artefact(
            db,
            data=data,
            mime=mime,
            filename=filename,
            source_kind="render_markdown",
            source_ref=None,
            created_by=(user or {}).get("id"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return ArtefactResponse(**meta)
