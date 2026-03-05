"""Migration 020: Diagram type and notation registry (ADR-079).

Creates registry tables for diagram types and notations, adds notation
and detected_notations columns to diagrams, seeds default data, and
migrates existing diagram_type values.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


# ── Seed data ────────────────────────────────────────────────────────────────

_DIAGRAM_TYPES = [
    ("component", "Component", "A structural component diagram", 0),
    ("sequence", "Sequence", "A behavioural sequence diagram", 1),
    ("class", "Class", "A UML class diagram", 2),
    ("deployment", "Deployment", "Infrastructure and deployment topology", 3),
    ("process", "Process", "A process or workflow diagram", 4),
    ("roadmap", "Roadmap", "A timeline or roadmap view", 5),
    ("free_form", "Free Form", "Unrestricted canvas with any notation", 6),
]

_NOTATIONS = [
    ("simple", "Simple", "Non-technical boxes-and-lines notation", 0),
    ("uml", "UML", "Unified Modeling Language notation", 1),
    ("archimate", "ArchiMate", "ArchiMate enterprise architecture notation", 2),
    ("c4", "C4", "C4 model notation (Context, Container, Component, Code)", 3),
]

# (diagram_type_id, notation_id, is_default)
_MAPPINGS = [
    # component: simple*, uml, archimate, c4
    ("component", "simple", 1),
    ("component", "uml", 0),
    ("component", "archimate", 0),
    ("component", "c4", 0),
    # sequence: simple, uml*
    ("sequence", "simple", 0),
    ("sequence", "uml", 1),
    # class: uml*
    ("class", "uml", 1),
    # deployment: simple, uml, archimate, c4*
    ("deployment", "simple", 0),
    ("deployment", "uml", 0),
    ("deployment", "archimate", 0),
    ("deployment", "c4", 1),
    # process: simple, uml, archimate*
    ("process", "simple", 0),
    ("process", "uml", 0),
    ("process", "archimate", 1),
    # roadmap: simple*
    ("roadmap", "simple", 1),
    # free_form: simple*, uml, archimate, c4
    ("free_form", "simple", 1),
    ("free_form", "uml", 0),
    ("free_form", "archimate", 0),
    ("free_form", "c4", 0),
]


async def up(db: aiosqlite.Connection) -> None:
    """Create registry tables, add notation columns, seed data, migrate existing rows."""

    # 1. Create diagram_types table
    await db.execute("""
        CREATE TABLE IF NOT EXISTS diagram_types (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            display_order INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1
        )
    """)

    # 2. Create notations table
    await db.execute("""
        CREATE TABLE IF NOT EXISTS notations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            display_order INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1
        )
    """)

    # 3. Create mapping table
    await db.execute("""
        CREATE TABLE IF NOT EXISTS diagram_type_notations (
            diagram_type_id TEXT NOT NULL REFERENCES diagram_types(id),
            notation_id TEXT NOT NULL REFERENCES notations(id),
            is_default INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (diagram_type_id, notation_id)
        )
    """)

    # 4. Add notation column to diagrams (if missing)
    cursor = await db.execute("PRAGMA table_info(diagrams)")
    columns = [row[1] for row in await cursor.fetchall()]

    if "notation" not in columns:
        await db.execute("ALTER TABLE diagrams ADD COLUMN notation TEXT")

    if "detected_notations" not in columns:
        await db.execute("ALTER TABLE diagrams ADD COLUMN detected_notations TEXT")

    # 5. Seed diagram types (idempotent)
    for dt_id, dt_name, dt_desc, dt_order in _DIAGRAM_TYPES:
        await db.execute(
            "INSERT OR IGNORE INTO diagram_types (id, name, description, display_order) "
            "VALUES (?, ?, ?, ?)",
            (dt_id, dt_name, dt_desc, dt_order),
        )

    # 6. Seed notations (idempotent)
    for n_id, n_name, n_desc, n_order in _NOTATIONS:
        await db.execute(
            "INSERT OR IGNORE INTO notations (id, name, description, display_order) "
            "VALUES (?, ?, ?, ?)",
            (n_id, n_name, n_desc, n_order),
        )

    # 7. Seed mappings (idempotent)
    for dt_id, n_id, is_default in _MAPPINGS:
        await db.execute(
            "INSERT OR IGNORE INTO diagram_type_notations "
            "(diagram_type_id, notation_id, is_default) VALUES (?, ?, ?)",
            (dt_id, n_id, is_default),
        )

    # 8. Migrate existing diagrams: populate notation and normalize diagram_type
    # Only migrate rows where notation is NULL (not yet migrated)
    cursor = await db.execute(
        "SELECT id, diagram_type FROM diagrams WHERE notation IS NULL"
    )
    rows = await cursor.fetchall()
    for diagram_id, old_type in rows:
        notation = "simple"
        new_type = old_type

        if old_type == "uml":
            notation = "uml"
            new_type = "component"
        elif old_type == "archimate":
            notation = "archimate"
            new_type = "component"
        elif old_type and old_type.startswith("c4"):
            notation = "c4"
            new_type = "component"
        elif old_type == "simple":
            notation = "simple"
            new_type = "component"
        elif old_type == "sequence":
            notation = "uml"
            new_type = "sequence"
        elif old_type == "roadmap":
            notation = "simple"
            new_type = "roadmap"
        elif old_type == "component":
            notation = "simple"
            new_type = "component"
        else:
            # Unknown type — default to component/simple
            notation = "simple"
            new_type = "component"

        await db.execute(
            "UPDATE diagrams SET notation = ?, diagram_type = ? WHERE id = ?",
            (notation, new_type, diagram_id),
        )

    # 9. Run auto-detection on existing diagrams to populate detected_notations
    cursor = await db.execute(
        "SELECT d.id, dv.data FROM diagrams d "
        "JOIN diagram_versions dv ON d.id = dv.diagram_id "
        "AND d.current_version = dv.version "
        "WHERE d.detected_notations IS NULL AND d.is_deleted = 0"
    )
    detect_rows = await cursor.fetchall()
    for diagram_id, data_json in detect_rows:
        try:
            data = json.loads(data_json) if data_json else {}
            detected = _detect_notations_inline(data)
            await db.execute(
                "UPDATE diagrams SET detected_notations = ? WHERE id = ?",
                (json.dumps(detected), diagram_id),
            )
        except (json.JSONDecodeError, TypeError):
            await db.execute(
                "UPDATE diagrams SET detected_notations = '[]' WHERE id = ?",
                (diagram_id,),
            )

    await db.commit()


def _detect_notations_inline(data: dict) -> list[str]:
    """Inline detection for migration — mirrors notation_detection.py."""
    uml = {'class', 'object', 'use_case', 'state', 'activity', 'node',
           'interface_uml', 'enumeration', 'abstract_class', 'component_uml', 'package_uml'}
    c4 = {'person', 'software_system', 'software_system_external', 'container',
          'c4_component', 'code_element', 'deployment_node', 'infrastructure_node',
          'container_instance'}
    archimate = {
        'business_actor', 'business_role', 'business_process', 'business_service',
        'business_object', 'business_function', 'business_interaction', 'business_event',
        'business_collaboration', 'business_interface',
        'application_component', 'application_service', 'application_interface',
        'application_function', 'application_interaction', 'application_event',
        'application_collaboration', 'application_process',
        'technology_node', 'technology_service', 'technology_interface',
        'technology_function', 'technology_interaction', 'technology_event',
        'technology_collaboration', 'technology_process', 'technology_artifact',
        'technology_device',
        'stakeholder', 'driver', 'assessment', 'goal', 'outcome', 'principle',
        'requirement_archimate', 'constraint_archimate',
        'resource', 'capability', 'course_of_action', 'value_stream',
        'work_package', 'deliverable', 'implementation_event', 'plateau', 'gap',
    }
    simple = {'component', 'service', 'interface', 'package', 'actor', 'database', 'queue'}
    universal = {'note', 'boundary', 'modelref'}

    notations = set()
    for nd in data.get('nodes', []):
        if not isinstance(nd, dict):
            continue
        nd_data = nd.get('data', {})
        if not isinstance(nd_data, dict):
            continue
        entity_type = nd_data.get('entityType', '')
        if entity_type in universal:
            continue
        elif entity_type in uml:
            notations.add('uml')
        elif entity_type in c4:
            notations.add('c4')
        elif entity_type in archimate:
            notations.add('archimate')
        elif entity_type in simple:
            notations.add('simple')
    return sorted(notations)
