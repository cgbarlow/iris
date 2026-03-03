# SPEC-070-A: Edge Import Metadata

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-070-A |
| **ADR** | [ADR-070](../ADR-070-Full-Edge-Support.md) |
| **Status** | Draft |
| **Date** | 2026-03-03 |

---

## Overview

SparxEA connectors store rich metadata including direction, cardinality, roles, stereotypes, and routing style. This spec extends the import pipeline to read, map, and persist this metadata on both relationship records and canvas edge data.

## Changes

### 1. Reader (`backend/app/import_sparx/reader.py`)

**QeaConnector dataclass** -- add fields after `Notes`:
- `Direction: str | None = None`
- `SourceCard: str | None = None`
- `DestCard: str | None = None`
- `SourceRole: str | None = None`
- `DestRole: str | None = None`
- `Stereotype: str | None = None`
- `RouteStyle: int | None = None`
- `SourceIsNavigable: str | None = None`
- `DestIsNavigable: str | None = None`

**`read_connectors()` SQL** -- extend SELECT to include `Direction, SourceCard, DestCard, SourceRole, DestRole, Stereotype, RouteStyle, SourceIsNavigable, DestIsNavigable` and parse into the new fields.

### 2. Mapper (`backend/app/import_sparx/mapper.py`)

Add `"Nesting": "contains"` to `CONNECTOR_TYPE_MAP`.

### 3. Service (`backend/app/import_sparx/service.py`)

**Relationship data** -- build `rel_data` dict conditionally from connector fields:
- `direction` from `conn.Direction`
- `sourceCardinality` from `conn.SourceCard`
- `targetCardinality` from `conn.DestCard`
- `sourceRole` from `conn.SourceRole`
- `targetRole` from `conn.DestRole`
- `stereotype` from `conn.Stereotype`

Pass `data=rel_data` to `create_relationship()`.

**Canvas edge data** -- extend the edge `data` dict with:
- `sourceCardinality`, `targetCardinality`, `sourceRole`, `targetRole`, `stereotype`, `direction` (conditional on non-None)
- `routingType` mapped from `conn.RouteStyle`: `{0: "bezier", 3: "step"}`, default `"bezier"`

## Route Style Mapping

| SparxEA RouteStyle | Iris routingType |
|--------------------|------------------|
| 0 | bezier |
| 3 | step |
| other | bezier (default) |

## Acceptance Criteria

1. `QeaConnector` reads Direction, SourceCard, DestCard, SourceRole, DestRole, Stereotype, RouteStyle from sample file
2. `Nesting` connector type maps to `contains`
3. Relationship `data` contains connector metadata (direction, cardinality, roles) after import
4. Canvas edge `data` contains `routingType` mapped from RouteStyle
5. Canvas edge `data` contains cardinality and role fields when present on connector
