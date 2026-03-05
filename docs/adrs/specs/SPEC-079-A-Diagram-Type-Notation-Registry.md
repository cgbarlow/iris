# SPEC-079-A: Diagram Type and Notation Registry

## Overview

Implements ADR-079: separates diagram structural type from visual notation via database registry tables.

## Database Schema

### New Tables

```sql
CREATE TABLE diagram_types (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    display_order INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE notations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    display_order INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE diagram_type_notations (
    diagram_type_id TEXT NOT NULL REFERENCES diagram_types(id),
    notation_id TEXT NOT NULL REFERENCES notations(id),
    is_default INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (diagram_type_id, notation_id)
);
```

### Schema Changes

- `diagrams` table: `ALTER TABLE diagrams ADD COLUMN notation TEXT`
- `diagrams` table: `ALTER TABLE diagrams ADD COLUMN detected_notations TEXT`

### Seed Data

**Diagram Types:** component, sequence, class, deployment, process, roadmap, free_form

**Notations:** simple, uml, archimate, c4

**Mapping Matrix** (* = default):

| Type | Simple | UML | ArchiMate | C4 |
|------|--------|-----|-----------|-----|
| component | * | yes | yes | yes |
| sequence | yes | * | | |
| class | | * | | |
| deployment | yes | yes | yes | * |
| process | yes | yes | * | |
| roadmap | * | | | |
| free_form | * | yes | yes | yes |

### Data Migration

For existing diagrams:
- `diagram_type` in (uml) → notation=uml, diagram_type=component
- `diagram_type` in (archimate) → notation=archimate, diagram_type=component
- `diagram_type` starts with c4 → notation=c4, diagram_type=component
- `diagram_type` in (simple) → notation=simple, diagram_type=component
- `diagram_type` = sequence → notation=uml (default for sequence)
- `diagram_type` = roadmap → notation=simple (default for roadmap)
- Everything else → notation=simple

## API Endpoints

### Registry

- `GET /api/registry/diagram-types` — List all active diagram types with notation mappings
- `GET /api/registry/notations` — List all active notations
- `PUT /api/registry/diagrams/{diagram_id}/notation` — Change a diagram's notation

### Modified Endpoints

- `POST /api/diagrams` — Accepts optional `notation` parameter
- `GET /api/diagrams` — Returns `notation` and `detected_notations` fields
- `GET /api/diagrams/{id}` — Returns `notation` and `detected_notations` fields

## Auto-Detection

The `detect_notations()` function scans canvas `data.nodes` and maps each node's `entityType` to a notation:
- UML types: class, object, use_case, state, activity, node, interface_uml, enumeration, abstract_class, component_uml, package_uml
- C4 types: person, software_system, software_system_external, container, c4_component, code_element, deployment_node, infrastructure_node, container_instance
- ArchiMate types: ~45 types across 6 layers
- Simple types: component, service, interface, package, actor, database, queue
- Universal types (ignored): note, boundary, modelref

Result stored as JSON array in `detected_notations` column.

## Frontend Changes

- DiagramDialog: Two-step type/notation selection
- Canvas page: Read notation from diagram.notation, show notation switcher in edit mode
- EntityDialog: Filter entity types by current notation
- Diagram list/gallery: Show detected_notations badges
