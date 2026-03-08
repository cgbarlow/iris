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
    "Package": "package_uml",
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

# ArchiMate stereotype → Iris type overrides.
# EA stores ArchiMate elements as standard UML types (Class, Component, Activity)
# with ArchiMate stereotypes. This map lets us override the Object_Type-based
# mapping when a recognised ArchiMate stereotype is present.
ARCHIMATE_STEREOTYPE_MAP: dict[str, str] = {
    # Business layer
    "ArchiMate_BusinessActor": "business_actor",
    "ArchiMate_BusinessRole": "business_role",
    "ArchiMate_BusinessProcess": "business_process",
    "ArchiMate_BusinessService": "business_service",
    "ArchiMate_BusinessObject": "business_object",
    "ArchiMate_BusinessFunction": "business_function",
    "ArchiMate_BusinessInteraction": "business_interaction",
    "ArchiMate_BusinessEvent": "business_event",
    "ArchiMate_BusinessCollaboration": "business_collaboration",
    "ArchiMate_BusinessInterface": "business_interface",
    # Application layer
    "ArchiMate_ApplicationComponent": "application_component",
    "ArchiMate_ApplicationService": "application_service",
    "ArchiMate_ApplicationInterface": "application_interface",
    "ArchiMate_ApplicationFunction": "application_function",
    "ArchiMate_ApplicationInteraction": "application_interaction",
    "ArchiMate_ApplicationEvent": "application_event",
    "ArchiMate_ApplicationCollaboration": "application_collaboration",
    "ArchiMate_ApplicationProcess": "application_process",
    # Technology layer
    "ArchiMate_TechnologyNode": "technology_node",
    "ArchiMate_TechnologyService": "technology_service",
    "ArchiMate_TechnologyInterface": "technology_interface",
    "ArchiMate_TechnologyFunction": "technology_function",
    "ArchiMate_TechnologyArtifact": "technology_artifact",
    "ArchiMate_Device": "technology_device",
    # Motivation layer
    "ArchiMate_Stakeholder": "stakeholder",
    "ArchiMate_Driver": "driver",
    "ArchiMate_Assessment": "assessment",
    "ArchiMate_Goal": "goal",
    "ArchiMate_Outcome": "outcome",
    "ArchiMate_Principle": "principle",
    "ArchiMate_Requirement": "requirement_archimate",
    "ArchiMate_Constraint": "constraint_archimate",
    # Strategy layer
    "ArchiMate_Resource": "resource",
    "ArchiMate_Capability": "capability",
    "ArchiMate_CourseOfAction": "course_of_action",
    "ArchiMate_ValueStream": "value_stream",
    # Implementation & Migration layer
    "ArchiMate_WorkPackage": "work_package",
    "ArchiMate_Deliverable": "deliverable",
    "ArchiMate_ImplementationEvent": "implementation_event",
    "ArchiMate_Plateau": "plateau",
    "ArchiMate_Gap": "gap",
    # Data layer (ArchiMate 3.x)
    "ArchiMate_DataObject": "business_object",
}


def map_archimate_stereotype(stereotype: str | None) -> str | None:
    """Map an ArchiMate stereotype to an Iris entity type.

    Returns the mapped type, or None if the stereotype is not an ArchiMate type.
    """
    if not stereotype:
        return None
    return ARCHIMATE_STEREOTYPE_MAP.get(stereotype)


SKIP_OBJECT_TYPES: set[str] = {"Text", "UMLDiagram", "Constraint"}

SKIP_CONNECTOR_TYPES: set[str] = set()

DIAGRAM_TYPE_MAP: dict[str, tuple[str, str]] = {
    "Logical": ("class", "uml"),
    "Use Case": ("use_case", "uml"),
    "Component": ("component", "uml"),
    "Deployment": ("deployment", "uml"),
    "Object": ("class", "uml"),
    "Package": ("pkg", "uml"),
    "Sequence": ("sequence", "uml"),
    "Activity": ("process", "uml"),
    "Statechart": ("state_machine", "uml"),
    "Custom": ("component", "archimate"),
    "Analysis": ("class", "uml"),
    "Class": ("class", "uml"),
}


def map_object_type(ea_type: str, stereotype: str | None = None) -> str | None:
    """Map a SparxEA Object_Type to an Iris entity type.

    Returns the mapped type string, or None if the type should be skipped.
    Text objects with NavigationCell stereotype are imported as navigation cards.
    """
    if ea_type in SKIP_OBJECT_TYPES:
        if ea_type == "Text":
            # NavigationCell: Prolaborate navigation tiles that link to diagrams
            if stereotype == "NavigationCell":
                return "navigation_cell"
            # Plain Text objects: rendered as notes (titles, labels on diagrams)
            return "note"
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
