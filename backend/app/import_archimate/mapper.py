"""xsi:type → iris type maps for ArchiMate Open Exchange import.

Element-type lookup delegates to the SparxEA importer's
``ARCHIMATE_STEREOTYPE_MAP`` (single source of truth for ArchiMate→Iris
element types) by prefixing the unprefixed OEX type with ``ArchiMate_``.

Relationship-type and a small set of structural types (Junction, Note)
are local — they aren't part of the SparxEA stereotype universe.
"""

from __future__ import annotations

from app.import_sparx.mapper import ARCHIMATE_STEREOTYPE_MAP

OEX_NAMESPACES: tuple[str, ...] = (
    "http://www.opengroup.org/xsd/archimate/3.0/",
    "http://www.opengroup.org/xsd/archimate/3.1/",
    "http://www.opengroup.org/xsd/archimate/3.2/",
)

# ArchiMate 3.x relationship taxonomy → Iris relationship_type.
# "Used" (legacy from 2.x → 3.0 transition) folds into "serving".
RELATIONSHIP_TYPE_MAP: dict[str, str] = {
    "Composition": "composition",
    "Aggregation": "aggregation",
    "Assignment": "assignment",
    "Realization": "realization",
    "Realisation": "realization",
    "Serving": "serving",
    "Used": "serving",
    "UsedBy": "serving",
    "Triggering": "triggering",
    "Flow": "flow",
    "Specialization": "specialization",
    "Specialisation": "specialization",
    "Access": "access",
    "Influence": "influence",
    "Association": "association",
}

# Structural / annotation xsi:types that aren't in ARCHIMATE_STEREOTYPE_MAP.
_LOCAL_ELEMENT_TYPE_MAP: dict[str, str] = {
    "Note": "note",
    "Group": "boundary",
    "Junction": "junction",
    "AndJunction": "junction",
    "OrJunction": "junction",
}


def map_oex_element_type(xsi_type: str | None) -> str | None:
    """Map an OEX element xsi:type (e.g. ``BusinessActor``) to an iris type.

    Returns None if the type is unrecognised.
    """
    if not xsi_type:
        return None
    xsi_type = xsi_type.strip()
    if not xsi_type:
        return None
    if xsi_type in _LOCAL_ELEMENT_TYPE_MAP:
        return _LOCAL_ELEMENT_TYPE_MAP[xsi_type]
    return ARCHIMATE_STEREOTYPE_MAP.get(f"ArchiMate_{xsi_type}")


def map_oex_relationship_type(xsi_type: str | None) -> str | None:
    """Map an OEX relationship xsi:type (e.g. ``Serving``) to an iris type."""
    if not xsi_type:
        return None
    return RELATIONSHIP_TYPE_MAP.get(xsi_type.strip())


__all__ = [
    "OEX_NAMESPACES",
    "RELATIONSHIP_TYPE_MAP",
    "map_oex_element_type",
    "map_oex_relationship_type",
]
