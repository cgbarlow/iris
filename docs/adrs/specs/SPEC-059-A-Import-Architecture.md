# SPEC-059-A: SparxEA Import Architecture

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-059-A |
| **ADR** | [ADR-059](../ADR-059-SparxEA-Import.md) |
| **Status** | Implemented |

## Module Structure

```
backend/app/import_sparx/
├── __init__.py
├── reader.py      — Read .qea SQLite tables into dataclasses
├── mapper.py      — Type mapping dictionaries
├── converter.py   — Coordinate and colour conversion
├── service.py     — Import orchestrator
└── router.py      — POST /api/import/sparx endpoint
```

## SparxEA File Format

`.qea` files are SQLite 3 databases (EA 16+). Key tables:
- `t_object` — elements (Object_ID, Object_Type, Name, Package_ID, Note)
- `t_package` — hierarchy (Package_ID, Name, Parent_ID)
- `t_connector` — relationships (Connector_ID, Connector_Type, Start_Object_ID, End_Object_ID)
- `t_diagram` — diagrams (Diagram_ID, Name, Diagram_Type, Package_ID)
- `t_diagramobjects` — element positions on diagrams
- `t_attribute` — class attributes (Object_ID, Name, Type)

## Type Mapping

### Object Types
| SparxEA | Iris | Category |
|---------|------|----------|
| Class | class | UML |
| Interface | interface_uml | UML |
| Object | object | UML |
| UseCase | use_case | UML |
| Actor | actor | Simple |
| Component | component | Simple |
| Enumeration | enumeration | UML |
| Package | (hierarchy) | Model parent |

### Connector Types
| SparxEA | Iris |
|---------|------|
| Association | association |
| Aggregation | aggregation |
| Composition | composition |
| Generalization | generalization |
| Realisation | realization |
| Dependency | dependency |
| Usage | usage |

### Diagram Types
| SparxEA | Iris model_type |
|---------|----------------|
| Class/Logical/Use Case/Component | uml |
| Sequence | sequence |
| Custom | archimate |

## Import Process

1. Read all data from .qea via aiosqlite
2. Create Iris models for packages (topological order, preserving hierarchy)
3. Create entities for elements (with class attributes if present)
4. Create relationships for connectors
5. Create diagram models with canvas node/edge data from diagram objects
6. Return ImportSummary with counts and warnings

## API

`POST /api/import/sparx` — accepts multipart `UploadFile`, returns ImportSummary JSON.
