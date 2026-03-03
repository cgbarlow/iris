"""API router for model relationships per SPEC-066-A."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user
from app.model_relationships.service import (
    create_model_relationship,
    delete_model_relationship,
    list_all_relationships_for_model,
)

router = APIRouter(tags=["model-relationships"])


class ModelRelationshipCreate(BaseModel):
    target_model_id: str = Field(min_length=1)
    relationship_type: str = Field(min_length=1)
    label: str | None = None
    description: str | None = None


@router.post("/api/models/{model_id}/relationships", status_code=201)
async def create(
    model_id: str,
    body: ModelRelationshipCreate,
    request: Request,
    current_user: dict = Depends(get_current_user),  # noqa: B008
) -> dict:
    """Create a relationship from this model to another."""
    db = request.app.state.db_manager.main_db

    # Verify source model exists
    cursor = await db.execute(
        "SELECT id FROM models WHERE id = ? AND is_deleted = 0", (model_id,)
    )
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Source model not found")

    # Verify target model exists
    cursor = await db.execute(
        "SELECT id FROM models WHERE id = ? AND is_deleted = 0",
        (body.target_model_id,),
    )
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Target model not found")

    try:
        return await create_model_relationship(
            db,
            source_model_id=model_id,
            target_model_id=body.target_model_id,
            relationship_type=body.relationship_type,
            label=body.label,
            description=body.description,
            created_by=current_user["id"],
        )
    except Exception as exc:
        if "UNIQUE constraint" in str(exc):
            raise HTTPException(
                status_code=409,
                detail="Relationship already exists between these models with this type",
            ) from exc
        raise


@router.get("/api/models/{model_id}/relationships")
async def list_rels(
    model_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),  # noqa: B008
) -> dict:
    """List all relationships for a model (model-to-model and entity-to-entity)."""
    db = request.app.state.db_manager.main_db
    return await list_all_relationships_for_model(db, model_id)


@router.delete("/api/model-relationships/{relationship_id}", status_code=204)
async def delete(
    relationship_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),  # noqa: B008
) -> None:
    """Delete a model relationship."""
    db = request.app.state.db_manager.main_db
    deleted = await delete_model_relationship(db, relationship_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Relationship not found")
