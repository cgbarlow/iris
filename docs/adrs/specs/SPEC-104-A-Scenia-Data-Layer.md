# SPEC-104-A: Scenia Data Layer

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-104-A |
| **ADR** | [ADR-104](../ADR-104-Scenia-Schema-Mapping.md) |
| **Status** | Draft |
| **Date** | 2026-03-25 |

---

## Overview

Scenia entities map to Iris elements/relationships. Scenia-specific lookup tables get their own tables.

## Schema Mapping

Scenia entities are stored as Iris elements with a `scenia_` prefix on `element_type`:

| Scenia Entity | element_type | Key data fields |
|---------------|--------------|-----------------|
| Strategy | scenia_strategy | vision, description, objectives |
| Programme | scenia_programme | strategyId, description, budget |
| Initiative | scenia_initiative | programmeId, assetId, startDate, endDate, budget, progress, status |
| Asset | scenia_asset | categoryId, description, owner, maturityRating |
| Application | scenia_application | assetId, statusId, description |
| AppSegment | scenia_app_segment | applicationId, startDate, endDate, statusId, row |
| Milestone | scenia_milestone | assetId, date, severity |
| Resource | scenia_resource | type, availability, cost |
| Dependency | relationship scenia_dependency | type (blocks/requires/related) |

## New Tables (m032)

```sql
CREATE TABLE IF NOT EXISTS scenia_timeline_settings (
    id TEXT PRIMARY KEY,
    set_id TEXT NOT NULL,
    start_date TEXT,
    end_date TEXT,
    view_mode TEXT,
    zoom_level REAL,
    data TEXT DEFAULT '{}',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scenia_versions (
    id TEXT PRIMARY KEY,
    set_id TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    name TEXT NOT NULL,
    data TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scenia_asset_categories (
    id TEXT PRIMARY KEY,
    set_id TEXT NOT NULL,
    name TEXT NOT NULL,
    color TEXT,
    display_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS scenia_application_statuses (
    id TEXT PRIMARY KEY,
    set_id TEXT NOT NULL,
    name TEXT NOT NULL,
    color TEXT,
    display_order INTEGER NOT NULL DEFAULT 0
);
```

## API Endpoints

All Scenia routes are gated on the scenia extension being enabled.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/scenia/data` | Bulk read — returns all Scenia entity arrays |
| PUT | `/api/scenia/data` | Bulk write — atomic save of all Scenia entity arrays |
| GET | `/api/scenia/strategies` | List strategies |
| POST | `/api/scenia/strategies` | Create strategy |
| GET | `/api/scenia/strategies/{id}` | Get strategy |
| PUT | `/api/scenia/strategies/{id}` | Update strategy |
| DELETE | `/api/scenia/strategies/{id}` | Delete strategy |
| GET | `/api/scenia/programmes` | List programmes |
| POST | `/api/scenia/programmes` | Create programme |
| GET | `/api/scenia/programmes/{id}` | Get programme |
| PUT | `/api/scenia/programmes/{id}` | Update programme |
| DELETE | `/api/scenia/programmes/{id}` | Delete programme |
| GET | `/api/scenia/initiatives` | List initiatives |
| POST | `/api/scenia/initiatives` | Create initiative |
| GET | `/api/scenia/initiatives/{id}` | Get initiative |
| PUT | `/api/scenia/initiatives/{id}` | Update initiative |
| DELETE | `/api/scenia/initiatives/{id}` | Delete initiative |
| GET | `/api/scenia/assets` | List assets |
| POST | `/api/scenia/assets` | Create asset |
| GET | `/api/scenia/assets/{id}` | Get asset |
| PUT | `/api/scenia/assets/{id}` | Update asset |
| DELETE | `/api/scenia/assets/{id}` | Delete asset |
| GET | `/api/scenia/applications` | List applications |
| POST | `/api/scenia/applications` | Create application |
| GET | `/api/scenia/applications/{id}` | Get application |
| PUT | `/api/scenia/applications/{id}` | Update application |
| DELETE | `/api/scenia/applications/{id}` | Delete application |
| GET | `/api/scenia/app-segments` | List app segments |
| POST | `/api/scenia/app-segments` | Create app segment |
| GET | `/api/scenia/app-segments/{id}` | Get app segment |
| PUT | `/api/scenia/app-segments/{id}` | Update app segment |
| DELETE | `/api/scenia/app-segments/{id}` | Delete app segment |
| GET | `/api/scenia/milestones` | List milestones |
| POST | `/api/scenia/milestones` | Create milestone |
| GET | `/api/scenia/milestones/{id}` | Get milestone |
| PUT | `/api/scenia/milestones/{id}` | Update milestone |
| DELETE | `/api/scenia/milestones/{id}` | Delete milestone |
| GET | `/api/scenia/resources` | List resources |
| POST | `/api/scenia/resources` | Create resource |
| GET | `/api/scenia/resources/{id}` | Get resource |
| PUT | `/api/scenia/resources/{id}` | Update resource |
| DELETE | `/api/scenia/resources/{id}` | Delete resource |
| GET | `/api/scenia/dependencies` | List dependencies |
| POST | `/api/scenia/dependencies` | Create dependency |
| DELETE | `/api/scenia/dependencies/{id}` | Delete dependency |
| GET | `/api/scenia/timeline-settings` | Get timeline settings |
| PUT | `/api/scenia/timeline-settings` | Update timeline settings |
| GET | `/api/scenia/versions` | List versions |
| POST | `/api/scenia/versions` | Create version |
| GET | `/api/scenia/asset-categories` | List asset categories |
| POST | `/api/scenia/asset-categories` | Create asset category |
| PUT | `/api/scenia/asset-categories/{id}` | Update asset category |
| DELETE | `/api/scenia/asset-categories/{id}` | Delete asset category |
| GET | `/api/scenia/application-statuses` | List application statuses |
| POST | `/api/scenia/application-statuses` | Create application status |
| PUT | `/api/scenia/application-statuses/{id}` | Update application status |
| DELETE | `/api/scenia/application-statuses/{id}` | Delete application status |

## Backend Module Structure

```
backend/app/scenia/
├── __init__.py
├── models.py         — Pydantic models for all Scenia entities
├── service.py        — CRUD operations, bulk data read/write
├── router.py         — APIRouter(prefix="/api/scenia")
└── dependencies.py   — require_scenia_enabled dependency
```

## Acceptance Criteria

1. Scenia entities persist as Iris elements with correct element_type
2. Bulk data endpoint returns all entity arrays
3. All routes gated on scenia extension being enabled
4. CRUD operations work for all entity types
5. Timeline settings and versions persist correctly
