# SPEC-045-A: Example Architecture Models Seed

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-045-A |
| **ADR Reference** | [ADR-045: Example Iris Architecture Models](../ADR-045-Example-Iris-Architecture-Models.md) |
| **Date** | 2026-03-01 |
| **Status** | Active |

---

## Overview

This specification details the idempotent seed script that creates example entities and a model demonstrating Iris's own architecture. The seed runs during application startup, after migrations and existing seeds (roles, settings), and creates content only on first run.

---

## A. Seed Module Location

File: `app/seed/example_models.py`

The module exposes a single public function:

```python
async def seed_example_models(db: aiosqlite.Connection) -> None
```

---

## B. Idempotency and Prerequisites

The seed has two guard checks:

**1. Active user prerequisite:** The seed skips if no active users exist yet (initial `/api/auth/setup` has not been completed). This prevents the system user from being created before the first admin user, which would cause the setup endpoint to reject with "Setup already completed" (it checks `SELECT COUNT(*) FROM users`).

```python
cursor = await db.execute(
    "SELECT COUNT(*) FROM users WHERE is_active = 1"
)
row = await cursor.fetchone()
if not row or row[0] == 0:
    return  # Setup not yet completed
```

**2. Tag-based idempotency:** The seed checks for existing entity tags with `tag = 'example'` before proceeding:

```python
cursor = await db.execute(
    "SELECT COUNT(*) FROM entity_tags WHERE tag = 'example'"
)
row = await cursor.fetchone()
if row and row[0] > 0:
    return  # Already seeded
```

This means the seed runs exactly once, on the first startup after initial admin setup. If a user deletes some but not all example entities, the seed will not re-create the missing ones. This is intentional: partial cleanup indicates user intent to customise.

---

## C. System User

A deactivated system user is created to satisfy foreign key constraints on `created_by` columns:

| Field | Value |
|-------|-------|
| ID | `00000000-0000-0000-0000-000000000000` |
| Username | `system` |
| Password Hash | `!no-login-seed-user` (invalid, cannot authenticate) |
| Role | `viewer` |
| Active | `0` (deactivated) |

The user is created with `INSERT OR IGNORE` so it is safe across multiple runs.

---

## D. Entity Definitions

Five component entities representing Iris's architecture:

| Node ID | Name | Description |
|---------|------|-------------|
| n1 | Frontend | SvelteKit + Svelte 5 runes application with @xyflow/svelte canvas |
| n2 | Backend | FastAPI REST API with JWT authentication and RBAC |
| n3 | Database | SQLite with WAL mode, FTS5 search, and versioned schema |
| n4 | Auth Service | Argon2id password hashing, JWT HS256 tokens, refresh rotation |
| n5 | Canvas Engine | @xyflow/svelte interactive graph editor with undo/redo |

All entities are tagged with `iris` and `example`.

Entity IDs are generated deterministically using `uuid.uuid5` with a fixed namespace, ensuring stability across runs.

---

## E. Model Definition

| Field | Value |
|-------|-------|
| Name | Iris Architecture |
| Type | component |
| Tags | `iris`, `example`, `template` |
| Description | Component model showing the internal architecture of the Iris modelling tool |

---

## F. Canvas Layout

### F.1 Node Positions

```
                    Frontend (400, 50)
                        |
         Auth Service   |    Canvas Engine
         (100, 250)  Backend  (700, 250)
                    (400, 250)
                        |
                    Database
                    (400, 450)
```

### F.2 Edges

| Edge ID | Source | Target | Type | Label |
|---------|--------|--------|------|-------|
| e1-2 | Frontend | Backend | uses | API calls |
| e2-3 | Backend | Database | uses | SQL queries |
| e1-4 | Frontend | Auth Service | uses | Login / refresh |
| e2-4 | Backend | Auth Service | uses | Token validation |
| e1-5 | Frontend | Canvas Engine | contains | Renders canvas |
| e4-3 | Auth Service | Database | uses | User store |

### F.3 Data Format

Each node follows the canvas node schema:

```json
{
    "id": "n1",
    "type": "component",
    "position": {"x": 400, "y": 50},
    "data": {
        "label": "Frontend",
        "entityType": "component",
        "description": "SvelteKit + Svelte 5",
        "entityId": "<generated-uuid>"
    }
}
```

Each edge follows the canvas edge schema:

```json
{
    "id": "e1-2",
    "source": "n1",
    "target": "n2",
    "type": "uses",
    "data": {
        "relationshipType": "uses",
        "label": "API calls"
    }
}
```

---

## G. Startup Integration

The seed is called from `app/startup.py` in the `initialize_databases` function, after existing seeds:

```python
# 4c. Seed example models (Iris architecture demo)
await seed_example_models(db_manager.main_db)
```

The search index rebuild (step 3b) runs before seeding, but the seed data will be picked up on the next startup since the FTS rebuild re-indexes all non-deleted entities and models.

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| Seed skips if no active users exist | Start fresh DB, run startup; verify no entities or models created |
| Seed creates 5 entities after setup | Complete initial setup, restart; verify 5 entities with system `created_by` |
| Seed creates 1 model after setup | Complete initial setup, restart; verify "Iris Architecture" model exists |
| Entities tagged with `iris` and `example` | Query `entity_tags`; verify 10 tag rows (5 entities x 2 tags) |
| Model tagged with `iris`, `example`, `template` | Query `model_tags`; verify 3 tag rows |
| Model data contains 5 nodes | Parse model version data JSON; verify `nodes` array length |
| Model data contains 6 edges | Parse model version data JSON; verify `edges` array length |
| Node entityId references match entity IDs | Verify each node's `data.entityId` matches an entity `id` |
| Seed is idempotent | Run startup twice; verify no duplicate entities or errors |
| System user is deactivated | Query `users` where `id = '0000...'`; verify `is_active = 0` |
| Entities appear in search after next restart | Search for "Frontend"; verify entity appears in results |
| Setup endpoint not affected | Fresh DB startup; verify `/api/auth/setup` still works |

---

*This specification implements [ADR-045](../ADR-045-Example-Iris-Architecture-Models.md).*
