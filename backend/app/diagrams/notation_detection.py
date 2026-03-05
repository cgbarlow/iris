"""Notation auto-detection from canvas data (ADR-079).

Scans diagram data.nodes and maps each node's entityType to a notation,
mirroring the frontend type→notation mapping from DynamicNode.svelte.
"""

from __future__ import annotations

# Entity type → notation mapping sets
UML_TYPES: frozenset[str] = frozenset({
    "class", "object", "use_case", "state", "activity", "node",
    "interface_uml", "enumeration", "abstract_class", "component_uml", "package_uml",
})

C4_TYPES: frozenset[str] = frozenset({
    "person", "software_system", "software_system_external", "container",
    "c4_component", "code_element", "deployment_node", "infrastructure_node",
    "container_instance",
})

ARCHIMATE_TYPES: frozenset[str] = frozenset({
    # Business layer
    "business_actor", "business_role", "business_process", "business_service",
    "business_object", "business_function", "business_interaction", "business_event",
    "business_collaboration", "business_interface",
    # Application layer
    "application_component", "application_service", "application_interface",
    "application_function", "application_interaction", "application_event",
    "application_collaboration", "application_process",
    # Technology layer
    "technology_node", "technology_service", "technology_interface",
    "technology_function", "technology_interaction", "technology_event",
    "technology_collaboration", "technology_process", "technology_artifact",
    "technology_device",
    # Motivation layer
    "stakeholder", "driver", "assessment", "goal", "outcome", "principle",
    "requirement_archimate", "constraint_archimate",
    # Strategy layer
    "resource", "capability", "course_of_action", "value_stream",
    # Implementation & Migration layer
    "work_package", "deliverable", "implementation_event", "plateau", "gap",
})

SIMPLE_TYPES: frozenset[str] = frozenset({
    "component", "service", "interface", "actor", "database",
})

UNIVERSAL_TYPES: frozenset[str] = frozenset({
    "note", "boundary", "modelref",
})


def detect_notations(data: dict) -> list[str]:
    """Scan diagram data.nodes and return sorted list of detected notations."""
    notations: set[str] = set()
    nodes = data.get("nodes", [])
    if not isinstance(nodes, list):
        return []

    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_data = node.get("data", {})
        if not isinstance(node_data, dict):
            continue
        entity_type = node_data.get("entityType", "")
        if not entity_type or entity_type in UNIVERSAL_TYPES:
            continue
        elif entity_type in UML_TYPES:
            notations.add("uml")
        elif entity_type in C4_TYPES:
            notations.add("c4")
        elif entity_type in ARCHIMATE_TYPES:
            notations.add("archimate")
        elif entity_type in SIMPLE_TYPES:
            notations.add("simple")

    return sorted(notations)
