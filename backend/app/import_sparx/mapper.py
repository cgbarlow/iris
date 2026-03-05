"""Type mapping from SparxEA to Iris types."""

from __future__ import annotations

OBJECT_TYPE_MAP: dict[str, str] = {
    "Class": "class",
    "Interface": "interface_uml",
    "Object": "object",
    "UseCase": "use_case",
    "Actor": "actor",
    "Component": "component",
    "Node": "node",
    "Activity": "activity",
    "State": "state",
    "StateMachine": "state",
    "Enumeration": "enumeration",
    "Package": "_package",  # special marker -- becomes hierarchy container
    "ArchiMate_ApplicationComponent": "application_component",
    "ArchiMate_ApplicationService": "application_service",
    "ArchiMate_BusinessActor": "business_actor",
    "ArchiMate_BusinessRole": "business_role",
    "ArchiMate_BusinessProcess": "business_process",
    "ArchiMate_BusinessService": "business_service",
    "ArchiMate_TechnologyNode": "technology_node",
    "Note": "note",
    "Boundary": "boundary",
    "Artifact": "component",
}

CONNECTOR_TYPE_MAP: dict[str, str] = {
    "Association": "association",
    "Aggregation": "aggregation",
    "Composition": "composition",
    "Generalization": "generalization",
    "Realisation": "realization",
    "Dependency": "dependency",
    "Usage": "usage",
    "NoteLink": "note_link",
    "Notelink": "note_link",
    "Nesting": "contains",
}

SKIP_OBJECT_TYPES: set[str] = {"Text", "UMLDiagram", "Constraint"}

SKIP_CONNECTOR_TYPES: set[str] = set()

DIAGRAM_TYPE_MAP: dict[str, tuple[str, str]] = {
    "Logical": ("class", "uml"),
    "Use Case": ("use_case", "uml"),
    "Component": ("component", "uml"),
    "Deployment": ("deployment", "uml"),
    "Object": ("class", "uml"),
    "Package": ("component", "uml"),
    "Sequence": ("sequence", "uml"),
    "Activity": ("process", "uml"),
    "Statechart": ("state_machine", "uml"),
    "Custom": ("component", "archimate"),
    "Analysis": ("class", "uml"),
    "Class": ("class", "uml"),
}


def map_object_type(ea_type: str) -> str | None:
    """Map a SparxEA Object_Type to an Iris entity type.

    Returns the mapped type string, or None if the type should be skipped.
    """
    if ea_type in SKIP_OBJECT_TYPES:
        return None
    return OBJECT_TYPE_MAP.get(ea_type)


def map_connector_type(ea_type: str) -> str | None:
    """Map a SparxEA Connector_Type to an Iris relationship type.

    Returns the mapped type string, or None if the type should be skipped.
    """
    if ea_type in SKIP_CONNECTOR_TYPES:
        return None
    return CONNECTOR_TYPE_MAP.get(ea_type)


def map_diagram_type(ea_type: str) -> tuple[str, str]:
    """Map a SparxEA Diagram_Type to an Iris (diagram_type, notation) pair.

    Returns the mapped tuple, defaulting to ('free_form', 'simple') for unknown types.
    """
    return DIAGRAM_TYPE_MAP.get(ea_type, ("free_form", "simple"))
