"""Orchestrator entry point for Sparx EA native XMI 2.1 (.xml) import.

Reads the XMI into the shared Qea* dataclasses, then delegates to the
surface-agnostic ``import_sparx_model`` so all mapping, geometry, and
idempotency logic is reused from the ``.qea`` path (ADR-219, DRY §13).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.import_sparx.service import ImportSummary, import_sparx_model
from app.import_sparx_xml.reader import parse_sparx_xmi

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort


async def import_sparx_xml_file(
    db: DatabasePort,
    path: str,
    *,
    imported_by: str,
    set_id: str | None = None,
) -> ImportSummary:
    """Import a Sparx EA native XMI 2.1 export into Iris."""
    model = parse_sparx_xmi(path)
    return await import_sparx_model(
        db,
        packages=model.packages,
        elements=model.elements,
        connectors=model.connectors,
        diagrams=model.diagrams,
        diagram_objects=model.diagram_objects,
        diagram_links=model.diagram_links,
        attributes=model.attributes,
        tagged_values=model.tagged_values,
        imported_by=imported_by,
        set_id=set_id,
        source_label="SparxEA XMI",
    )
