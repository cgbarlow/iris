"""Element template API routes (ADR-191, issue #153)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.auth.dependencies import get_current_user, get_optional_user
from app.element_templates.models import (
    ElementTemplateCreate,
    ElementTemplateListResponse,
    ElementTemplateResponse,
    ElementTemplateUpdate,
)
from app.element_templates.service import (
    ElementTemplateNotFoundError,
    ElementTemplateScopeError,
    create_element_template,
    delete_element_template,
    get_element_template,
    list_element_templates,
    update_element_template,
)

router = APIRouter(prefix="/api/element-templates", tags=["element-templates"])


@router.post("", response_model=ElementTemplateResponse, status_code=201)
async def create(
    body: ElementTemplateCreate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ElementTemplateResponse:
    """Create a template from an existing element."""
    db = request.app.state.db_manager.main_db
    try:
        result = await create_element_template(
            db,
            source_element_id=body.source_element_id,
            name=body.name,
            description=body.description,
            included_fields=body.included_fields,
            set_id=body.set_id,
            is_global=body.is_global,
            created_by=current_user["id"],
        )
    except ElementTemplateScopeError as exc:
        raise HTTPException(status_code=422, detail=str(exc))  # noqa: B904
    except ElementTemplateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))  # noqa: B904
    return ElementTemplateResponse(**result)


@router.get("", response_model=ElementTemplateListResponse)
async def list_all(
    request: Request,
    set_id: str | None = None,
    include_global: bool = True,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    _current_user: dict[str, Any] | None = Depends(get_optional_user),  # noqa: B008
) -> ElementTemplateListResponse:
    """List element templates with set-scope + global filter."""
    db = request.app.state.db_manager.main_db
    items, total = await list_element_templates(
        db,
        set_id=set_id,
        include_global=include_global,
        page=page,
        page_size=page_size,
    )
    return ElementTemplateListResponse(
        items=[ElementTemplateResponse(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{template_id}", response_model=ElementTemplateResponse)
async def get_one(
    template_id: str,
    request: Request,
    _current_user: dict[str, Any] | None = Depends(get_optional_user),  # noqa: B008
) -> ElementTemplateResponse:
    """Get a single template by ID."""
    db = request.app.state.db_manager.main_db
    result = await get_element_template(db, template_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return ElementTemplateResponse(**result)


@router.put("/{template_id}", response_model=ElementTemplateResponse)
async def update(
    template_id: str,
    body: ElementTemplateUpdate,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ElementTemplateResponse:
    """Edit a template. Templates are not versioned — no If-Match."""
    db = request.app.state.db_manager.main_db
    # The model uses None to mean "leave untouched" for everything
    # except set_id; for set_id, we need a tri-state because None is
    # the legitimate value for globals. The Pydantic model's set_id
    # default is None, so we differentiate via the request body's
    # explicit keys.
    raw = body.model_dump(exclude_unset=True)
    kwargs: dict[str, Any] = {}
    if "name" in raw:
        kwargs["name"] = raw["name"]
    if "description" in raw:
        kwargs["description"] = raw["description"]
    if "included_fields" in raw:
        kwargs["included_fields"] = raw["included_fields"]
    if "is_global" in raw:
        kwargs["is_global"] = raw["is_global"]
    if "set_id" in raw:
        kwargs["set_id"] = raw["set_id"]  # may be None
    try:
        result = await update_element_template(db, template_id, **kwargs)
    except ElementTemplateScopeError as exc:
        raise HTTPException(status_code=422, detail=str(exc))  # noqa: B904
    if result is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return ElementTemplateResponse(**result)


@router.delete("/{template_id}", status_code=204)
async def delete(
    template_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> None:
    """Soft-delete a template."""
    db = request.app.state.db_manager.main_db
    ok = await delete_element_template(db, template_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Template not found")
