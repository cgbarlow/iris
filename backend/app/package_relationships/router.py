"""API router for package relationships."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user
from app.package_relationships.service import (
    create_package_relationship,
    delete_package_relationship,
    list_package_relationships,
)

router = APIRouter(tags=["package-relationships"])


class PackageRelationshipCreate(BaseModel):
    target_package_id: str = Field(min_length=1)
    relationship_type: str = Field(min_length=1)
    label: str | None = None
    description: str | None = None


@router.post("/api/packages/{package_id}/relationships", status_code=201)
async def create(
    package_id: str,
    body: PackageRelationshipCreate,
    request: Request,
    current_user: dict = Depends(get_current_user),  # noqa: B008
) -> dict:
    """Create a relationship from this package to another."""
    db = request.app.state.db_manager.main_db

    # Verify source package exists
    cursor = await db.execute(
        "SELECT id FROM packages WHERE id = ? AND is_deleted = 0", (package_id,)
    )
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Source package not found")

    # Verify target package exists
    cursor = await db.execute(
        "SELECT id FROM packages WHERE id = ? AND is_deleted = 0",
        (body.target_package_id,),
    )
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Target package not found")

    try:
        return await create_package_relationship(
            db,
            source_package_id=package_id,
            target_package_id=body.target_package_id,
            relationship_type=body.relationship_type,
            label=body.label,
            description=body.description,
            created_by=current_user["id"],
        )
    except Exception as exc:
        if "UNIQUE constraint" in str(exc):
            raise HTTPException(
                status_code=409,
                detail="Relationship already exists between these packages with this type",
            ) from exc
        raise


@router.get("/api/packages/{package_id}/relationships")
async def list_rels(
    package_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),  # noqa: B008
) -> dict:
    """List all relationships for a package (package-to-package and element-to-element)."""
    db = request.app.state.db_manager.main_db
    package_rels = await list_package_relationships(db, package_id)
    return {
        "package_relationships": package_rels,
        "element_relationships": [],
    }


@router.delete("/api/package-relationships/{relationship_id}", status_code=204)
async def delete(
    relationship_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),  # noqa: B008
) -> None:
    """Delete a package relationship."""
    db = request.app.state.db_manager.main_db
    deleted = await delete_package_relationship(db, relationship_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Relationship not found")
