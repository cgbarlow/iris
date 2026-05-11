"""Named-prompts API routes (ADR-154, SPEC-154-A)."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response as FastAPIResponse

from app.auth.dependencies import get_current_user, get_optional_user
from app.named_prompts.models import (
    Prompt,
    PromptCreate,
    PromptListResponse,
    PromptUpdate,
)
from app.named_prompts.service import (
    create_prompt,
    delete_prompt,
    get_prompt,
    list_effective_prompts_for_set,
    list_prompts_for_collection_effective,
    list_prompts_for_scope,
    update_prompt,
)

router = APIRouter(prefix="/api/named-prompts", tags=["named-prompts"])


@router.post("", response_model=Prompt, status_code=201)
async def create(
    body: PromptCreate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> Prompt:
    db = request.app.state.db_manager.main_db
    try:
        result = await create_prompt(
            db,
            scope_type=body.scope_type,
            scope_id=body.scope_id,
            name=body.name,
            description=body.description,
            body=body.body,
            created_by=current_user.get("id"),
        )
    except ValueError as exc:
        if str(exc) == "scope_not_found":
            raise HTTPException(  # noqa: B904
                status_code=404, detail=f"{body.scope_type.title()} {body.scope_id} not found",
            )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        # IntegrityError on (scope_type, scope_id, name) UNIQUE violation.
        raise HTTPException(  # noqa: B904
            status_code=409,
            detail=f"A named prompt with this name already exists on this scope ({type(exc).__name__})",
        )
    return Prompt(**result)


@router.get("", response_model=PromptListResponse)
async def list_for_scope(
    request: Request,
    scope_type: Literal["collection", "set"] = Query(...),
    scope_id: str = Query(...),
    _current_user: dict[str, Any] | None = Depends(get_optional_user),  # noqa: B008
) -> PromptListResponse:
    db = request.app.state.db_manager.main_db
    items = await list_prompts_for_scope(db, scope_type, scope_id)
    return PromptListResponse(items=[Prompt(**item) for item in items])


@router.get("/by-scope", response_model=PromptListResponse)
async def list_by_scope(
    request: Request,
    collection_id: str | None = Query(default=None),
    set_id: str | None = Query(default=None),
    _current_user: dict[str, Any] | None = Depends(get_optional_user),  # noqa: B008
) -> PromptListResponse:
    """Effective list including inherited prompts for a Set."""
    if (collection_id is None) == (set_id is None):
        raise HTTPException(
            status_code=400,
            detail="Exactly one of collection_id or set_id must be supplied.",
        )
    db = request.app.state.db_manager.main_db
    if set_id is not None:
        items = await list_effective_prompts_for_set(db, set_id)
    else:
        assert collection_id is not None  # narrowing for type-checker
        items = await list_prompts_for_collection_effective(db, collection_id)
    return PromptListResponse(items=[Prompt(**item) for item in items])


@router.get("/{prompt_id}", response_model=Prompt)
async def get_one(
    prompt_id: str,
    request: Request,
    _current_user: dict[str, Any] | None = Depends(get_optional_user),  # noqa: B008
) -> Prompt:
    db = request.app.state.db_manager.main_db
    result = await get_prompt(db, prompt_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Named prompt not found")
    return Prompt(**result)


@router.put("/{prompt_id}", response_model=Prompt)
async def update(
    prompt_id: str,
    body: PromptUpdate,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> Prompt:
    db = request.app.state.db_manager.main_db
    result = await update_prompt(
        db, prompt_id, description=body.description, body=body.body,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Named prompt not found")
    return Prompt(**result)


@router.delete("/{prompt_id}", response_model=None)
async def delete(
    prompt_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> FastAPIResponse:
    db = request.app.state.db_manager.main_db
    deleted = await delete_prompt(db, prompt_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Named prompt not found")
    return FastAPIResponse(status_code=204)
