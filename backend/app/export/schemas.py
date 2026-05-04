"""Pydantic bundle schemas for `/api/export/*` JSON responses.

See SPEC-128-A. Bundles embed existing response models so a consumer
that already parses `DiagramResponse`/`ElementResponse` can reuse those
types when decoding an export.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — Pydantic needs runtime access
from typing import Literal

from pydantic import BaseModel, Field

from app.collections.models import CollectionResponse
from app.diagrams.models import DiagramResponse
from app.elements.models import ElementResponse
from app.packages.models import PackageResponse
from app.sets.models import SetResponse

EXPORT_SCHEMA_VERSION: Literal["1.0"] = "1.0"


class ExportCap(BaseModel):
    """Returned on 413 to tell the caller how large the bundle would be."""

    count: int
    limit: int
    hint: str = "Paginate the underlying list endpoints instead."


class DiagramExport(BaseModel):
    """Single-diagram bundle: the diagram plus every element it links."""

    schema_version: Literal["1.0"] = "1.0"
    exported_at: datetime
    diagram: DiagramResponse
    elements: list[ElementResponse] = Field(default_factory=list)


class ElementExport(BaseModel):
    """Single-element bundle."""

    schema_version: Literal["1.0"] = "1.0"
    exported_at: datetime
    element: ElementResponse
    linked_diagram_ids: list[str] = Field(default_factory=list)


class PackageExport(BaseModel):
    """Package + descendant packages/diagrams/elements."""

    schema_version: Literal["1.0"] = "1.0"
    exported_at: datetime
    package: PackageResponse
    descendant_packages: list[PackageResponse] = Field(default_factory=list)
    diagrams: list[DiagramResponse] = Field(default_factory=list)
    elements: list[ElementResponse] = Field(default_factory=list)


class SetExport(BaseModel):
    """Set + all packages/diagrams/elements in the set."""

    schema_version: Literal["1.0"] = "1.0"
    exported_at: datetime
    set_: SetResponse = Field(alias="set")
    packages: list[PackageResponse] = Field(default_factory=list)
    diagrams: list[DiagramResponse] = Field(default_factory=list)
    elements: list[ElementResponse] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class CollectionExport(BaseModel):
    """Collection + every set within it (each expanded as `SetExport`)."""

    schema_version: Literal["1.0"] = "1.0"
    exported_at: datetime
    collection: CollectionResponse
    sets: list[SetExport] = Field(default_factory=list)
