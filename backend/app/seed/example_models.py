"""Idempotent seed: example models demonstrating Iris's own architecture.

Creates entities representing the Iris system and four models:
  1. Iris Architecture (component) — core component overview
  2. API Request Flow (sequence) — login and data fetch sequence
  3. Data Layer (component) — database, versioning, and search internals
  4. Iris Enterprise View (archimate) — high-level enterprise architecture

All entities are tagged with 'iris' and 'example'; models are tagged with
'iris', 'example', and 'template'.

Idempotency: the seed checks for existing entity_tags with tag='example'
and skips entirely if any are found.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

_SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000000"

# ── Entity definitions ──────────────────────────────────────────────────────
# (node_id, entity_type, name, description)
_ENTITIES = [
    # Core components (used in Architecture model)
    ("n1", "component", "Frontend",
     "SvelteKit + Svelte 5 runes application with @xyflow/svelte canvas"),
    ("n2", "component", "Backend",
     "FastAPI REST API with JWT authentication and RBAC"),
    ("n3", "database", "Database",
     "SQLite with WAL mode, FTS5 search, and versioned schema migrations"),
    ("n4", "service", "Auth Service",
     "Argon2id password hashing, JWT HS256 tokens, refresh rotation"),
    ("n5", "component", "Canvas Engine",
     "@xyflow/svelte interactive graph editor with undo/redo and multiple view modes"),
    # Additional entities for richer models
    ("n6", "service", "Search Service",
     "Full-text search powered by SQLite FTS5 with ranking and highlighting"),
    ("n7", "service", "Audit Service",
     "Middleware-based audit logging capturing all state-changing API operations"),
    ("n8", "component", "Model Renderer",
     "Thumbnail generator producing SVG previews of canvas models for gallery display"),
    ("n9", "interface", "REST API",
     "JSON REST interface at /api/* with OpenAPI documentation and JWT bearer auth"),
    ("n10", "actor", "User",
     "Human user interacting with the system through a web browser"),
    ("n11", "actor", "Admin",
     "Administrator with elevated privileges for user management and system settings"),
    ("n12", "component", "Version Control",
     "Entity and model versioning with optimistic concurrency via ETags"),
    ("n13", "queue", "Event Bus",
     "Internal event dispatch for audit logging and thumbnail regeneration"),
    ("n14", "component", "Export Engine",
     "Diagram export to SVG, PNG, and PDF formats using html-to-image"),
    ("n15", "package", "Middleware Stack",
     "CORS, rate limiting, security headers, and audit middleware layers"),
]

_ENTITY_TAGS = ["iris", "example"]
_MODEL_TAGS = ["iris", "example", "template"]

# Relationships between entities: (index, source_node, target_node, rel_type, label, description)
# These create actual relationship records in the DB so entity detail pages show connections.
_RELATIONSHIPS = [
    (0, "n10", "n1", "uses", "Browses",
     "User interacts with the Frontend via web browser"),
    (1, "n11", "n1", "uses", "Manages system",
     "Admin accesses Frontend for user and settings management"),
    (2, "n1", "n9", "uses", "API calls",
     "Frontend communicates with Backend through the REST API interface"),
    (3, "n9", "n2", "implements", "Serves",
     "REST API interface is implemented by the Backend"),
    (4, "n1", "n5", "contains", "Embeds",
     "Frontend contains the Canvas Engine as an embedded component"),
    (5, "n5", "n14", "uses", "Exports via",
     "Canvas Engine uses Export Engine for SVG/PNG/PDF output"),
    (6, "n1", "n2", "depends_on", "REST calls",
     "Frontend depends on Backend for all data operations"),
    (7, "n2", "n4", "uses", "Token validation",
     "Backend delegates authentication to Auth Service"),
    (8, "n2", "n3", "uses", "SQL queries",
     "Backend reads and writes data through SQLite"),
    (9, "n4", "n3", "uses", "User store",
     "Auth Service reads user credentials from Database"),
    (10, "n2", "n12", "uses", "Version entities",
     "Backend uses Version Control for entity/model versioning"),
    (11, "n2", "n6", "uses", "Query search",
     "Backend delegates full-text queries to Search Service"),
    (12, "n2", "n7", "uses", "Log operations",
     "Backend routes state-changing operations through Audit Service"),
    (13, "n12", "n3", "uses", "Read/write versions",
     "Version Control reads and writes versioned records in Database"),
    (14, "n6", "n3", "depends_on", "FTS5 queries",
     "Search Service depends on Database FTS5 indexes"),
    (15, "n7", "n13", "uses", "Emit events",
     "Audit Service emits events to Event Bus"),
    (16, "n13", "n3", "uses", "Persist audit logs",
     "Event Bus persists audit log entries in Database"),
    (17, "n8", "n3", "uses", "Read model data",
     "Model Renderer reads model canvas data from Database"),
    (18, "n11", "n15", "uses", "Configures",
     "Admin configures Middleware Stack settings"),
    (19, "n15", "n2", "contains", "Wraps",
     "Middleware Stack wraps Backend request handling"),
]


def _gen_id(prefix: str, index: int) -> str:
    """Generate a deterministic UUID v5 ID for seed data."""
    namespace = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    return str(uuid.uuid5(namespace, f"{prefix}-{index}"))


# ── Model 1: Iris Architecture (component) ──────────────────────────────────

def _build_architecture_model(
    eids: dict[str, str], rids: dict[str, str],
) -> dict[str, object]:
    """Core component overview with Frontend, Backend, DB, Auth, Canvas."""
    nodes = [
        {"id": "n10", "type": "actor",
         "position": {"x": 400, "y": 0},
         "data": {"label": "User", "entityType": "actor",
                  "description": "Web browser user", "entityId": eids["n10"]}},
        {"id": "n1", "type": "component",
         "position": {"x": 350, "y": 150},
         "data": {"label": "Frontend", "entityType": "component",
                  "description": "SvelteKit + Svelte 5 runes application",
                  "entityId": eids["n1"]}},
        {"id": "n9", "type": "interface",
         "position": {"x": 370, "y": 330},
         "data": {"label": "REST API", "entityType": "interface",
                  "description": "/api/* JSON endpoints", "entityId": eids["n9"]}},
        {"id": "n2", "type": "component",
         "position": {"x": 350, "y": 480},
         "data": {"label": "Backend", "entityType": "component",
                  "description": "FastAPI REST API with RBAC",
                  "entityId": eids["n2"]}},
        {"id": "n4", "type": "service",
         "position": {"x": 60, "y": 480},
         "data": {"label": "Auth Service", "entityType": "service",
                  "description": "JWT + Argon2id", "entityId": eids["n4"]}},
        {"id": "n5", "type": "component",
         "position": {"x": 650, "y": 150},
         "data": {"label": "Canvas Engine", "entityType": "component",
                  "description": "@xyflow/svelte editor",
                  "entityId": eids["n5"]}},
        {"id": "n14", "type": "component",
         "position": {"x": 650, "y": 330},
         "data": {"label": "Export Engine", "entityType": "component",
                  "description": "SVG/PNG/PDF export", "entityId": eids["n14"]}},
        {"id": "n3", "type": "database",
         "position": {"x": 370, "y": 650},
         "data": {"label": "Database", "entityType": "database",
                  "description": "SQLite + WAL + FTS5", "entityId": eids["n3"]}},
    ]
    edges = [
        {"id": "e10-1", "source": "n10", "target": "n1", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Browses",
                  "relationshipId": rids["r0"]}},
        {"id": "e1-9", "source": "n1", "target": "n9", "type": "uses",
         "data": {"relationshipType": "uses", "label": "API calls",
                  "relationshipId": rids["r2"]}},
        {"id": "e9-2", "source": "n9", "target": "n2", "type": "implements",
         "data": {"relationshipType": "implements", "label": "Serves",
                  "relationshipId": rids["r3"]}},
        {"id": "e1-5", "source": "n1", "target": "n5", "type": "contains",
         "data": {"relationshipType": "contains", "label": "Embeds",
                  "relationshipId": rids["r4"]}},
        {"id": "e5-14", "source": "n5", "target": "n14", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Exports via",
                  "relationshipId": rids["r5"]}},
        {"id": "e2-4", "source": "n2", "target": "n4", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Token validation",
                  "relationshipId": rids["r7"]}},
        {"id": "e2-3", "source": "n2", "target": "n3", "type": "uses",
         "data": {"relationshipType": "uses", "label": "SQL queries",
                  "relationshipId": rids["r8"]}},
        {"id": "e4-3", "source": "n4", "target": "n3", "type": "uses",
         "data": {"relationshipType": "uses", "label": "User store",
                  "relationshipId": rids["r9"]}},
    ]
    return {"nodes": nodes, "edges": edges}


# ── Model 2: API Request Flow (sequence) ────────────────────────────────────

def _build_sequence_model(
    eids: dict[str, str], rids: dict[str, str],
) -> dict[str, object]:
    """Sequence diagram: user login then fetch model data."""
    participants = [
        {"id": "p1", "name": "Browser", "type": "actor",
         "entityId": eids["n10"]},
        {"id": "p2", "name": "Frontend", "type": "component",
         "entityId": eids["n1"]},
        {"id": "p3", "name": "Backend", "type": "component",
         "entityId": eids["n2"]},
        {"id": "p4", "name": "Auth Service", "type": "service",
         "entityId": eids["n4"]},
        {"id": "p5", "name": "Database", "type": "component",
         "entityId": eids["n3"]},
    ]
    messages = [
        {"id": "m1", "from": "p1", "to": "p2",
         "label": "Navigate to /models", "type": "sync", "order": 0},
        {"id": "m2", "from": "p2", "to": "p3",
         "label": "POST /api/auth/login", "type": "sync", "order": 1},
        {"id": "m3", "from": "p3", "to": "p4",
         "label": "Verify credentials", "type": "sync", "order": 2},
        {"id": "m4", "from": "p4", "to": "p5",
         "label": "SELECT user by username", "type": "sync", "order": 3},
        {"id": "m5", "from": "p5", "to": "p4",
         "label": "User record", "type": "reply", "order": 4},
        {"id": "m6", "from": "p4", "to": "p3",
         "label": "JWT access + refresh tokens", "type": "reply", "order": 5},
        {"id": "m7", "from": "p3", "to": "p2",
         "label": "200 {access_token}", "type": "reply", "order": 6},
        {"id": "m8", "from": "p2", "to": "p3",
         "label": "GET /api/models (Bearer token)", "type": "sync", "order": 7},
        {"id": "m9", "from": "p3", "to": "p5",
         "label": "SELECT models with versions", "type": "sync", "order": 8},
        {"id": "m10", "from": "p5", "to": "p3",
         "label": "Model list", "type": "reply", "order": 9},
        {"id": "m11", "from": "p3", "to": "p2",
         "label": "200 [{model}, ...]", "type": "reply", "order": 10},
        {"id": "m12", "from": "p2", "to": "p1",
         "label": "Render gallery", "type": "reply", "order": 11},
    ]
    activations = [
        {"participantId": "p2", "startOrder": 0, "endOrder": 11},
        {"participantId": "p3", "startOrder": 1, "endOrder": 6},
        {"participantId": "p4", "startOrder": 2, "endOrder": 5},
        {"participantId": "p5", "startOrder": 3, "endOrder": 4},
        {"participantId": "p3", "startOrder": 7, "endOrder": 10},
        {"participantId": "p5", "startOrder": 8, "endOrder": 9},
    ]
    return {
        "participants": participants,
        "messages": messages,
        "activations": activations,
    }


# ── Model 3: Data Layer (component) ─────────────────────────────────────────

def _build_data_layer_model(
    eids: dict[str, str], rids: dict[str, str],
) -> dict[str, object]:
    """Component model showing database, versioning, search, and audit."""
    nodes = [
        {"id": "n2", "type": "component",
         "position": {"x": 350, "y": 50},
         "data": {"label": "Backend", "entityType": "component",
                  "description": "FastAPI application server",
                  "entityId": eids["n2"]}},
        {"id": "n12", "type": "component",
         "position": {"x": 60, "y": 230},
         "data": {"label": "Version Control", "entityType": "component",
                  "description": "Optimistic concurrency with ETags",
                  "entityId": eids["n12"]}},
        {"id": "n6", "type": "service",
         "position": {"x": 350, "y": 230},
         "data": {"label": "Search Service", "entityType": "service",
                  "description": "FTS5 full-text search with ranking",
                  "entityId": eids["n6"]}},
        {"id": "n7", "type": "service",
         "position": {"x": 640, "y": 230},
         "data": {"label": "Audit Service", "entityType": "service",
                  "description": "Middleware-based operation logging",
                  "entityId": eids["n7"]}},
        {"id": "n8", "type": "component",
         "position": {"x": 60, "y": 430},
         "data": {"label": "Model Renderer", "entityType": "component",
                  "description": "SVG thumbnail generation",
                  "entityId": eids["n8"]}},
        {"id": "n3", "type": "database",
         "position": {"x": 350, "y": 430},
         "data": {"label": "Database", "entityType": "database",
                  "description": "SQLite + WAL + FTS5 + migrations",
                  "entityId": eids["n3"]}},
        {"id": "n13", "type": "queue",
         "position": {"x": 640, "y": 430},
         "data": {"label": "Event Bus", "entityType": "queue",
                  "description": "Internal event dispatch",
                  "entityId": eids["n13"]}},
    ]
    edges = [
        {"id": "e2-12", "source": "n2", "target": "n12", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Version entities",
                  "relationshipId": rids["r10"]}},
        {"id": "e2-6", "source": "n2", "target": "n6", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Query search",
                  "relationshipId": rids["r11"]}},
        {"id": "e2-7", "source": "n2", "target": "n7", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Log operations",
                  "relationshipId": rids["r12"]}},
        {"id": "e12-3", "source": "n12", "target": "n3", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Read/write versions",
                  "relationshipId": rids["r13"]}},
        {"id": "e6-3", "source": "n6", "target": "n3", "type": "depends_on",
         "data": {"relationshipType": "depends_on", "label": "FTS5 queries",
                  "relationshipId": rids["r14"]}},
        {"id": "e7-13", "source": "n7", "target": "n13", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Emit events",
                  "relationshipId": rids["r15"]}},
        {"id": "e13-3", "source": "n13", "target": "n3", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Persist audit logs",
                  "relationshipId": rids["r16"]}},
        {"id": "e8-3", "source": "n8", "target": "n3", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Read model data",
                  "relationshipId": rids["r17"]}},
    ]
    return {"nodes": nodes, "edges": edges}


# ── Model 4: Enterprise View (archimate) ────────────────────────────────────

def _build_enterprise_model(
    eids: dict[str, str], rids: dict[str, str],
) -> dict[str, object]:
    """ArchiMate-style enterprise view of Iris."""
    nodes = [
        {"id": "n10", "type": "actor",
         "position": {"x": 60, "y": 50},
         "data": {"label": "User", "entityType": "actor",
                  "description": "End user", "entityId": eids["n10"]}},
        {"id": "n11", "type": "actor",
         "position": {"x": 350, "y": 50},
         "data": {"label": "Admin", "entityType": "actor",
                  "description": "System administrator", "entityId": eids["n11"]}},
        {"id": "n1", "type": "component",
         "position": {"x": 60, "y": 230},
         "data": {"label": "Frontend", "entityType": "component",
                  "description": "SvelteKit web application",
                  "entityId": eids["n1"]}},
        {"id": "n15", "type": "package",
         "position": {"x": 350, "y": 230},
         "data": {"label": "Middleware Stack", "entityType": "package",
                  "description": "CORS, rate limits, security headers, audit",
                  "entityId": eids["n15"]}},
        {"id": "n2", "type": "component",
         "position": {"x": 60, "y": 430},
         "data": {"label": "Backend", "entityType": "component",
                  "description": "FastAPI application",
                  "entityId": eids["n2"]}},
        {"id": "n4", "type": "service",
         "position": {"x": 350, "y": 430},
         "data": {"label": "Auth Service", "entityType": "service",
                  "description": "Authentication and authorization",
                  "entityId": eids["n4"]}},
        {"id": "n3", "type": "database",
         "position": {"x": 60, "y": 620},
         "data": {"label": "Database", "entityType": "database",
                  "description": "SQLite persistent storage",
                  "entityId": eids["n3"]}},
        {"id": "n6", "type": "service",
         "position": {"x": 350, "y": 620},
         "data": {"label": "Search Service", "entityType": "service",
                  "description": "Full-text search",
                  "entityId": eids["n6"]}},
    ]
    edges = [
        {"id": "ea1", "source": "n10", "target": "n1", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Browses models",
                  "relationshipId": rids["r0"]}},
        {"id": "ea2", "source": "n11", "target": "n1", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Manages system",
                  "relationshipId": rids["r1"]}},
        {"id": "ea3", "source": "n11", "target": "n15", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Configures",
                  "relationshipId": rids["r18"]}},
        {"id": "ea4", "source": "n1", "target": "n2", "type": "depends_on",
         "data": {"relationshipType": "depends_on", "label": "REST calls",
                  "relationshipId": rids["r6"]}},
        {"id": "ea5", "source": "n15", "target": "n2", "type": "contains",
         "data": {"relationshipType": "contains", "label": "Wraps",
                  "relationshipId": rids["r19"]}},
        {"id": "ea6", "source": "n2", "target": "n4", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Authenticates",
                  "relationshipId": rids["r7"]}},
        {"id": "ea7", "source": "n2", "target": "n3", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Persists data",
                  "relationshipId": rids["r8"]}},
        {"id": "ea8", "source": "n6", "target": "n3", "type": "depends_on",
         "data": {"relationshipType": "depends_on", "label": "Indexes",
                  "relationshipId": rids["r14"]}},
        {"id": "ea9", "source": "n4", "target": "n3", "type": "uses",
         "data": {"relationshipType": "uses", "label": "User credentials",
                  "relationshipId": rids["r9"]}},
    ]
    return {"nodes": nodes, "edges": edges}


# ── Model definitions ───────────────────────────────────────────────────────

_MODELS = [
    {
        "index": 0,
        "model_type": "component",
        "name": "Iris Architecture",
        "description": (
            "Component model showing the internal architecture of Iris: "
            "Frontend, Backend, Database, Auth, Canvas Engine, and Export "
            "with their interactions."
        ),
        "builder": _build_architecture_model,
        "tags": _MODEL_TAGS,
    },
    {
        "index": 1,
        "model_type": "sequence",
        "name": "API Request Flow",
        "description": (
            "Sequence diagram showing a typical user login followed by "
            "fetching the model gallery, illustrating the interaction "
            "between Browser, Frontend, Backend, Auth, and Database."
        ),
        "builder": _build_sequence_model,
        "tags": _MODEL_TAGS,
    },
    {
        "index": 2,
        "model_type": "component",
        "name": "Data Layer",
        "description": (
            "Component model detailing the data layer: version control, "
            "search service, audit service, model renderer, event bus, "
            "and their database interactions."
        ),
        "builder": _build_data_layer_model,
        "tags": _MODEL_TAGS,
    },
    {
        "index": 3,
        "model_type": "archimate",
        "name": "Iris Enterprise View",
        "description": (
            "Enterprise architecture view showing actors (User, Admin), "
            "application components, middleware, authentication, and data "
            "services across technology layers."
        ),
        "builder": _build_enterprise_model,
        "tags": _MODEL_TAGS,
    },
]


async def _ensure_system_user(db: aiosqlite.Connection) -> None:
    """Create a deactivated system user for seed data ownership."""
    await db.execute(
        "INSERT OR IGNORE INTO users (id, username, password_hash, role, is_active) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            _SYSTEM_USER_ID,
            "system",
            "!no-login-seed-user",
            "viewer",
            0,
        ),
    )


async def seed_example_models(db: aiosqlite.Connection) -> None:
    """Seed example entities and models demonstrating Iris architecture.

    Idempotent: skips if any entity_tags with tag='example' already exist.
    Also skips if no active users exist yet (initial setup not completed).
    """
    # --- Skip if initial setup not yet completed ------------------------------
    cursor = await db.execute(
        "SELECT COUNT(*) FROM users WHERE is_active = 1"
    )
    row = await cursor.fetchone()
    if not row or row[0] == 0:
        return

    # --- Idempotency check ---------------------------------------------------
    cursor = await db.execute(
        "SELECT COUNT(*) FROM entity_tags WHERE tag = 'example'"
    )
    row = await cursor.fetchone()
    if row and row[0] > 0:
        return

    # --- Ensure system user exists for FK compliance --------------------------
    await _ensure_system_user(db)

    now = datetime.now(tz=UTC).isoformat()

    # --- Create entities ------------------------------------------------------
    entity_ids: dict[str, str] = {}

    for idx, (node_id, entity_type, name, description) in enumerate(_ENTITIES):
        entity_id = _gen_id("entity", idx)
        entity_ids[node_id] = entity_id

        await db.execute(
            "INSERT INTO entities (id, entity_type, current_version, "
            "created_at, created_by, updated_at) VALUES (?, ?, 1, ?, ?, ?)",
            (entity_id, entity_type, now, _SYSTEM_USER_ID, now),
        )
        await db.execute(
            "INSERT INTO entity_versions (entity_id, version, name, description, "
            "data, change_type, created_at, created_by) "
            "VALUES (?, 1, ?, ?, ?, 'create', ?, ?)",
            (entity_id, name, description, json.dumps({}), now, _SYSTEM_USER_ID),
        )

        for tag in _ENTITY_TAGS:
            await db.execute(
                "INSERT INTO entity_tags (entity_id, tag, created_at, created_by) "
                "VALUES (?, ?, ?, ?)",
                (entity_id, tag, now, _SYSTEM_USER_ID),
            )

    # --- Create relationships -------------------------------------------------
    rel_ids: dict[str, str] = {}

    for idx, (ri, src, tgt, rel_type, label, desc) in enumerate(_RELATIONSHIPS):
        rel_id = _gen_id("rel", ri)
        rel_ids[f"r{ri}"] = rel_id

        await db.execute(
            "INSERT INTO relationships (id, source_entity_id, target_entity_id, "
            "relationship_type, current_version, created_at, created_by, updated_at) "
            "VALUES (?, ?, ?, ?, 1, ?, ?, ?)",
            (rel_id, entity_ids[src], entity_ids[tgt], rel_type,
             now, _SYSTEM_USER_ID, now),
        )
        await db.execute(
            "INSERT INTO relationship_versions (relationship_id, version, label, "
            "description, data, change_type, created_at, created_by) "
            "VALUES (?, 1, ?, ?, ?, 'create', ?, ?)",
            (rel_id, label, desc, json.dumps({}), now, _SYSTEM_USER_ID),
        )

    # --- Create models --------------------------------------------------------
    for model_def in _MODELS:
        model_id = _gen_id("model", model_def["index"])
        model_data = model_def["builder"](entity_ids, rel_ids)
        model_data_json = json.dumps(model_data)

        await db.execute(
            "INSERT INTO models (id, model_type, current_version, "
            "created_at, created_by, updated_at) VALUES (?, ?, 1, ?, ?, ?)",
            (model_id, model_def["model_type"], now, _SYSTEM_USER_ID, now),
        )
        await db.execute(
            "INSERT INTO model_versions (model_id, version, name, description, "
            "data, change_type, created_at, created_by) "
            "VALUES (?, 1, ?, ?, ?, 'create', ?, ?)",
            (
                model_id,
                model_def["name"],
                model_def["description"],
                model_data_json,
                now,
                _SYSTEM_USER_ID,
            ),
        )

        for tag in model_def["tags"]:
            await db.execute(
                "INSERT INTO model_tags (model_id, tag, created_at, created_by) "
                "VALUES (?, ?, ?, ?)",
                (model_id, tag, now, _SYSTEM_USER_ID),
            )

    await db.commit()
