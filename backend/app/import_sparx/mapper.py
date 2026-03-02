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
}

CONNECTOR_TYPE_MAP: dict[str, str] = {
    "Association": "association",
    "Aggregation": "aggregation",
    "Composition": "composition",
    "Generalization": "generalization",
    "Realisation": "realization",
    "Dependency": "dependency",
    "Usage": "usage",
}

SKIP_OBJECT_TYPES: set[str] = {"Note", "Boundary", "Text", "UMLDiagram", "Constraint"}

SKIP_CONNECTOR_TYPES: set[str] = {"NoteLink", "Notelink"}

DIAGRAM_TYPE_MAP: dict[str, str] = {
    "Logical": "uml",
    "Use Case": "uml",
    "Component": "uml",
    "Deployment": "uml",
    "Object": "uml",
    "Package": "uml",
    "Sequence": "sequence",
    "Activity": "uml",
    "Statechart": "uml",
    "Custom": "archimate",
    "Analysis": "uml",
    "Class": "uml",
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


def map_diagram_type(ea_type: str) -> str:
    """Map a SparxEA Diagram_Type to an Iris model type.

    Returns the mapped type, defaulting to 'simple' for unknown types.
    """
    return DIAGRAM_TYPE_MAP.get(ea_type, "simple")
