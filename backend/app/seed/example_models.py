"""Idempotent seed: example diagrams demonstrating Iris's own architecture.

Creates elements representing the Iris system and six diagrams:
  1. Iris Architecture (component) — core component overview
  2. API Request Flow (sequence) — login and data fetch sequence
  3. Data Layer (component) — database, versioning, and search internals
  4. Iris Enterprise View (archimate) — high-level enterprise architecture
  5. Iris System Overview (component) — diagram-in-diagram view referencing all above
  6. Data Model (component) — complete database schema with all tables and FKs

All elements are tagged with 'iris' and 'example'; diagrams are tagged with
'iris', 'example', and 'template'.

Idempotency: the seed checks for existing element_tags with tag='example'
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
_DEFAULT_SET_ID = "00000000-0000-0000-0000-000000000001"

# ── Element definitions ─────────────────────────────────────────────────────
# (node_id, element_type, name, description)
_ENTITIES = [
    # Core components (used in Architecture diagram)
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
    ("n8", "component", "Diagram Renderer",
     "Thumbnail generator producing SVG previews of canvas diagrams for gallery display"),
    ("n9", "interface", "REST API",
     "JSON REST interface at /api/* with OpenAPI documentation and JWT bearer auth"),
    ("n10", "actor", "User",
     "Human user interacting with the system through a web browser"),
    ("n11", "actor", "Admin",
     "Administrator with elevated privileges for user management and system settings"),
    ("n12", "component", "Version Control",
     "Element and diagram versioning with optimistic concurrency via ETags"),
    ("n13", "queue", "Event Bus",
     "Internal event dispatch for audit logging and thumbnail regeneration"),
    ("n14", "component", "Export Engine",
     "Diagram export to SVG, PNG, and PDF formats using html-to-image"),
    ("n15", "package", "Middleware Stack",
     "CORS, rate limiting, security headers, and audit middleware layers"),
]

_ELEMENT_DESCRIPTIONS = {node_id: desc for node_id, _, _, desc in _ENTITIES}

_ELEMENT_TAGS = ["iris", "example"]
_DIAGRAM_TAGS = ["iris", "example", "template"]

# Relationships between elements: (index, source_node, target_node, rel_type, label, description)
# These create actual relationship records in the DB so element detail pages show connections.
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
    (10, "n2", "n12", "uses", "Version elements",
     "Backend uses Version Control for element/diagram versioning"),
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
    (17, "n8", "n3", "uses", "Read diagram data",
     "Diagram Renderer reads diagram canvas data from Database"),
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
    eids: dict[str, str], rids: dict[str, str], **_kw: object,
) -> dict[str, object]:
    """Core component overview with Frontend, Backend, DB, Auth, Canvas."""
    nodes = [
        {"id": "n10", "type": "actor",
         "position": {"x": 400, "y": 0},
         "data": {"label": "User", "entityType": "actor",
                  "description": _ELEMENT_DESCRIPTIONS["n10"],
                  "entityId": eids["n10"]}},
        {"id": "n1", "type": "component",
         "position": {"x": 350, "y": 250},
         "data": {"label": "Frontend", "entityType": "component",
                  "description": _ELEMENT_DESCRIPTIONS["n1"],
                  "entityId": eids["n1"]}},
        {"id": "n9", "type": "interface",
         "position": {"x": 370, "y": 500},
         "data": {"label": "REST API", "entityType": "interface",
                  "description": _ELEMENT_DESCRIPTIONS["n9"],
                  "entityId": eids["n9"]}},
        {"id": "n2", "type": "component",
         "position": {"x": 350, "y": 750},
         "data": {"label": "Backend", "entityType": "component",
                  "description": _ELEMENT_DESCRIPTIONS["n2"],
                  "entityId": eids["n2"]}},
        {"id": "n4", "type": "service",
         "position": {"x": 60, "y": 750},
         "data": {"label": "Auth Service", "entityType": "service",
                  "description": _ELEMENT_DESCRIPTIONS["n4"],
                  "entityId": eids["n4"]}},
        {"id": "n5", "type": "component",
         "position": {"x": 650, "y": 250},
         "data": {"label": "Canvas Engine", "entityType": "component",
                  "description": _ELEMENT_DESCRIPTIONS["n5"],
                  "entityId": eids["n5"]}},
        {"id": "n14", "type": "component",
         "position": {"x": 650, "y": 500},
         "data": {"label": "Export Engine", "entityType": "component",
                  "description": _ELEMENT_DESCRIPTIONS["n14"],
                  "entityId": eids["n14"]}},
        {"id": "n3", "type": "database",
         "position": {"x": 370, "y": 1000},
         "data": {"label": "Database", "entityType": "database",
                  "description": _ELEMENT_DESCRIPTIONS["n3"],
                  "entityId": eids["n3"]}},
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
    eids: dict[str, str], rids: dict[str, str], **_kw: object,
) -> dict[str, object]:
    """Sequence diagram: user login then fetch diagram data."""
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
         "label": "Navigate to /diagrams", "type": "sync", "order": 0},
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
         "label": "GET /api/diagrams (Bearer token)", "type": "sync", "order": 7},
        {"id": "m9", "from": "p3", "to": "p5",
         "label": "SELECT diagrams with versions", "type": "sync", "order": 8},
        {"id": "m10", "from": "p5", "to": "p3",
         "label": "Diagram list", "type": "reply", "order": 9},
        {"id": "m11", "from": "p3", "to": "p2",
         "label": "200 [{diagram}, ...]", "type": "reply", "order": 10},
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
    eids: dict[str, str], rids: dict[str, str], **_kw: object,
) -> dict[str, object]:
    """Component diagram showing database, versioning, search, and audit."""
    nodes = [
        {"id": "n2", "type": "component",
         "position": {"x": 350, "y": 50},
         "data": {"label": "Backend", "entityType": "component",
                  "description": _ELEMENT_DESCRIPTIONS["n2"],
                  "entityId": eids["n2"]}},
        {"id": "n12", "type": "component",
         "position": {"x": 60, "y": 300},
         "data": {"label": "Version Control", "entityType": "component",
                  "description": _ELEMENT_DESCRIPTIONS["n12"],
                  "entityId": eids["n12"]}},
        {"id": "n6", "type": "service",
         "position": {"x": 350, "y": 300},
         "data": {"label": "Search Service", "entityType": "service",
                  "description": _ELEMENT_DESCRIPTIONS["n6"],
                  "entityId": eids["n6"]}},
        {"id": "n7", "type": "service",
         "position": {"x": 640, "y": 300},
         "data": {"label": "Audit Service", "entityType": "service",
                  "description": _ELEMENT_DESCRIPTIONS["n7"],
                  "entityId": eids["n7"]}},
        {"id": "n8", "type": "component",
         "position": {"x": 60, "y": 550},
         "data": {"label": "Diagram Renderer", "entityType": "component",
                  "description": _ELEMENT_DESCRIPTIONS["n8"],
                  "entityId": eids["n8"]}},
        {"id": "n3", "type": "database",
         "position": {"x": 350, "y": 550},
         "data": {"label": "Database", "entityType": "database",
                  "description": _ELEMENT_DESCRIPTIONS["n3"],
                  "entityId": eids["n3"]}},
        {"id": "n13", "type": "queue",
         "position": {"x": 640, "y": 550},
         "data": {"label": "Event Bus", "entityType": "queue",
                  "description": _ELEMENT_DESCRIPTIONS["n13"],
                  "entityId": eids["n13"]}},
    ]
    edges = [
        {"id": "e2-12", "source": "n2", "target": "n12", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Version elements",
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
         "data": {"relationshipType": "uses", "label": "Read diagram data",
                  "relationshipId": rids["r17"]}},
    ]
    return {"nodes": nodes, "edges": edges}


# ── Model 4: Enterprise View (archimate) ────────────────────────────────────

def _build_enterprise_model(
    eids: dict[str, str], rids: dict[str, str], **_kw: object,
) -> dict[str, object]:
    """ArchiMate-style enterprise view of Iris."""
    nodes = [
        {"id": "n10", "type": "business_actor",
         "position": {"x": 60, "y": 50},
         "data": {"label": "User", "entityType": "actor",
                  "layer": "business", "archimateType": "Business Actor",
                  "description": _ELEMENT_DESCRIPTIONS["n10"],
                  "entityId": eids["n10"]}},
        {"id": "n11", "type": "business_actor",
         "position": {"x": 400, "y": 50},
         "data": {"label": "Admin", "entityType": "actor",
                  "layer": "business", "archimateType": "Business Actor",
                  "description": _ELEMENT_DESCRIPTIONS["n11"],
                  "entityId": eids["n11"]}},
        {"id": "n1", "type": "application_component",
         "position": {"x": 60, "y": 300},
         "data": {"label": "Frontend", "entityType": "component",
                  "layer": "application", "archimateType": "Application Component",
                  "description": _ELEMENT_DESCRIPTIONS["n1"],
                  "entityId": eids["n1"]}},
        {"id": "n15", "type": "technology_node",
         "position": {"x": 400, "y": 300},
         "data": {"label": "Middleware Stack", "entityType": "package",
                  "layer": "technology", "archimateType": "Technology Node",
                  "description": _ELEMENT_DESCRIPTIONS["n15"],
                  "entityId": eids["n15"]}},
        {"id": "n2", "type": "application_component",
         "position": {"x": 60, "y": 550},
         "data": {"label": "Backend", "entityType": "component",
                  "layer": "application", "archimateType": "Application Component",
                  "description": _ELEMENT_DESCRIPTIONS["n2"],
                  "entityId": eids["n2"]}},
        {"id": "n4", "type": "application_service",
         "position": {"x": 400, "y": 550},
         "data": {"label": "Auth Service", "entityType": "service",
                  "layer": "application", "archimateType": "Application Service",
                  "description": _ELEMENT_DESCRIPTIONS["n4"],
                  "entityId": eids["n4"]}},
        {"id": "n3", "type": "technology_node",
         "position": {"x": 60, "y": 800},
         "data": {"label": "Database", "entityType": "database",
                  "layer": "technology", "archimateType": "Technology Node",
                  "description": _ELEMENT_DESCRIPTIONS["n3"],
                  "entityId": eids["n3"]}},
        {"id": "n6", "type": "technology_service",
         "position": {"x": 400, "y": 800},
         "data": {"label": "Search Service", "entityType": "service",
                  "layer": "technology", "archimateType": "Technology Service",
                  "description": _ELEMENT_DESCRIPTIONS["n6"],
                  "entityId": eids["n6"]}},
    ]
    edges = [
        {"id": "ea1", "source": "n10", "target": "n1", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Browses diagrams",
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


# ── Model 5: System Overview (diagram-in-diagram) ────────────────────────────────

def _build_system_overview_model(
    eids: dict[str, str],
    rids: dict[str, str],
    mids: dict[int, str] | None = None,
) -> dict[str, object]:
    """Top-level overview with modelref nodes for all sub-diagrams plus key elements."""
    mids = mids or {}
    nodes = [
        # Model references — the sub-models
        {"id": "mr0", "type": "modelref",
         "position": {"x": 60, "y": 50},
         "data": {"label": "Iris Architecture", "entityType": "component",
                  "description": "Core component overview: Frontend, Backend, DB, Auth, Canvas",
                  "linkedModelId": mids.get(0, "")}},
        {"id": "mr1", "type": "modelref",
         "position": {"x": 350, "y": 50},
         "data": {"label": "API Request Flow", "entityType": "component",
                  "description": "Login and diagram fetch sequence diagram",
                  "linkedModelId": mids.get(1, "")}},
        {"id": "mr2", "type": "modelref",
         "position": {"x": 60, "y": 300},
         "data": {"label": "Data Layer", "entityType": "component",
                  "description": "Versioning, search, audit, and event bus internals",
                  "linkedModelId": mids.get(2, "")}},
        {"id": "mr3", "type": "modelref",
         "position": {"x": 350, "y": 300},
         "data": {"label": "Iris Enterprise View", "entityType": "component",
                  "description": "ArchiMate enterprise architecture view",
                  "linkedModelId": mids.get(3, "")}},
        {"id": "mr5", "type": "modelref",
         "position": {"x": 60, "y": 550},
         "data": {"label": "Data Model", "entityType": "database",
                  "description": "Complete database schema with all 20 tables and FK relationships",
                  "linkedModelId": mids.get(5, "")}},
        # Key entities providing context
        {"id": "n10", "type": "actor",
         "position": {"x": 640, "y": 50},
         "data": {"label": "User", "entityType": "actor",
                  "description": _ELEMENT_DESCRIPTIONS["n10"],
                  "entityId": eids["n10"]}},
        {"id": "n11", "type": "actor",
         "position": {"x": 640, "y": 300},
         "data": {"label": "Admin", "entityType": "actor",
                  "description": _ELEMENT_DESCRIPTIONS["n11"],
                  "entityId": eids["n11"]}},
    ]
    edges = [
        # User interacts with Architecture and API flow
        {"id": "eo1", "source": "n10", "target": "mr0", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Uses system"}},
        {"id": "eo2", "source": "n10", "target": "mr1", "type": "uses",
         "data": {"relationshipType": "uses", "label": "API interactions"}},
        # Admin manages enterprise view and data layer
        {"id": "eo3", "source": "n11", "target": "mr3", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Manages"}},
        {"id": "eo4", "source": "n11", "target": "mr2", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Configures"}},
        # Architecture depends on Data Layer
        {"id": "eo5", "source": "mr0", "target": "mr2", "type": "depends_on",
         "data": {"relationshipType": "depends_on", "label": "Persistence layer"}},
        # Enterprise view composes Architecture and Data Layer
        {"id": "eo6", "source": "mr3", "target": "mr0", "type": "composes",
         "data": {"relationshipType": "composes", "label": "Includes"}},
        {"id": "eo7", "source": "mr3", "target": "mr2", "type": "composes",
         "data": {"relationshipType": "composes", "label": "Includes"}},
        # Data Model details the Data Layer schema
        {"id": "eo8", "source": "mr5", "target": "mr2", "type": "depends_on",
         "data": {"relationshipType": "depends_on", "label": "Schema for"}},
    ]
    return {"nodes": nodes, "edges": edges}


# ── Model 6: Data Model (component) ──────────────────────────────────────────

def _build_data_model(
    eids: dict[str, str],
    rids: dict[str, str],
    mids: dict[int, str] | None = None,
) -> dict[str, object]:
    """Complete database schema showing all tables and foreign key relationships."""
    mids = mids or {}
    nodes = [
        # ── Row 1: Auth & Access Control (y=50) ──
        {"id": "t_roles", "type": "database",
         "position": {"x": 60, "y": 50},
         "data": {"label": "roles", "entityType": "database",
                  "description": "id (PK), name, description, created_at "
                  "— 4 seeded roles: admin, architect, reviewer, viewer"}},
        {"id": "t_role_perms", "type": "database",
         "position": {"x": 350, "y": 50},
         "data": {"label": "role_permissions", "entityType": "database",
                  "description": "role_id (FK\u2192roles), permission "
                  "— composite PK, 63 seeded permission mappings"}},
        {"id": "t_users", "type": "database",
         "position": {"x": 640, "y": 50},
         "data": {"label": "users", "entityType": "database",
                  "description": "id (PK), username (UNIQUE), password_hash, "
                  "role (FK\u2192roles), is_active, failed_login_count, "
                  "locked_until, last_login_at, password_changed_at"}},
        # ── Row 2: Auth Support (y=300) ──
        {"id": "t_pwd_hist", "type": "database",
         "position": {"x": 350, "y": 300},
         "data": {"label": "password_history", "entityType": "database",
                  "description": "user_id (FK\u2192users), password_hash, "
                  "changed_at — composite PK, prevents password reuse"}},
        {"id": "t_refresh", "type": "database",
         "position": {"x": 640, "y": 300},
         "data": {"label": "refresh_tokens", "entityType": "database",
                  "description": "id (PK), user_id (FK\u2192users), family_id, "
                  "expires_at, used_at, revoked — token rotation with family tracking"}},
        # ── Row 3: Core Domain – Elements (y=550) ──
        {"id": "t_elements", "type": "database",
         "position": {"x": 60, "y": 550},
         "data": {"label": "elements", "entityType": "database",
                  "description": "id (PK), element_type, current_version, "
                  "created_by (FK\u2192users), is_deleted — soft delete, "
                  "optimistic concurrency"}},
        {"id": "t_element_ver", "type": "database",
         "position": {"x": 350, "y": 550},
         "data": {"label": "element_versions", "entityType": "database",
                  "description": "element_id (FK\u2192entities), version "
                  "— composite PK, name, description, data (JSON), "
                  "change_type, rollback_to"}},
        {"id": "t_element_tags", "type": "database",
         "position": {"x": 640, "y": 550},
         "data": {"label": "element_tags", "entityType": "database",
                  "description": "element_id (FK\u2192entities), tag "
                  "— composite PK, created_at, created_by"}},
        # ── Row 4: Core Domain – Relationships (y=800) ──
        {"id": "t_rels", "type": "database",
         "position": {"x": 60, "y": 800},
         "data": {"label": "relationships", "entityType": "database",
                  "description": "id (PK), source_element_id (FK\u2192entities), "
                  "target_element_id (FK\u2192entities), relationship_type, "
                  "current_version, is_deleted"}},
        {"id": "t_rel_ver", "type": "database",
         "position": {"x": 350, "y": 800},
         "data": {"label": "relationship_versions", "entityType": "database",
                  "description": "relationship_id (FK\u2192relationships), version "
                  "— composite PK, label, description, data (JSON), change_type"}},
        # ── Row 5: Core Domain – Diagrams (y=1050) ──
        {"id": "t_diagrams", "type": "database",
         "position": {"x": 60, "y": 1050},
         "data": {"label": "diagrams", "entityType": "database",
                  "description": "id (PK), diagram_type, current_version, "
                  "created_by (FK\u2192users), is_deleted — component, "
                  "sequence, archimate, roadmap"}},
        {"id": "t_diagram_ver", "type": "database",
         "position": {"x": 350, "y": 1050},
         "data": {"label": "diagram_versions", "entityType": "database",
                  "description": "diagram_id (FK\u2192models), version "
                  "— composite PK, name, description, data (JSON canvas), "
                  "change_type"}},
        {"id": "t_diagram_tags", "type": "database",
         "position": {"x": 640, "y": 1050},
         "data": {"label": "diagram_tags", "entityType": "database",
                  "description": "diagram_id (FK\u2192models), tag "
                  "— composite PK, created_at, created_by"}},
        # ── Row 6: Features (y=1300) ──
        {"id": "t_comments", "type": "database",
         "position": {"x": 60, "y": 1300},
         "data": {"label": "comments", "entityType": "database",
                  "description": "id (PK), target_type (entity|model), "
                  "target_id, user_id (FK\u2192users), content, is_deleted "
                  "— soft delete"}},
        {"id": "t_bookmarks", "type": "database",
         "position": {"x": 350, "y": 1300},
         "data": {"label": "bookmarks", "entityType": "database",
                  "description": "user_id (FK\u2192users), diagram_id (FK\u2192diagrams) "
                  "— composite PK, per-user diagram bookmarks"}},
        {"id": "t_diagram_thumbs", "type": "database",
         "position": {"x": 640, "y": 1300},
         "data": {"label": "diagram_thumbnails", "entityType": "database",
                  "description": "diagram_id (FK\u2192models), theme — composite PK, "
                  "thumbnail (BLOB PNG), 3 theme variants per diagram"}},
        # ── Row 7: Search & Config (y=1550) ──
        {"id": "t_elem_fts", "type": "service",
         "position": {"x": 60, "y": 1550},
         "data": {"label": "elements_fts", "entityType": "service",
                  "description": "FTS5 virtual table — entity_id, name, "
                  "element_type, description, porter unicode61 tokenizer"}},
        {"id": "t_diag_fts", "type": "service",
         "position": {"x": 350, "y": 1550},
         "data": {"label": "diagrams_fts", "entityType": "service",
                  "description": "FTS5 virtual table — diagram_id, name, "
                  "diagram_type, description, porter unicode61 tokenizer"}},
        {"id": "t_settings", "type": "database",
         "position": {"x": 640, "y": 1550},
         "data": {"label": "settings", "entityType": "database",
                  "description": "key (PK), value, updated_at, updated_by "
                  "— application configuration key-value store"}},
        # ── Row 8: Audit (y=1800) ──
        {"id": "t_audit", "type": "package",
         "position": {"x": 350, "y": 1800},
         "data": {"label": "audit_log", "entityType": "package",
                  "description": "Separate DB (iris_audit.db) — id (PK), "
                  "timestamp, user_id, username, action, target_type, "
                  "target_id, detail, previous_hash, entry_hash "
                  "— SHA-256 hash chain"}},
        # ── Model reference to Data Layer ──
        {"id": "mr_data_layer", "type": "modelref",
         "position": {"x": 930, "y": 50},
         "data": {"label": "Data Layer", "entityType": "component",
                  "description": "Component model showing database services, "
                  "versioning, search, and audit",
                  "linkedModelId": mids.get(2, "")}},
    ]
    edges = [
        # Auth
        {"id": "fk1", "source": "t_role_perms", "target": "t_roles",
         "type": "depends_on",
         "data": {"relationshipType": "depends_on",
                  "label": "role_id \u2192 roles.id"}},
        {"id": "fk2", "source": "t_users", "target": "t_roles",
         "type": "depends_on",
         "data": {"relationshipType": "depends_on",
                  "label": "role \u2192 roles.id"}},
        {"id": "fk3", "source": "t_pwd_hist", "target": "t_users",
         "type": "depends_on",
         "data": {"relationshipType": "depends_on",
                  "label": "user_id \u2192 users.id"}},
        {"id": "fk4", "source": "t_refresh", "target": "t_users",
         "type": "depends_on",
         "data": {"relationshipType": "depends_on",
                  "label": "user_id \u2192 users.id"}},
        # Entities
        {"id": "fk5", "source": "t_entities", "target": "t_users",
         "type": "depends_on",
         "data": {"relationshipType": "depends_on",
                  "label": "created_by \u2192 users.id"}},
        {"id": "fk6", "source": "t_element_ver", "target": "t_elements",
         "type": "depends_on",
         "data": {"relationshipType": "depends_on",
                  "label": "element_id \u2192 entities.id"}},
        {"id": "fk7", "source": "t_element_tags", "target": "t_elements",
         "type": "depends_on",
         "data": {"relationshipType": "depends_on",
                  "label": "element_id \u2192 entities.id"}},
        # Relationships
        {"id": "fk8", "source": "t_rels", "target": "t_elements",
         "type": "depends_on",
         "data": {"relationshipType": "depends_on",
                  "label": "source_element_id \u2192 entities.id"}},
        {"id": "fk9", "source": "t_rels", "target": "t_elements",
         "type": "depends_on",
         "data": {"relationshipType": "depends_on",
                  "label": "target_element_id \u2192 entities.id"}},
        {"id": "fk10", "source": "t_rel_ver", "target": "t_rels",
         "type": "depends_on",
         "data": {"relationshipType": "depends_on",
                  "label": "relationship_id \u2192 relationships.id"}},
        # Models
        {"id": "fk11", "source": "t_diagrams", "target": "t_users",
         "type": "depends_on",
         "data": {"relationshipType": "depends_on",
                  "label": "created_by \u2192 users.id"}},
        {"id": "fk12", "source": "t_diagram_ver", "target": "t_diagrams",
         "type": "depends_on",
         "data": {"relationshipType": "depends_on",
                  "label": "diagram_id \u2192 models.id"}},
        {"id": "fk13", "source": "t_diagram_tags", "target": "t_diagrams",
         "type": "depends_on",
         "data": {"relationshipType": "depends_on",
                  "label": "diagram_id \u2192 models.id"}},
        # Features
        {"id": "fk14", "source": "t_comments", "target": "t_users",
         "type": "depends_on",
         "data": {"relationshipType": "depends_on",
                  "label": "user_id \u2192 users.id"}},
        {"id": "fk15", "source": "t_bookmarks", "target": "t_users",
         "type": "depends_on",
         "data": {"relationshipType": "depends_on",
                  "label": "user_id \u2192 users.id"}},
        {"id": "fk16", "source": "t_bookmarks", "target": "t_diagrams",
         "type": "depends_on",
         "data": {"relationshipType": "depends_on",
                  "label": "diagram_id \u2192 models.id"}},
        {"id": "fk17", "source": "t_diagram_thumbs", "target": "t_diagrams",
         "type": "depends_on",
         "data": {"relationshipType": "depends_on",
                  "label": "diagram_id \u2192 models.id"}},
        # Search indexes
        {"id": "fk18", "source": "t_elem_fts", "target": "t_elements",
         "type": "depends_on",
         "data": {"relationshipType": "depends_on",
                  "label": "indexes elements"}},
        {"id": "fk19", "source": "t_diag_fts", "target": "t_diagrams",
         "type": "depends_on",
         "data": {"relationshipType": "depends_on",
                  "label": "indexes diagrams"}},
        # Model ref links
        {"id": "ref1", "source": "mr_data_layer", "target": "t_elements",
         "type": "composes",
         "data": {"relationshipType": "composes", "label": "Manages"}},
        {"id": "ref2", "source": "mr_data_layer", "target": "t_diagrams",
         "type": "composes",
         "data": {"relationshipType": "composes", "label": "Manages"}},
    ]
    return {"nodes": nodes, "edges": edges}


# ── Diagram definitions ───────────────────────────────────────────────────────

_DIAGRAMS = [
    {
        "index": 0,
        "diagram_type": "component",
        "name": "Iris Architecture",
        "description": (
            "Component diagram showing the internal architecture of Iris: "
            "Frontend, Backend, Database, Auth, Canvas Engine, and Export "
            "with their interactions."
        ),
        "builder": _build_architecture_model,
        "tags": _DIAGRAM_TAGS,
    },
    {
        "index": 1,
        "diagram_type": "sequence",
        "name": "API Request Flow",
        "description": (
            "Sequence diagram showing a typical user login followed by "
            "fetching the diagram gallery, illustrating the interaction "
            "between Browser, Frontend, Backend, Auth, and Database."
        ),
        "builder": _build_sequence_model,
        "tags": _DIAGRAM_TAGS,
    },
    {
        "index": 2,
        "diagram_type": "component",
        "name": "Data Layer",
        "description": (
            "Component diagram detailing the data layer: version control, "
            "search service, audit service, diagram renderer, event bus, "
            "and their database interactions."
        ),
        "builder": _build_data_layer_model,
        "tags": _DIAGRAM_TAGS,
    },
    {
        "index": 3,
        "diagram_type": "archimate",
        "name": "Iris Enterprise View",
        "description": (
            "Enterprise architecture view showing actors (User, Admin), "
            "application components, middleware, authentication, and data "
            "services across technology layers."
        ),
        "builder": _build_enterprise_model,
        "tags": _DIAGRAM_TAGS,
    },
    {
        "index": 4,
        "diagram_type": "component",
        "name": "Iris System Overview",
        "description": (
            "Top-level overview diagram using diagram-in-diagram references to "
            "all Iris sub-diagrams (Architecture, API Flow, Data Layer, "
            "Enterprise View, Data Model), showing how they relate to "
            "each other and to key actors."
        ),
        "builder": _build_system_overview_model,
        "tags": _DIAGRAM_TAGS,
    },
    {
        "index": 5,
        "diagram_type": "component",
        "name": "Data Model",
        "description": (
            "Complete database schema for Iris showing all 20 tables "
            "across both databases (iris.db and iris_audit.db), their "
            "columns, primary keys, and 19 foreign key relationships. "
            "Covers auth, elements, relationships, diagrams, versioning, "
            "comments, bookmarks, thumbnails, tags, FTS5 search indexes, "
            "settings, and audit log."
        ),
        "builder": _build_data_model,
        "tags": _DIAGRAM_TAGS,
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
    """Seed example elements and diagrams demonstrating Iris architecture.

    Idempotent: skips if any element_tags with tag='example' already exist.
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
        "SELECT COUNT(*) FROM element_tags WHERE tag = 'example'"
    )
    row = await cursor.fetchone()
    if row and row[0] > 0:
        return

    # --- Ensure system user exists for FK compliance --------------------------
    await _ensure_system_user(db)

    now = datetime.now(tz=UTC).isoformat()

    # --- Create elements ------------------------------------------------------
    element_ids: dict[str, str] = {}

    for idx, (node_id, element_type, name, description) in enumerate(_ENTITIES):
        element_id = _gen_id("element", idx)
        element_ids[node_id] = element_id

        await db.execute(
            "INSERT INTO elements (id, element_type, set_id, current_version, "
            "created_at, created_by, updated_at) VALUES (?, ?, ?, 1, ?, ?, ?)",
            (element_id, element_type, _DEFAULT_SET_ID, now, _SYSTEM_USER_ID, now),
        )
        await db.execute(
            "INSERT INTO element_versions (element_id, version, name, description, "
            "data, change_type, created_at, created_by) "
            "VALUES (?, 1, ?, ?, ?, 'create', ?, ?)",
            (element_id, name, description, json.dumps({}), now, _SYSTEM_USER_ID),
        )

        for tag in _ELEMENT_TAGS:
            await db.execute(
                "INSERT INTO element_tags (element_id, tag, created_at, created_by) "
                "VALUES (?, ?, ?, ?)",
                (element_id, tag, now, _SYSTEM_USER_ID),
            )

    # --- Create relationships -------------------------------------------------
    rel_ids: dict[str, str] = {}

    for idx, (ri, src, tgt, rel_type, label, desc) in enumerate(_RELATIONSHIPS):
        rel_id = _gen_id("rel", ri)
        rel_ids[f"r{ri}"] = rel_id

        await db.execute(
            "INSERT INTO relationships (id, source_element_id, target_element_id, "
            "relationship_type, current_version, created_at, created_by, updated_at) "
            "VALUES (?, ?, ?, ?, 1, ?, ?, ?)",
            (rel_id, element_ids[src], element_ids[tgt], rel_type,
             now, _SYSTEM_USER_ID, now),
        )
        await db.execute(
            "INSERT INTO relationship_versions (relationship_id, version, label, "
            "description, data, change_type, created_at, created_by) "
            "VALUES (?, 1, ?, ?, ?, 'create', ?, ?)",
            (rel_id, label, desc, json.dumps({}), now, _SYSTEM_USER_ID),
        )

    # --- Create diagrams --------------------------------------------------------
    # Pre-compute all diagram IDs so the overview diagram can reference them
    diagram_id_map: dict[int, str] = {}
    for model_def in _DIAGRAMS:
        diagram_id_map[model_def["index"]] = _gen_id("diagram", model_def["index"])

    for model_def in _DIAGRAMS:
        diagram_id = diagram_id_map[model_def["index"]]
        diagram_data = model_def["builder"](element_ids, rel_ids, mids=diagram_id_map)
        diagram_data_json = json.dumps(diagram_data)

        await db.execute(
            "INSERT INTO diagrams (id, diagram_type, set_id, current_version, "
            "created_at, created_by, updated_at) VALUES (?, ?, ?, 1, ?, ?, ?)",
            (diagram_id, model_def["diagram_type"], _DEFAULT_SET_ID, now, _SYSTEM_USER_ID, now),
        )
        await db.execute(
            "INSERT INTO diagram_versions (diagram_id, version, name, description, "
            "data, change_type, created_at, created_by) "
            "VALUES (?, 1, ?, ?, ?, 'create', ?, ?)",
            (
                diagram_id,
                model_def["name"],
                model_def["description"],
                diagram_data_json,
                now,
                _SYSTEM_USER_ID,
            ),
        )

        for tag in model_def["tags"]:
            await db.execute(
                "INSERT INTO diagram_tags (diagram_id, tag, created_at, created_by) "
                "VALUES (?, ?, ?, ?)",
                (diagram_id, tag, now, _SYSTEM_USER_ID),
            )

    await db.commit()
