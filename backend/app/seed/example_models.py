"""Idempotent seed: example diagrams covering all 31 diagram-type/notation permutations.

Creates elements representing the Iris system and 32 diagrams organised
into a 5-package hierarchy by notation:

  Iris (root package)
  ├── Simple Notation   — 10 diagrams
  ├── UML Notation      — 8 diagrams
  ├── ArchiMate Notation — 7 diagrams
  ├── C4 Notation       — 6 diagrams
  └── Iris System Overview (component — modelrefs to key diagrams)

All elements are tagged with 'iris' and 'example'; diagrams are tagged with
'iris', 'example', and 'template'.

Idempotency:
  - If _gen_id("pkg", 4) exists → already v3, skip
  - If _gen_id("pkg", 0) exists but no pkg-4 → v2, clear + reseed v3
  - If element_tags with tag='example' exist but no root package → v1, clear + reseed
  - Otherwise → fresh seed
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

_ELEMENT_TAGS = ["iris", "example"]
_DIAGRAM_TAGS = ["iris", "example", "template"]


def _gen_id(prefix: str, index: int) -> str:
    """Generate a deterministic UUID v5 ID for seed data."""
    namespace = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    return str(uuid.uuid5(namespace, f"{prefix}-{index}"))


def _grid_nodes(
    node_defs: list[dict],
    cols: int = 3,
    x_gap: int = 300,
    y_gap: int = 250,
    x_start: int = 60,
    y_start: int = 50,
) -> list[dict]:
    """Generate positioned nodes in a grid layout."""
    nodes = []
    for i, nd in enumerate(node_defs):
        col = i % cols
        row = i // cols
        nodes.append({
            "id": nd["id"],
            "type": nd["type"],
            "position": {"x": x_start + col * x_gap, "y": y_start + row * y_gap},
            "data": nd["data"],
        })
    return nodes


# ── Element definitions ─────────────────────────────────────────────────────
# (node_id, element_type, name, description, notation)

_ENTITIES: list[tuple[str, str, str, str, str]] = [
    # ── Simple notation (15 elements, indices 0–14) ──────────────────────────
    ("n1", "component", "Frontend",
     "SvelteKit + Svelte 5 runes application with @xyflow/svelte canvas", "simple"),
    ("n2", "component", "Backend",
     "FastAPI REST API with JWT authentication and RBAC", "simple"),
    ("n3", "database", "Database",
     "SQLite with WAL mode, FTS5 search, and versioned schema migrations", "simple"),
    ("n4", "service", "Auth Service",
     "Argon2id password hashing, JWT HS256 tokens, refresh rotation", "simple"),
    ("n5", "component", "Canvas Engine",
     "@xyflow/svelte interactive graph editor with undo/redo and multiple view modes", "simple"),
    ("n6", "service", "Search Service",
     "Full-text search powered by SQLite FTS5 with ranking and highlighting", "simple"),
    ("n7", "service", "Audit Service",
     "Middleware-based audit logging capturing all state-changing API operations", "simple"),
    ("n8", "component", "Diagram Renderer",
     "Thumbnail generator producing SVG previews of canvas diagrams for gallery display", "simple"),
    ("n9", "interface", "REST API",
     "JSON REST interface at /api/* with OpenAPI documentation and JWT bearer auth", "simple"),
    ("n10", "actor", "User",
     "Human user interacting with the system through a web browser", "simple"),
    ("n11", "actor", "Admin",
     "Administrator with elevated privileges for user management and system settings", "simple"),
    ("n12", "component", "Version Control",
     "Element and diagram versioning with optimistic concurrency via ETags", "simple"),
    ("n13", "component", "Event Bus",
     "Internal event dispatch for audit logging and thumbnail regeneration", "simple"),
    ("n14", "component", "Export Engine",
     "Diagram export to SVG, PNG, and PDF formats using html-to-image", "simple"),
    ("n15", "component", "Middleware Stack",
     "CORS, rate limiting, security headers, and audit middleware layers", "simple"),

    # ── UML notation (12 elements, indices 15–26) ────────────────────────────
    ("u1", "class", "DiagramService",
     "Manages diagram CRUD and versioning", "uml"),
    ("u2", "class", "ElementService",
     "Manages element CRUD and versioning", "uml"),
    ("u3", "class", "AuthController",
     "Handles authentication and authorization", "uml"),
    ("u4", "class", "PackageService",
     "Manages package hierarchy", "uml"),
    ("u5", "interface_uml", "IRenderer",
     "Interface for diagram rendering", "uml"),
    ("u6", "interface_uml", "IExporter",
     "Interface for export operations", "uml"),
    ("u7", "abstract_class", "BaseVersionedEntity",
     "Base class for all versioned entities", "uml"),
    ("u8", "enumeration", "NotationType",
     "Enum: simple, uml, archimate, c4", "uml"),
    ("u9", "use_case", "CreateDiagram",
     "User creates a new diagram", "uml"),
    ("u10", "use_case", "ManageElements",
     "User manages elements on canvas", "uml"),
    ("u11", "state", "DiagramDraft",
     "Diagram in draft/editing state", "uml"),
    ("u12", "state", "DiagramPublished",
     "Diagram published/finalized", "uml"),

    # ── ArchiMate notation (18 elements, indices 27–44) ──────────────────────
    ("a1", "business_actor", "Architect",
     "Enterprise architect using Iris for modelling", "archimate"),
    ("a2", "business_role", "ModelOwner",
     "Role responsible for maintaining architecture models", "archimate"),
    ("a3", "business_process", "ArchitectureModeling",
     "Process of creating and maintaining architecture models", "archimate"),
    ("a4", "business_service", "DiagramDesign",
     "Service providing diagram creation and editing capabilities", "archimate"),
    ("a5", "application_component", "IrisApplication",
     "The Iris application as an ArchiMate application component", "archimate"),
    ("a6", "application_service", "CanvasEditor",
     "Interactive canvas editing service within Iris", "archimate"),
    ("a7", "application_interface", "RESTEndpoint",
     "REST API endpoint interface for external integrations", "archimate"),
    ("a8", "application_function", "ThumbnailGeneration",
     "Function that generates diagram preview thumbnails", "archimate"),
    ("a9", "technology_node", "AppServer",
     "Application server hosting the Iris backend", "archimate"),
    ("a10", "technology_service", "DatabaseService",
     "SQLite database technology service", "archimate"),
    ("a11", "technology_artifact", "SQLiteFile",
     "SQLite database file artifact on disk", "archimate"),
    ("a12", "technology_device", "WebBrowser",
     "Web browser device rendering the frontend", "archimate"),
    ("a13", "stakeholder", "EnterpriseArchitect",
     "Stakeholder driving architecture governance", "archimate"),
    ("a14", "driver", "DigitalTransformation",
     "Driver for adopting modern architecture tooling", "archimate"),
    ("a15", "goal", "ModelingEfficiency",
     "Goal to improve modelling speed and quality", "archimate"),
    ("a16", "requirement_archimate", "MultiNotationSupport",
     "Requirement to support multiple notation standards", "archimate"),
    ("a17", "capability", "ArchitectureModelingCap",
     "Capability for enterprise architecture modelling", "archimate"),
    ("a18", "resource", "DevelopmentTeam",
     "Development team resource for building Iris", "archimate"),

    # ── C4 notation (10 elements, indices 45–54) ─────────────────────────────
    ("c1", "person", "IrisUser",
     "End user browsing and editing architecture diagrams", "c4"),
    ("c2", "person", "IrisAdmin",
     "Administrator managing users and system settings", "c4"),
    ("c3", "software_system", "IrisPlatform",
     "Architecture modelling platform with multi-notation support", "c4"),
    ("c4_ext_browser", "software_system_external", "WebBrowserExt",
     "External web browser rendering the SvelteKit frontend", "c4"),
    ("c5", "software_system_external", "SQLiteEngine",
     "Embedded SQLite database engine with WAL mode", "c4"),
    ("c6", "container", "SvelteKitFrontend",
     "SvelteKit + Svelte 5 frontend application container", "c4"),
    ("c7", "container", "FastAPIBackend",
     "FastAPI REST API backend container", "c4"),
    ("c8", "container", "SQLiteDatabase",
     "SQLite database container with WAL and FTS5", "c4"),
    ("c9", "c4_component", "AuthModule",
     "Authentication and authorization component", "c4"),
    ("c10", "c4_component", "CanvasModule",
     "Canvas rendering and editing component", "c4"),
]

_ELEMENT_DESCRIPTIONS = {nid: desc for nid, _, _, desc, _ in _ENTITIES}

# ── Relationships ────────────────────────────────────────────────────────────
# (index, source_node, target_node, rel_type, label, description)

_RELATIONSHIPS: list[tuple[int, str, str, str, str, str]] = [
    # ── Simple notation (20, indices 0–19) ───────────────────────────────────
    (0, "n10", "n1", "uses", "Browses",
     "User interacts with the Frontend via web browser"),
    (1, "n11", "n1", "uses", "Manages system",
     "Admin accesses Frontend for user and settings management"),
    (2, "n1", "n9", "uses", "API calls",
     "Frontend communicates with Backend through the REST API interface"),
    (3, "n9", "n2", "uses", "Serves",
     "REST API interface is served by the Backend"),
    (4, "n1", "n5", "uses", "Embeds",
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
    (19, "n15", "n2", "uses", "Wraps",
     "Middleware Stack wraps Backend request handling"),

    # ── UML notation (10, indices 20–29) ─────────────────────────────────────
    (20, "u1", "u7", "generalization", "Extends",
     "DiagramService extends BaseVersionedEntity"),
    (21, "u2", "u7", "generalization", "Extends",
     "ElementService extends BaseVersionedEntity"),
    (22, "u3", "u1", "dependency", "Uses",
     "AuthController depends on DiagramService"),
    (23, "u3", "u2", "dependency", "Uses",
     "AuthController depends on ElementService"),
    (24, "u4", "u7", "generalization", "Extends",
     "PackageService extends BaseVersionedEntity"),
    (25, "u5", "u1", "realization", "Renders",
     "IRenderer is realized by DiagramService"),
    (26, "u6", "u1", "realization", "Exports",
     "IExporter is realized by DiagramService"),
    (27, "u1", "u8", "dependency", "Uses",
     "DiagramService depends on NotationType enum"),
    (28, "u9", "u1", "association", "Invokes",
     "CreateDiagram use case invokes DiagramService"),
    (29, "u10", "u2", "association", "Invokes",
     "ManageElements use case invokes ElementService"),

    # ── ArchiMate notation (12, indices 30–41) ───────────────────────────────
    (30, "a1", "a2", "assignment", "Fills",
     "Architect is assigned the ModelOwner role"),
    (31, "a2", "a3", "assignment", "Performs",
     "ModelOwner performs ArchitectureModeling process"),
    (32, "a3", "a4", "serving", "Realizes",
     "ArchitectureModeling process serves DiagramDesign"),
    (33, "a4", "a5", "serving", "Provided by",
     "DiagramDesign is served by IrisApplication"),
    (34, "a5", "a6", "archimate_composition", "Contains",
     "IrisApplication contains CanvasEditor service"),
    (35, "a5", "a7", "archimate_composition", "Exposes",
     "IrisApplication exposes RESTEndpoint interface"),
    (36, "a5", "a8", "archimate_composition", "Contains",
     "IrisApplication contains ThumbnailGeneration function"),
    (37, "a9", "a5", "serving", "Hosts",
     "AppServer serves IrisApplication"),
    (38, "a9", "a10", "archimate_composition", "Provides",
     "AppServer provides DatabaseService"),
    (39, "a10", "a11", "access", "Stores in",
     "DatabaseService accesses SQLiteFile artifact"),
    (40, "a12", "a5", "serving", "Renders",
     "WebBrowser serves IrisApplication frontend"),
    (41, "a13", "a14", "association", "Motivates",
     "EnterpriseArchitect drives DigitalTransformation"),

    # ── C4 notation (8, indices 42–49) ───────────────────────────────────────
    (42, "c1", "c3", "c4_relationship", "Uses",
     "IrisUser uses IrisPlatform via HTTPS"),
    (43, "c2", "c3", "c4_relationship", "Administers",
     "IrisAdmin administers IrisPlatform"),
    (44, "c3", "c4_ext_browser", "c4_relationship", "Delivers to",
     "IrisPlatform delivers content to WebBrowser"),
    (45, "c3", "c5", "c4_relationship", "Stores in",
     "IrisPlatform stores data in SQLiteEngine"),
    (46, "c6", "c7", "c4_relationship", "Calls API",
     "SvelteKitFrontend calls FastAPIBackend via REST"),
    (47, "c7", "c8", "c4_relationship", "Reads/writes",
     "FastAPIBackend reads/writes SQLiteDatabase"),
    (48, "c7", "c9", "c4_relationship", "Contains",
     "FastAPIBackend contains AuthModule"),
    (49, "c7", "c10", "c4_relationship", "Contains",
     "FastAPIBackend contains CanvasModule"),
]

# ── Package definitions ─────────────────────────────────────────────────────
# (index, name, description, parent_index_or_none)
_PACKAGES = [
    (0, "Iris", "Root package for Iris architecture examples", None),
    (1, "Simple Notation", "Diagrams using simple notation elements", 0),
    (2, "UML Notation", "Diagrams using UML notation elements", 0),
    (3, "ArchiMate Notation", "Diagrams using ArchiMate notation elements", 0),
    (4, "C4 Notation", "Diagrams using C4 notation elements", 0),
]


# ── Diagram builder functions ────────────────────────────────────────────────

def _e(eids: dict, nid: str) -> dict:
    """Build entity data dict for a node referencing an element."""
    _, etype, name, desc, _ = next(e for e in _ENTITIES if e[0] == nid)
    return {"label": name, "entityType": etype,
            "description": desc, "entityId": eids.get(nid, "")}


def _r(rids: dict, idx: int) -> str:
    """Get relationship ID by index."""
    return rids.get(f"r{idx}", "")


# ── Simple Notation Diagrams (10, indices 0–9) ───────────────────────────────

def _build_simple_component(eids: dict, rids: dict, **_kw: object) -> dict:
    """Simple component: Iris Architecture overview."""
    nodes = _grid_nodes([
        {"id": "n10", "type": "actor", "data": _e(eids, "n10")},
        {"id": "n11", "type": "actor", "data": _e(eids, "n11")},
        {"id": "n9", "type": "interface", "data": _e(eids, "n9")},
        {"id": "n1", "type": "component", "data": _e(eids, "n1")},
        {"id": "n2", "type": "component", "data": _e(eids, "n2")},
        {"id": "n5", "type": "component", "data": _e(eids, "n5")},
        {"id": "n4", "type": "service", "data": _e(eids, "n4")},
        {"id": "n3", "type": "database", "data": _e(eids, "n3")},
    ])
    edges = [
        {"id": "e0", "source": "n10", "target": "n1", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Browses", "relationshipId": _r(rids, 0)}},
        {"id": "e1", "source": "n11", "target": "n1", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Manages", "relationshipId": _r(rids, 1)}},
        {"id": "e2", "source": "n1", "target": "n9", "type": "uses",
         "data": {"relationshipType": "uses", "label": "API calls", "relationshipId": _r(rids, 2)}},
        {"id": "e3", "source": "n9", "target": "n2", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Serves", "relationshipId": _r(rids, 3)}},
        {"id": "e4", "source": "n1", "target": "n5", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Embeds", "relationshipId": _r(rids, 4)}},
        {"id": "e5", "source": "n2", "target": "n4", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Auth", "relationshipId": _r(rids, 7)}},
        {"id": "e6", "source": "n2", "target": "n3", "type": "uses",
         "data": {"relationshipType": "uses", "label": "SQL", "relationshipId": _r(rids, 8)}},
        {"id": "e7", "source": "n4", "target": "n3", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Users", "relationshipId": _r(rids, 9)}},
    ]
    return {"nodes": nodes, "edges": edges}


def _build_simple_sequence(eids: dict, rids: dict, **_kw: object) -> dict:
    """Simple sequence: Iris request lifecycle."""
    return {
        "participants": [
            {"id": "p1", "name": "User", "type": "actor", "entityId": eids.get("n10", "")},
            {"id": "p2", "name": "Frontend", "type": "component", "entityId": eids.get("n1", "")},
            {"id": "p3", "name": "Backend", "type": "component", "entityId": eids.get("n2", "")},
            {"id": "p4", "name": "Auth", "type": "service", "entityId": eids.get("n4", "")},
            {"id": "p5", "name": "Database", "type": "database", "entityId": eids.get("n3", "")},
        ],
        "messages": [
            {"id": "m1", "from": "p1", "to": "p2", "label": "Navigate to /diagrams", "type": "sync", "order": 0},
            {"id": "m2", "from": "p2", "to": "p3", "label": "POST /api/auth/login", "type": "sync", "order": 1},
            {"id": "m3", "from": "p3", "to": "p4", "label": "Verify credentials", "type": "sync", "order": 2},
            {"id": "m4", "from": "p4", "to": "p5", "label": "SELECT user", "type": "sync", "order": 3},
            {"id": "m5", "from": "p5", "to": "p4", "label": "User record", "type": "reply", "order": 4},
            {"id": "m6", "from": "p4", "to": "p3", "label": "JWT tokens", "type": "reply", "order": 5},
            {"id": "m7", "from": "p3", "to": "p2", "label": "200 OK", "type": "reply", "order": 6},
            {"id": "m8", "from": "p2", "to": "p1", "label": "Render dashboard", "type": "reply", "order": 7},
        ],
        "activations": [
            {"participantId": "p2", "startOrder": 0, "endOrder": 7},
            {"participantId": "p3", "startOrder": 1, "endOrder": 6},
            {"participantId": "p4", "startOrder": 2, "endOrder": 5},
            {"participantId": "p5", "startOrder": 3, "endOrder": 4},
        ],
    }


def _build_simple_deployment(eids: dict, rids: dict, **_kw: object) -> dict:
    """Simple deployment: Iris data infrastructure."""
    nodes = _grid_nodes([
        {"id": "n3", "type": "database", "data": _e(eids, "n3")},
        {"id": "n6", "type": "service", "data": _e(eids, "n6")},
        {"id": "n7", "type": "service", "data": _e(eids, "n7")},
        {"id": "n13", "type": "component", "data": _e(eids, "n13")},
        {"id": "n12", "type": "component", "data": _e(eids, "n12")},
        {"id": "n8", "type": "component", "data": _e(eids, "n8")},
    ])
    edges = [
        {"id": "e0", "source": "n6", "target": "n3", "type": "depends_on",
         "data": {"relationshipType": "depends_on", "label": "FTS5", "relationshipId": _r(rids, 14)}},
        {"id": "e1", "source": "n7", "target": "n13", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Events", "relationshipId": _r(rids, 15)}},
        {"id": "e2", "source": "n13", "target": "n3", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Persist", "relationshipId": _r(rids, 16)}},
        {"id": "e3", "source": "n12", "target": "n3", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Versions", "relationshipId": _r(rids, 13)}},
        {"id": "e4", "source": "n8", "target": "n3", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Read", "relationshipId": _r(rids, 17)}},
    ]
    return {"nodes": nodes, "edges": edges}


def _build_simple_process(eids: dict, rids: dict, **_kw: object) -> dict:
    """Simple process: Diagram creation flow."""
    nodes = _grid_nodes([
        {"id": "n10", "type": "actor", "data": _e(eids, "n10")},
        {"id": "n1", "type": "component", "data": _e(eids, "n1")},
        {"id": "n5", "type": "component", "data": _e(eids, "n5")},
        {"id": "n2", "type": "component", "data": _e(eids, "n2")},
        {"id": "n3", "type": "database", "data": _e(eids, "n3")},
    ], cols=5, x_gap=250)
    edges = [
        {"id": "e0", "source": "n10", "target": "n1", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Opens app", "relationshipId": _r(rids, 0)}},
        {"id": "e1", "source": "n1", "target": "n5", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Opens canvas", "relationshipId": _r(rids, 4)}},
        {"id": "e2", "source": "n1", "target": "n2", "type": "depends_on",
         "data": {"relationshipType": "depends_on", "label": "Save diagram", "relationshipId": _r(rids, 6)}},
        {"id": "e3", "source": "n2", "target": "n3", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Persist", "relationshipId": _r(rids, 8)}},
    ]
    return {"nodes": nodes, "edges": edges}


def _build_simple_roadmap(eids: dict, rids: dict, **_kw: object) -> dict:
    """Simple roadmap: Iris product milestones."""
    nodes = _grid_nodes([
        {"id": "v1", "type": "component", "data": {"label": "v1.0 — Foundation", "entityType": "component",
         "description": "Core CRUD, authentication, canvas, and versioning"}},
        {"id": "v2", "type": "component", "data": {"label": "v2.0 — Multi-Notation", "entityType": "component",
         "description": "UML, ArchiMate, C4 support, import, sets, packages"}},
        {"id": "v3", "type": "component", "data": {"label": "v3.0 — Enterprise", "entityType": "component",
         "description": "Collaboration, real-time editing, cloud deployment"}},
        {"id": "v4", "type": "component", "data": {"label": "v4.0 — AI-Assisted", "entityType": "component",
         "description": "AI-powered diagram generation and analysis"}},
    ], cols=4, x_gap=280)
    edges = [
        {"id": "e0", "source": "v1", "target": "v2", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Builds on"}},
        {"id": "e1", "source": "v2", "target": "v3", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Evolves to"}},
        {"id": "e2", "source": "v3", "target": "v4", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Evolves to"}},
    ]
    return {"nodes": nodes, "edges": edges}


def _build_simple_free_form(eids: dict, rids: dict, **_kw: object) -> dict:
    """Simple free_form: Iris database schema overview (20 tables)."""
    tables = [
        ("t_roles", "roles", "id, name, description, created_at"),
        ("t_role_perms", "role_permissions", "role_id FK→roles, permission"),
        ("t_users", "users", "id, username, password_hash, role FK→roles, is_active"),
        ("t_pwd_hist", "password_history", "user_id FK→users, password_hash, changed_at"),
        ("t_refresh", "refresh_tokens", "id, user_id FK→users, family_id, expires_at"),
        ("t_elements", "elements", "id, element_type, set_id, current_version, is_deleted"),
        ("t_element_ver", "element_versions", "element_id FK→elements, version, name, data"),
        ("t_element_tags", "element_tags", "element_id FK→elements, tag"),
        ("t_rels", "relationships", "id, source_element_id, target_element_id, type"),
        ("t_rel_ver", "relationship_versions", "relationship_id FK→rels, version, label"),
        ("t_diagrams", "diagrams", "id, diagram_type, set_id, current_version, notation"),
        ("t_diagram_ver", "diagram_versions", "diagram_id FK→diagrams, version, name, data"),
        ("t_diagram_tags", "diagram_tags", "diagram_id FK→diagrams, tag"),
        ("t_comments", "comments", "id, target_type, target_id, user_id, content"),
        ("t_bookmarks", "bookmarks", "user_id FK→users, diagram_id FK→diagrams"),
        ("t_thumbs", "diagram_thumbnails", "diagram_id FK→diagrams, theme, thumbnail"),
        ("t_elem_fts", "elements_fts", "FTS5 virtual table for element search"),
        ("t_diag_fts", "diagrams_fts", "FTS5 virtual table for diagram search"),
        ("t_settings", "settings", "key, value, updated_at, updated_by"),
        ("t_audit", "audit_log", "Separate DB: id, timestamp, user_id, action, hash chain"),
    ]
    node_defs = [
        {"id": tid, "type": "database",
         "data": {"label": name, "entityType": "database", "description": desc}}
        for tid, name, desc in tables
    ]
    nodes = _grid_nodes(node_defs, cols=4, x_gap=300, y_gap=200)
    fk_edges = [
        ("t_role_perms", "t_roles"), ("t_users", "t_roles"),
        ("t_pwd_hist", "t_users"), ("t_refresh", "t_users"),
        ("t_element_ver", "t_elements"), ("t_element_tags", "t_elements"),
        ("t_rels", "t_elements"), ("t_rel_ver", "t_rels"),
        ("t_diagram_ver", "t_diagrams"), ("t_diagram_tags", "t_diagrams"),
        ("t_comments", "t_users"), ("t_bookmarks", "t_users"),
        ("t_bookmarks", "t_diagrams"), ("t_thumbs", "t_diagrams"),
    ]
    edges = [
        {"id": f"fk{i}", "source": src, "target": tgt, "type": "depends_on",
         "data": {"relationshipType": "depends_on", "label": "FK"}}
        for i, (src, tgt) in enumerate(fk_edges)
    ]
    return {"nodes": nodes, "edges": edges}


def _build_simple_use_case(eids: dict, rids: dict, **_kw: object) -> dict:
    """Simple use_case: User interactions with Iris."""
    nodes = _grid_nodes([
        {"id": "n10", "type": "actor", "data": _e(eids, "n10")},
        {"id": "n11", "type": "actor", "data": _e(eids, "n11")},
        {"id": "uc1", "type": "component", "data": {"label": "Create Diagram", "entityType": "component",
         "description": "User creates a new diagram on the canvas"}},
        {"id": "uc2", "type": "component", "data": {"label": "Import Model", "entityType": "component",
         "description": "User imports a SparxEA .qea file"}},
        {"id": "uc3", "type": "component", "data": {"label": "Manage Users", "entityType": "component",
         "description": "Admin creates and manages user accounts"}},
    ])
    edges = [
        {"id": "e0", "source": "n10", "target": "uc1", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Performs"}},
        {"id": "e1", "source": "n10", "target": "uc2", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Performs"}},
        {"id": "e2", "source": "n11", "target": "uc3", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Performs"}},
        {"id": "e3", "source": "n11", "target": "uc1", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Performs"}},
    ]
    return {"nodes": nodes, "edges": edges}


def _build_simple_state_machine(eids: dict, rids: dict, **_kw: object) -> dict:
    """Simple state_machine: Diagram lifecycle states."""
    nodes = _grid_nodes([
        {"id": "s1", "type": "component", "data": {"label": "Draft", "entityType": "component",
         "description": "Diagram is being created or edited"}},
        {"id": "s2", "type": "component", "data": {"label": "Published", "entityType": "component",
         "description": "Diagram is finalized and shared"}},
        {"id": "s3", "type": "component", "data": {"label": "Archived", "entityType": "component",
         "description": "Diagram is archived for reference"}},
        {"id": "s4", "type": "component", "data": {"label": "Deleted", "entityType": "component",
         "description": "Diagram is soft-deleted in recycle bin"}},
    ], cols=4, x_gap=280)
    edges = [
        {"id": "e0", "source": "s1", "target": "s2", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Publish"}},
        {"id": "e1", "source": "s2", "target": "s3", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Archive"}},
        {"id": "e2", "source": "s2", "target": "s1", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Edit"}},
        {"id": "e3", "source": "s3", "target": "s4", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Delete"}},
    ]
    return {"nodes": nodes, "edges": edges}


def _build_simple_system_context(eids: dict, rids: dict, **_kw: object) -> dict:
    """Simple system_context: Iris system boundary."""
    nodes = _grid_nodes([
        {"id": "n10", "type": "actor", "data": _e(eids, "n10")},
        {"id": "n11", "type": "actor", "data": _e(eids, "n11")},
        {"id": "sys", "type": "component", "data": {"label": "Iris Platform", "entityType": "component",
         "description": "Architecture modelling platform"}},
        {"id": "browser", "type": "component", "data": {"label": "Web Browser", "entityType": "component",
         "description": "Client-side rendering"}},
        {"id": "sqlite", "type": "database", "data": {"label": "SQLite", "entityType": "database",
         "description": "Embedded database engine"}},
    ])
    edges = [
        {"id": "e0", "source": "n10", "target": "sys", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Uses"}},
        {"id": "e1", "source": "n11", "target": "sys", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Administers"}},
        {"id": "e2", "source": "sys", "target": "browser", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Delivers to"}},
        {"id": "e3", "source": "sys", "target": "sqlite", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Persists in"}},
    ]
    return {"nodes": nodes, "edges": edges}


def _build_simple_container(eids: dict, rids: dict, **_kw: object) -> dict:
    """Simple container: Iris container view."""
    nodes = _grid_nodes([
        {"id": "n1", "type": "component", "data": _e(eids, "n1")},
        {"id": "n2", "type": "component", "data": _e(eids, "n2")},
        {"id": "n3", "type": "database", "data": _e(eids, "n3")},
        {"id": "n4", "type": "service", "data": _e(eids, "n4")},
        {"id": "n5", "type": "component", "data": _e(eids, "n5")},
    ])
    edges = [
        {"id": "e0", "source": "n1", "target": "n2", "type": "depends_on",
         "data": {"relationshipType": "depends_on", "label": "REST", "relationshipId": _r(rids, 6)}},
        {"id": "e1", "source": "n2", "target": "n3", "type": "uses",
         "data": {"relationshipType": "uses", "label": "SQL", "relationshipId": _r(rids, 8)}},
        {"id": "e2", "source": "n2", "target": "n4", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Auth", "relationshipId": _r(rids, 7)}},
        {"id": "e3", "source": "n1", "target": "n5", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Embeds", "relationshipId": _r(rids, 4)}},
    ]
    return {"nodes": nodes, "edges": edges}


# ── UML Notation Diagrams (8, indices 10–17) ─────────────────────────────────

def _build_uml_component(eids: dict, rids: dict, **_kw: object) -> dict:
    """UML component: Iris service modules."""
    nodes = _grid_nodes([
        {"id": "u3", "type": "class", "data": _e(eids, "u3")},
        {"id": "u5", "type": "interface_uml", "data": _e(eids, "u5")},
        {"id": "u6", "type": "interface_uml", "data": _e(eids, "u6")},
        {"id": "u1", "type": "class", "data": _e(eids, "u1")},
        {"id": "u2", "type": "class", "data": _e(eids, "u2")},
    ])
    edges = [
        {"id": "e0", "source": "u3", "target": "u1", "type": "dependency",
         "data": {"relationshipType": "dependency", "label": "Uses", "relationshipId": _r(rids, 22)}},
        {"id": "e1", "source": "u3", "target": "u2", "type": "dependency",
         "data": {"relationshipType": "dependency", "label": "Uses", "relationshipId": _r(rids, 23)}},
        {"id": "e2", "source": "u5", "target": "u1", "type": "realization",
         "data": {"relationshipType": "realization", "label": "Renders", "relationshipId": _r(rids, 25)}},
        {"id": "e3", "source": "u6", "target": "u1", "type": "realization",
         "data": {"relationshipType": "realization", "label": "Exports", "relationshipId": _r(rids, 26)}},
    ]
    return {"nodes": nodes, "edges": edges}


def _build_uml_sequence(eids: dict, rids: dict, **_kw: object) -> dict:
    """UML sequence: API request flow (login + fetch)."""
    return {
        "participants": [
            {"id": "p1", "name": "Browser", "type": "actor", "entityId": eids.get("n10", "")},
            {"id": "p2", "name": "Frontend", "type": "component", "entityId": eids.get("n1", "")},
            {"id": "p3", "name": "Backend", "type": "component", "entityId": eids.get("n2", "")},
            {"id": "p4", "name": "Auth Service", "type": "service", "entityId": eids.get("n4", "")},
            {"id": "p5", "name": "Database", "type": "component", "entityId": eids.get("n3", "")},
        ],
        "messages": [
            {"id": "m1", "from": "p1", "to": "p2", "label": "Navigate to /diagrams", "type": "sync", "order": 0},
            {"id": "m2", "from": "p2", "to": "p3", "label": "POST /api/auth/login", "type": "sync", "order": 1},
            {"id": "m3", "from": "p3", "to": "p4", "label": "Verify credentials", "type": "sync", "order": 2},
            {"id": "m4", "from": "p4", "to": "p5", "label": "SELECT user by username", "type": "sync", "order": 3},
            {"id": "m5", "from": "p5", "to": "p4", "label": "User record", "type": "reply", "order": 4},
            {"id": "m6", "from": "p4", "to": "p3", "label": "JWT access + refresh tokens", "type": "reply", "order": 5},
            {"id": "m7", "from": "p3", "to": "p2", "label": "200 {access_token}", "type": "reply", "order": 6},
            {"id": "m8", "from": "p2", "to": "p3", "label": "GET /api/diagrams (Bearer token)", "type": "sync", "order": 7},
            {"id": "m9", "from": "p3", "to": "p5", "label": "SELECT diagrams with versions", "type": "sync", "order": 8},
            {"id": "m10", "from": "p5", "to": "p3", "label": "Diagram list", "type": "reply", "order": 9},
            {"id": "m11", "from": "p3", "to": "p2", "label": "200 [{diagram}, ...]", "type": "reply", "order": 10},
            {"id": "m12", "from": "p2", "to": "p1", "label": "Render gallery", "type": "reply", "order": 11},
        ],
        "activations": [
            {"participantId": "p2", "startOrder": 0, "endOrder": 11},
            {"participantId": "p3", "startOrder": 1, "endOrder": 6},
            {"participantId": "p4", "startOrder": 2, "endOrder": 5},
            {"participantId": "p5", "startOrder": 3, "endOrder": 4},
            {"participantId": "p3", "startOrder": 7, "endOrder": 10},
            {"participantId": "p5", "startOrder": 8, "endOrder": 9},
        ],
    }


def _build_uml_class(eids: dict, rids: dict, **_kw: object) -> dict:
    """UML class: Iris domain model."""
    nodes = _grid_nodes([
        {"id": "u7", "type": "abstract_class", "data": _e(eids, "u7")},
        {"id": "u8", "type": "enumeration", "data": _e(eids, "u8")},
        {"id": "u1", "type": "class", "data": _e(eids, "u1")},
        {"id": "u2", "type": "class", "data": _e(eids, "u2")},
        {"id": "u4", "type": "class", "data": _e(eids, "u4")},
        {"id": "u3", "type": "class", "data": _e(eids, "u3")},
    ])
    edges = [
        {"id": "e0", "source": "u1", "target": "u7", "type": "generalization",
         "data": {"relationshipType": "generalization", "label": "Extends", "relationshipId": _r(rids, 20)}},
        {"id": "e1", "source": "u2", "target": "u7", "type": "generalization",
         "data": {"relationshipType": "generalization", "label": "Extends", "relationshipId": _r(rids, 21)}},
        {"id": "e2", "source": "u4", "target": "u7", "type": "generalization",
         "data": {"relationshipType": "generalization", "label": "Extends", "relationshipId": _r(rids, 24)}},
        {"id": "e3", "source": "u1", "target": "u8", "type": "dependency",
         "data": {"relationshipType": "dependency", "label": "Uses", "relationshipId": _r(rids, 27)}},
    ]
    return {"nodes": nodes, "edges": edges}


def _build_uml_deployment(eids: dict, rids: dict, **_kw: object) -> dict:
    """UML deployment: Iris runtime deployment."""
    nodes = _grid_nodes([
        {"id": "u3", "type": "class", "data": _e(eids, "u3")},
        {"id": "u1", "type": "class", "data": _e(eids, "u1")},
        {"id": "u2", "type": "class", "data": _e(eids, "u2")},
        {"id": "u4", "type": "class", "data": _e(eids, "u4")},
    ])
    edges = [
        {"id": "e0", "source": "u3", "target": "u1", "type": "dependency",
         "data": {"relationshipType": "dependency", "label": "Delegates", "relationshipId": _r(rids, 22)}},
        {"id": "e1", "source": "u3", "target": "u2", "type": "dependency",
         "data": {"relationshipType": "dependency", "label": "Delegates", "relationshipId": _r(rids, 23)}},
    ]
    return {"nodes": nodes, "edges": edges}


def _build_uml_process(eids: dict, rids: dict, **_kw: object) -> dict:
    """UML process: Edit workflow activity."""
    nodes = _grid_nodes([
        {"id": "act1", "type": "component", "data": {"label": "Open Diagram", "entityType": "component",
         "description": "User opens an existing diagram for editing"}},
        {"id": "act2", "type": "component", "data": {"label": "Edit Canvas", "entityType": "component",
         "description": "User modifies nodes and edges on canvas"}},
        {"id": "act3", "type": "component", "data": {"label": "Validate", "entityType": "component",
         "description": "System validates diagram structure"}},
        {"id": "act4", "type": "component", "data": {"label": "Save Version", "entityType": "component",
         "description": "System persists new version to database"}},
        {"id": "act5", "type": "component", "data": {"label": "Generate Thumbnail", "entityType": "component",
         "description": "System regenerates SVG/PNG thumbnail"}},
    ], cols=5, x_gap=240)
    edges = [
        {"id": "e0", "source": "act1", "target": "act2", "type": "uses",
         "data": {"relationshipType": "uses", "label": "→"}},
        {"id": "e1", "source": "act2", "target": "act3", "type": "uses",
         "data": {"relationshipType": "uses", "label": "→"}},
        {"id": "e2", "source": "act3", "target": "act4", "type": "uses",
         "data": {"relationshipType": "uses", "label": "→"}},
        {"id": "e3", "source": "act4", "target": "act5", "type": "uses",
         "data": {"relationshipType": "uses", "label": "→"}},
    ]
    return {"nodes": nodes, "edges": edges}


def _build_uml_free_form(eids: dict, rids: dict, **_kw: object) -> dict:
    """UML free_form: Mix of UML elements."""
    nodes = _grid_nodes([
        {"id": "u7", "type": "abstract_class", "data": _e(eids, "u7")},
        {"id": "u1", "type": "class", "data": _e(eids, "u1")},
        {"id": "u5", "type": "interface_uml", "data": _e(eids, "u5")},
        {"id": "u8", "type": "enumeration", "data": _e(eids, "u8")},
        {"id": "u9", "type": "use_case", "data": _e(eids, "u9")},
    ])
    edges = [
        {"id": "e0", "source": "u1", "target": "u7", "type": "generalization",
         "data": {"relationshipType": "generalization", "label": "Extends", "relationshipId": _r(rids, 20)}},
        {"id": "e1", "source": "u5", "target": "u1", "type": "realization",
         "data": {"relationshipType": "realization", "label": "Renders", "relationshipId": _r(rids, 25)}},
        {"id": "e2", "source": "u9", "target": "u1", "type": "association",
         "data": {"relationshipType": "association", "label": "Invokes", "relationshipId": _r(rids, 28)}},
    ]
    return {"nodes": nodes, "edges": edges}


def _build_uml_use_case(eids: dict, rids: dict, **_kw: object) -> dict:
    """UML use_case: Iris use cases."""
    nodes = _grid_nodes([
        {"id": "n10", "type": "actor", "data": _e(eids, "n10")},
        {"id": "n11", "type": "actor", "data": _e(eids, "n11")},
        {"id": "u9", "type": "use_case", "data": _e(eids, "u9")},
        {"id": "u10", "type": "use_case", "data": _e(eids, "u10")},
        {"id": "uc_export", "type": "use_case", "data": {"label": "Export Diagram", "entityType": "use_case",
         "description": "User exports diagram to SVG/PNG/PDF"}},
    ])
    edges = [
        {"id": "e0", "source": "n10", "target": "u9", "type": "association",
         "data": {"relationshipType": "association", "label": "Performs"}},
        {"id": "e1", "source": "n10", "target": "u10", "type": "association",
         "data": {"relationshipType": "association", "label": "Performs"}},
        {"id": "e2", "source": "n10", "target": "uc_export", "type": "association",
         "data": {"relationshipType": "association", "label": "Performs"}},
        {"id": "e3", "source": "n11", "target": "u9", "type": "association",
         "data": {"relationshipType": "association", "label": "Performs"}},
    ]
    return {"nodes": nodes, "edges": edges}


def _build_uml_state_machine(eids: dict, rids: dict, **_kw: object) -> dict:
    """UML state_machine: Element lifecycle."""
    nodes = _grid_nodes([
        {"id": "u11", "type": "state", "data": _e(eids, "u11")},
        {"id": "u12", "type": "state", "data": _e(eids, "u12")},
        {"id": "s_versioned", "type": "state", "data": {"label": "Versioned", "entityType": "state",
         "description": "Element has multiple versions in history"}},
        {"id": "s_deleted", "type": "state", "data": {"label": "Deleted", "entityType": "state",
         "description": "Element is soft-deleted in recycle bin"}},
    ], cols=4, x_gap=280)
    edges = [
        {"id": "e0", "source": "u11", "target": "u12", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Publish"}},
        {"id": "e1", "source": "u12", "target": "s_versioned", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Update"}},
        {"id": "e2", "source": "s_versioned", "target": "u11", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Edit"}},
        {"id": "e3", "source": "s_versioned", "target": "s_deleted", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Delete"}},
    ]
    return {"nodes": nodes, "edges": edges}


# ── ArchiMate Notation Diagrams (7, indices 18–24) ───────────────────────────

def _build_archimate_component(eids: dict, rids: dict, **_kw: object) -> dict:
    """ArchiMate component: Iris enterprise view (business+app+tech layers)."""
    nodes = _grid_nodes([
        {"id": "a1", "type": "business_actor",
         "data": {**_e(eids, "a1"), "layer": "business", "archimateType": "Business Actor"}},
        {"id": "a2", "type": "business_role",
         "data": {**_e(eids, "a2"), "layer": "business", "archimateType": "Business Role"}},
        {"id": "a3", "type": "business_process",
         "data": {**_e(eids, "a3"), "layer": "business", "archimateType": "Business Process"}},
        {"id": "a5", "type": "application_component",
         "data": {**_e(eids, "a5"), "layer": "application", "archimateType": "Application Component"}},
        {"id": "a6", "type": "application_service",
         "data": {**_e(eids, "a6"), "layer": "application", "archimateType": "Application Service"}},
        {"id": "a7", "type": "application_interface",
         "data": {**_e(eids, "a7"), "layer": "application", "archimateType": "Application Interface"}},
        {"id": "a9", "type": "technology_node",
         "data": {**_e(eids, "a9"), "layer": "technology", "archimateType": "Technology Node"}},
        {"id": "a10", "type": "technology_service",
         "data": {**_e(eids, "a10"), "layer": "technology", "archimateType": "Technology Service"}},
    ], cols=3)
    edges = [
        {"id": "e0", "source": "a1", "target": "a2", "type": "assignment",
         "data": {"relationshipType": "assignment", "label": "Fills", "relationshipId": _r(rids, 30)}},
        {"id": "e1", "source": "a2", "target": "a3", "type": "assignment",
         "data": {"relationshipType": "assignment", "label": "Performs", "relationshipId": _r(rids, 31)}},
        {"id": "e2", "source": "a3", "target": "a5", "type": "serving",
         "data": {"relationshipType": "serving", "label": "Realizes", "relationshipId": _r(rids, 33)}},
        {"id": "e3", "source": "a5", "target": "a6", "type": "archimate_composition",
         "data": {"relationshipType": "archimate_composition", "label": "Contains", "relationshipId": _r(rids, 34)}},
        {"id": "e4", "source": "a5", "target": "a7", "type": "archimate_composition",
         "data": {"relationshipType": "archimate_composition", "label": "Exposes", "relationshipId": _r(rids, 35)}},
        {"id": "e5", "source": "a9", "target": "a5", "type": "serving",
         "data": {"relationshipType": "serving", "label": "Hosts", "relationshipId": _r(rids, 37)}},
        {"id": "e6", "source": "a9", "target": "a10", "type": "archimate_composition",
         "data": {"relationshipType": "archimate_composition", "label": "Provides", "relationshipId": _r(rids, 38)}},
    ]
    return {"nodes": nodes, "edges": edges}


def _build_archimate_deployment(eids: dict, rids: dict, **_kw: object) -> dict:
    """ArchiMate deployment: Technology layer."""
    nodes = _grid_nodes([
        {"id": "a9", "type": "technology_node",
         "data": {**_e(eids, "a9"), "layer": "technology", "archimateType": "Technology Node"}},
        {"id": "a10", "type": "technology_service",
         "data": {**_e(eids, "a10"), "layer": "technology", "archimateType": "Technology Service"}},
        {"id": "a11", "type": "technology_artifact",
         "data": {**_e(eids, "a11"), "layer": "technology", "archimateType": "Technology Artifact"}},
        {"id": "a12", "type": "technology_device",
         "data": {**_e(eids, "a12"), "layer": "technology", "archimateType": "Technology Device"}},
        {"id": "a5", "type": "application_component",
         "data": {**_e(eids, "a5"), "layer": "application", "archimateType": "Application Component"}},
    ])
    edges = [
        {"id": "e0", "source": "a9", "target": "a10", "type": "archimate_composition",
         "data": {"relationshipType": "archimate_composition", "label": "Provides", "relationshipId": _r(rids, 38)}},
        {"id": "e1", "source": "a10", "target": "a11", "type": "access",
         "data": {"relationshipType": "access", "label": "Stores in", "relationshipId": _r(rids, 39)}},
        {"id": "e2", "source": "a12", "target": "a5", "type": "serving",
         "data": {"relationshipType": "serving", "label": "Renders", "relationshipId": _r(rids, 40)}},
        {"id": "e3", "source": "a9", "target": "a5", "type": "serving",
         "data": {"relationshipType": "serving", "label": "Hosts", "relationshipId": _r(rids, 37)}},
    ]
    return {"nodes": nodes, "edges": edges}


def _build_archimate_process(eids: dict, rids: dict, **_kw: object) -> dict:
    """ArchiMate process: Modeling business process."""
    nodes = _grid_nodes([
        {"id": "a1", "type": "business_actor",
         "data": {**_e(eids, "a1"), "layer": "business", "archimateType": "Business Actor"}},
        {"id": "a3", "type": "business_process",
         "data": {**_e(eids, "a3"), "layer": "business", "archimateType": "Business Process"}},
        {"id": "a4", "type": "business_service",
         "data": {**_e(eids, "a4"), "layer": "business", "archimateType": "Business Service"}},
        {"id": "a5", "type": "application_component",
         "data": {**_e(eids, "a5"), "layer": "application", "archimateType": "Application Component"}},
        {"id": "a6", "type": "application_service",
         "data": {**_e(eids, "a6"), "layer": "application", "archimateType": "Application Service"}},
    ])
    edges = [
        {"id": "e0", "source": "a1", "target": "a3", "type": "assignment",
         "data": {"relationshipType": "assignment", "label": "Performs"}},
        {"id": "e1", "source": "a3", "target": "a4", "type": "serving",
         "data": {"relationshipType": "serving", "label": "Realizes", "relationshipId": _r(rids, 32)}},
        {"id": "e2", "source": "a4", "target": "a5", "type": "serving",
         "data": {"relationshipType": "serving", "label": "Provided by", "relationshipId": _r(rids, 33)}},
        {"id": "e3", "source": "a5", "target": "a6", "type": "archimate_composition",
         "data": {"relationshipType": "archimate_composition", "label": "Contains", "relationshipId": _r(rids, 34)}},
    ]
    return {"nodes": nodes, "edges": edges}


def _build_archimate_roadmap(eids: dict, rids: dict, **_kw: object) -> dict:
    """ArchiMate roadmap: Implementation phases."""
    nodes = _grid_nodes([
        {"id": "wp1", "type": "component", "data": {"label": "Foundation Phase", "entityType": "component",
         "layer": "implementation_migration", "archimateType": "Work Package",
         "description": "Core platform with auth, CRUD, canvas"}},
        {"id": "wp2", "type": "component", "data": {"label": "Multi-Notation Phase", "entityType": "component",
         "layer": "implementation_migration", "archimateType": "Work Package",
         "description": "UML, ArchiMate, C4 support, imports"}},
        {"id": "wp3", "type": "component", "data": {"label": "Enterprise Phase", "entityType": "component",
         "layer": "implementation_migration", "archimateType": "Work Package",
         "description": "Collaboration, locking, advanced views"}},
        {"id": "wp4", "type": "component", "data": {"label": "Target Architecture", "entityType": "component",
         "layer": "implementation_migration", "archimateType": "Plateau",
         "description": "Fully featured architecture platform"}},
    ], cols=4, x_gap=280)
    edges = [
        {"id": "e0", "source": "wp1", "target": "wp2", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Enables"}},
        {"id": "e1", "source": "wp2", "target": "wp3", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Enables"}},
        {"id": "e2", "source": "wp3", "target": "wp4", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Delivers"}},
    ]
    return {"nodes": nodes, "edges": edges}


def _build_archimate_free_form(eids: dict, rids: dict, **_kw: object) -> dict:
    """ArchiMate free_form: Cross-layer overview."""
    nodes = _grid_nodes([
        {"id": "a1", "type": "business_actor",
         "data": {**_e(eids, "a1"), "layer": "business", "archimateType": "Business Actor"}},
        {"id": "a4", "type": "business_service",
         "data": {**_e(eids, "a4"), "layer": "business", "archimateType": "Business Service"}},
        {"id": "a5", "type": "application_component",
         "data": {**_e(eids, "a5"), "layer": "application", "archimateType": "Application Component"}},
        {"id": "a8", "type": "application_function",
         "data": {**_e(eids, "a8"), "layer": "application", "archimateType": "Application Function"}},
        {"id": "a9", "type": "technology_node",
         "data": {**_e(eids, "a9"), "layer": "technology", "archimateType": "Technology Node"}},
        {"id": "a11", "type": "technology_artifact",
         "data": {**_e(eids, "a11"), "layer": "technology", "archimateType": "Technology Artifact"}},
    ])
    edges = [
        {"id": "e0", "source": "a1", "target": "a4", "type": "serving",
         "data": {"relationshipType": "serving", "label": "Uses"}},
        {"id": "e1", "source": "a5", "target": "a8", "type": "archimate_composition",
         "data": {"relationshipType": "archimate_composition", "label": "Contains", "relationshipId": _r(rids, 36)}},
        {"id": "e2", "source": "a9", "target": "a5", "type": "serving",
         "data": {"relationshipType": "serving", "label": "Hosts", "relationshipId": _r(rids, 37)}},
    ]
    return {"nodes": nodes, "edges": edges}


def _build_archimate_motivation(eids: dict, rids: dict, **_kw: object) -> dict:
    """ArchiMate motivation: Stakeholder goals and requirements."""
    nodes = _grid_nodes([
        {"id": "a13", "type": "stakeholder",
         "data": {**_e(eids, "a13"), "layer": "motivation", "archimateType": "Stakeholder"}},
        {"id": "a14", "type": "driver",
         "data": {**_e(eids, "a14"), "layer": "motivation", "archimateType": "Driver"}},
        {"id": "a15", "type": "goal",
         "data": {**_e(eids, "a15"), "layer": "motivation", "archimateType": "Goal"}},
        {"id": "a16", "type": "requirement_archimate",
         "data": {**_e(eids, "a16"), "layer": "motivation", "archimateType": "Requirement"}},
        {"id": "a5", "type": "application_component",
         "data": {**_e(eids, "a5"), "layer": "application", "archimateType": "Application Component"}},
    ])
    edges = [
        {"id": "e0", "source": "a13", "target": "a14", "type": "association",
         "data": {"relationshipType": "association", "label": "Motivates", "relationshipId": _r(rids, 41)}},
        {"id": "e1", "source": "a14", "target": "a15", "type": "association",
         "data": {"relationshipType": "association", "label": "Drives"}},
        {"id": "e2", "source": "a15", "target": "a16", "type": "association",
         "data": {"relationshipType": "association", "label": "Requires"}},
        {"id": "e3", "source": "a16", "target": "a5", "type": "serving",
         "data": {"relationshipType": "serving", "label": "Realized by"}},
    ]
    return {"nodes": nodes, "edges": edges}


def _build_archimate_strategy(eids: dict, rids: dict, **_kw: object) -> dict:
    """ArchiMate strategy: Capabilities and resources."""
    nodes = _grid_nodes([
        {"id": "a17", "type": "capability",
         "data": {**_e(eids, "a17"), "layer": "strategy", "archimateType": "Capability"}},
        {"id": "a18", "type": "resource",
         "data": {**_e(eids, "a18"), "layer": "strategy", "archimateType": "Resource"}},
        {"id": "coa", "type": "component", "data": {"label": "Adopt Multi-Notation", "entityType": "component",
         "layer": "strategy", "archimateType": "Course of Action",
         "description": "Strategic course of action to adopt multi-notation modelling"}},
        {"id": "vs", "type": "component", "data": {"label": "Architecture Governance", "entityType": "component",
         "layer": "strategy", "archimateType": "Value Stream",
         "description": "Value stream for enterprise architecture governance"}},
    ], cols=4, x_gap=280)
    edges = [
        {"id": "e0", "source": "a17", "target": "a18", "type": "association",
         "data": {"relationshipType": "association", "label": "Requires"}},
        {"id": "e1", "source": "coa", "target": "a17", "type": "serving",
         "data": {"relationshipType": "serving", "label": "Develops"}},
        {"id": "e2", "source": "vs", "target": "coa", "type": "association",
         "data": {"relationshipType": "association", "label": "Includes"}},
    ]
    return {"nodes": nodes, "edges": edges}


# ── C4 Notation Diagrams (6, indices 25–30) ──────────────────────────────────

def _build_c4_component(eids: dict, rids: dict, **_kw: object) -> dict:
    """C4 component: Internal components of the backend."""
    nodes = _grid_nodes([
        {"id": "c7", "type": "container", "data": _e(eids, "c7")},
        {"id": "c9", "type": "c4_component", "data": _e(eids, "c9")},
        {"id": "c10", "type": "c4_component", "data": _e(eids, "c10")},
        {"id": "c8", "type": "container", "data": _e(eids, "c8")},
        {"id": "c6", "type": "container", "data": _e(eids, "c6")},
    ])
    edges = [
        {"id": "e0", "source": "c7", "target": "c9", "type": "c4_relationship",
         "data": {"relationshipType": "c4_relationship", "label": "Contains", "relationshipId": _r(rids, 48)}},
        {"id": "e1", "source": "c7", "target": "c10", "type": "c4_relationship",
         "data": {"relationshipType": "c4_relationship", "label": "Contains", "relationshipId": _r(rids, 49)}},
        {"id": "e2", "source": "c6", "target": "c7", "type": "c4_relationship",
         "data": {"relationshipType": "c4_relationship", "label": "Calls API", "relationshipId": _r(rids, 46)}},
        {"id": "e3", "source": "c7", "target": "c8", "type": "c4_relationship",
         "data": {"relationshipType": "c4_relationship", "label": "Reads/writes", "relationshipId": _r(rids, 47)}},
    ]
    return {"nodes": nodes, "edges": edges}


def _build_c4_sequence(eids: dict, rids: dict, **_kw: object) -> dict:
    """C4 sequence: User interaction flow."""
    return {
        "participants": [
            {"id": "p1", "name": "IrisUser", "type": "person", "entityId": eids.get("c1", "")},
            {"id": "p2", "name": "SvelteKit Frontend", "type": "container", "entityId": eids.get("c6", "")},
            {"id": "p3", "name": "FastAPI Backend", "type": "container", "entityId": eids.get("c7", "")},
            {"id": "p4", "name": "SQLite Database", "type": "container", "entityId": eids.get("c8", "")},
        ],
        "messages": [
            {"id": "m1", "from": "p1", "to": "p2", "label": "Browse diagrams", "type": "sync", "order": 0},
            {"id": "m2", "from": "p2", "to": "p3", "label": "GET /api/diagrams", "type": "sync", "order": 1},
            {"id": "m3", "from": "p3", "to": "p4", "label": "SELECT diagrams", "type": "sync", "order": 2},
            {"id": "m4", "from": "p4", "to": "p3", "label": "Result set", "type": "reply", "order": 3},
            {"id": "m5", "from": "p3", "to": "p2", "label": "JSON response", "type": "reply", "order": 4},
            {"id": "m6", "from": "p2", "to": "p1", "label": "Render gallery", "type": "reply", "order": 5},
        ],
        "activations": [
            {"participantId": "p2", "startOrder": 0, "endOrder": 5},
            {"participantId": "p3", "startOrder": 1, "endOrder": 4},
            {"participantId": "p4", "startOrder": 2, "endOrder": 3},
        ],
    }


def _build_c4_deployment(eids: dict, rids: dict, **_kw: object) -> dict:
    """C4 deployment: Production deployment view."""
    nodes = _grid_nodes([
        {"id": "c3", "type": "software_system", "data": _e(eids, "c3")},
        {"id": "c6", "type": "container", "data": _e(eids, "c6")},
        {"id": "c7", "type": "container", "data": _e(eids, "c7")},
        {"id": "c8", "type": "container", "data": _e(eids, "c8")},
    ])
    edges = [
        {"id": "e0", "source": "c6", "target": "c7", "type": "c4_relationship",
         "data": {"relationshipType": "c4_relationship", "label": "Calls", "technology": "REST/HTTPS",
                  "relationshipId": _r(rids, 46)}},
        {"id": "e1", "source": "c7", "target": "c8", "type": "c4_relationship",
         "data": {"relationshipType": "c4_relationship", "label": "Reads/writes", "technology": "SQLite WAL",
                  "relationshipId": _r(rids, 47)}},
    ]
    return {"nodes": nodes, "edges": edges}


def _build_c4_free_form(eids: dict, rids: dict, **_kw: object) -> dict:
    """C4 free_form: Mix of all C4 levels."""
    nodes = _grid_nodes([
        {"id": "c1", "type": "person", "data": _e(eids, "c1")},
        {"id": "c2", "type": "person", "data": _e(eids, "c2")},
        {"id": "c3", "type": "software_system", "data": _e(eids, "c3")},
        {"id": "c6", "type": "container", "data": _e(eids, "c6")},
        {"id": "c9", "type": "c4_component", "data": _e(eids, "c9")},
        {"id": "c10", "type": "c4_component", "data": _e(eids, "c10")},
    ])
    edges = [
        {"id": "e0", "source": "c1", "target": "c3", "type": "c4_relationship",
         "data": {"relationshipType": "c4_relationship", "label": "Uses", "relationshipId": _r(rids, 42)}},
        {"id": "e1", "source": "c2", "target": "c3", "type": "c4_relationship",
         "data": {"relationshipType": "c4_relationship", "label": "Administers", "relationshipId": _r(rids, 43)}},
        {"id": "e2", "source": "c6", "target": "c9", "type": "c4_relationship",
         "data": {"relationshipType": "c4_relationship", "label": "Uses"}},
    ]
    return {"nodes": nodes, "edges": edges}


def _build_c4_system_context(eids: dict, rids: dict, **_kw: object) -> dict:
    """C4 system_context: Iris in its environment."""
    nodes = _grid_nodes([
        {"id": "c1", "type": "person", "data": _e(eids, "c1")},
        {"id": "c2", "type": "person", "data": _e(eids, "c2")},
        {"id": "c3", "type": "software_system", "data": _e(eids, "c3")},
        {"id": "c4_ext_browser", "type": "software_system_external",
         "data": {**_e(eids, "c4_ext_browser"), "c4External": True}},
        {"id": "c5", "type": "software_system_external",
         "data": {**_e(eids, "c5"), "c4External": True}},
    ])
    edges = [
        {"id": "e0", "source": "c1", "target": "c3", "type": "c4_relationship",
         "data": {"relationshipType": "c4_relationship", "label": "Uses", "technology": "HTTPS/REST",
                  "relationshipId": _r(rids, 42)}},
        {"id": "e1", "source": "c2", "target": "c3", "type": "c4_relationship",
         "data": {"relationshipType": "c4_relationship", "label": "Administers", "technology": "HTTPS/REST",
                  "relationshipId": _r(rids, 43)}},
        {"id": "e2", "source": "c3", "target": "c4_ext_browser", "type": "c4_relationship",
         "data": {"relationshipType": "c4_relationship", "label": "Delivers to", "technology": "HTML/CSS/JS",
                  "relationshipId": _r(rids, 44)}},
        {"id": "e3", "source": "c3", "target": "c5", "type": "c4_relationship",
         "data": {"relationshipType": "c4_relationship", "label": "Stores in", "technology": "SQLite WAL",
                  "relationshipId": _r(rids, 45)}},
    ]
    return {"nodes": nodes, "edges": edges}


def _build_c4_container(eids: dict, rids: dict, **_kw: object) -> dict:
    """C4 container: Container-level decomposition."""
    nodes = _grid_nodes([
        {"id": "c1", "type": "person", "data": _e(eids, "c1")},
        {"id": "c6", "type": "container", "data": _e(eids, "c6")},
        {"id": "c7", "type": "container", "data": _e(eids, "c7")},
        {"id": "c8", "type": "container", "data": _e(eids, "c8")},
        {"id": "c5", "type": "software_system_external",
         "data": {**_e(eids, "c5"), "c4External": True}},
    ])
    edges = [
        {"id": "e0", "source": "c1", "target": "c6", "type": "c4_relationship",
         "data": {"relationshipType": "c4_relationship", "label": "Uses", "technology": "HTTPS"}},
        {"id": "e1", "source": "c6", "target": "c7", "type": "c4_relationship",
         "data": {"relationshipType": "c4_relationship", "label": "Calls API", "technology": "REST",
                  "relationshipId": _r(rids, 46)}},
        {"id": "e2", "source": "c7", "target": "c8", "type": "c4_relationship",
         "data": {"relationshipType": "c4_relationship", "label": "Reads/writes", "technology": "SQLite",
                  "relationshipId": _r(rids, 47)}},
    ]
    return {"nodes": nodes, "edges": edges}


# ── Overview Diagram (index 31, root package) ────────────────────────────────

def _build_system_overview(
    eids: dict, rids: dict, mids: dict[int, str] | None = None,
) -> dict:
    """Top-level overview with modelrefs to key diagrams per notation."""
    mids = mids or {}
    nodes = _grid_nodes([
        {"id": "mr0", "type": "modelref", "data": {"label": "Iris Architecture (Simple)",
         "entityType": "component", "description": "Core component overview",
         "linkedModelId": mids.get(0, "")}},
        {"id": "mr10", "type": "modelref", "data": {"label": "UML Components",
         "entityType": "component", "description": "UML service modules",
         "linkedModelId": mids.get(10, "")}},
        {"id": "mr18", "type": "modelref", "data": {"label": "ArchiMate Enterprise",
         "entityType": "component", "description": "Enterprise architecture view",
         "linkedModelId": mids.get(18, "")}},
        {"id": "mr29", "type": "modelref", "data": {"label": "C4 System Context",
         "entityType": "component", "description": "C4 system context diagram",
         "linkedModelId": mids.get(29, "")}},
        {"id": "mr5", "type": "modelref", "data": {"label": "Database Schema",
         "entityType": "database", "description": "Complete database schema",
         "linkedModelId": mids.get(5, "")}},
        {"id": "mr12", "type": "modelref", "data": {"label": "UML Domain Model",
         "entityType": "component", "description": "Class diagram of Iris domain",
         "linkedModelId": mids.get(12, "")}},
        {"id": "n10", "type": "actor", "data": _e(eids, "n10")},
        {"id": "n11", "type": "actor", "data": _e(eids, "n11")},
    ])
    edges = [
        {"id": "eo1", "source": "n10", "target": "mr0", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Uses system"}},
        {"id": "eo2", "source": "n10", "target": "mr29", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Context"}},
        {"id": "eo3", "source": "n11", "target": "mr18", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Manages"}},
        {"id": "eo4", "source": "mr0", "target": "mr5", "type": "depends_on",
         "data": {"relationshipType": "depends_on", "label": "Persistence"}},
        {"id": "eo5", "source": "mr18", "target": "mr0", "type": "uses",
         "data": {"relationshipType": "uses", "label": "Includes"}},
        {"id": "eo6", "source": "mr10", "target": "mr12", "type": "depends_on",
         "data": {"relationshipType": "depends_on", "label": "Domain model"}},
    ]
    return {"nodes": nodes, "edges": edges}


# ── Diagram definitions ───────────────────────────────────────────────────────

_DIAGRAMS = [
    # ── Simple Notation (pkg-1, indices 0–9) ─────────────────────────────────
    {"index": 0, "diagram_type": "component", "notation": "simple",
     "name": "Iris Architecture", "parent_package_index": 1,
     "description": "Component diagram showing Iris internal architecture with Frontend, Backend, DB, Auth, and Canvas Engine.",
     "builder": _build_simple_component, "tags": _DIAGRAM_TAGS},
    {"index": 1, "diagram_type": "sequence", "notation": "simple",
     "name": "Iris Request Lifecycle", "parent_package_index": 1,
     "description": "Sequence diagram showing a user login and dashboard render flow.",
     "builder": _build_simple_sequence, "tags": _DIAGRAM_TAGS},
    {"index": 2, "diagram_type": "deployment", "notation": "simple",
     "name": "Iris Data Infrastructure", "parent_package_index": 1,
     "description": "Deployment diagram showing database, search, audit, and versioning services.",
     "builder": _build_simple_deployment, "tags": _DIAGRAM_TAGS},
    {"index": 3, "diagram_type": "process", "notation": "simple",
     "name": "Diagram Creation Process", "parent_package_index": 1,
     "description": "Process diagram showing the flow of creating a diagram from user to database.",
     "builder": _build_simple_process, "tags": _DIAGRAM_TAGS},
    {"index": 4, "diagram_type": "roadmap", "notation": "simple",
     "name": "Iris Product Roadmap", "parent_package_index": 1,
     "description": "Roadmap showing Iris version milestones from v1 Foundation to v4 AI-Assisted.",
     "builder": _build_simple_roadmap, "tags": _DIAGRAM_TAGS},
    {"index": 5, "diagram_type": "free_form", "notation": "simple",
     "name": "Iris Database Schema", "parent_package_index": 1,
     "description": "Free-form diagram showing all 20 database tables and foreign key relationships.",
     "builder": _build_simple_free_form, "tags": _DIAGRAM_TAGS},
    {"index": 6, "diagram_type": "use_case", "notation": "simple",
     "name": "User Interactions", "parent_package_index": 1,
     "description": "Use case diagram showing User and Admin interactions with Iris.",
     "builder": _build_simple_use_case, "tags": _DIAGRAM_TAGS},
    {"index": 7, "diagram_type": "state_machine", "notation": "simple",
     "name": "Diagram Lifecycle", "parent_package_index": 1,
     "description": "State machine showing diagram states: Draft, Published, Archived, Deleted.",
     "builder": _build_simple_state_machine, "tags": _DIAGRAM_TAGS},
    {"index": 8, "diagram_type": "system_context", "notation": "simple",
     "name": "Iris System Boundary", "parent_package_index": 1,
     "description": "System context showing Iris with external actors and systems.",
     "builder": _build_simple_system_context, "tags": _DIAGRAM_TAGS},
    {"index": 9, "diagram_type": "container", "notation": "simple",
     "name": "Iris Container View", "parent_package_index": 1,
     "description": "Container view showing Frontend, Backend, Database containers.",
     "builder": _build_simple_container, "tags": _DIAGRAM_TAGS},

    # ── UML Notation (pkg-2, indices 10–17) ──────────────────────────────────
    {"index": 10, "diagram_type": "component", "notation": "uml",
     "name": "Iris UML Components", "parent_package_index": 2,
     "description": "UML component diagram showing AuthController, services, and interfaces.",
     "builder": _build_uml_component, "tags": _DIAGRAM_TAGS},
    {"index": 11, "diagram_type": "sequence", "notation": "uml",
     "name": "API Request Flow", "parent_package_index": 2,
     "description": "UML sequence diagram showing login and diagram fetch with full activation bars.",
     "builder": _build_uml_sequence, "tags": _DIAGRAM_TAGS},
    {"index": 12, "diagram_type": "class", "notation": "uml",
     "name": "Iris Domain Model", "parent_package_index": 2,
     "description": "UML class diagram showing service classes, abstract base, interfaces, and enum.",
     "builder": _build_uml_class, "tags": _DIAGRAM_TAGS},
    {"index": 13, "diagram_type": "deployment", "notation": "uml",
     "name": "Iris UML Deployment", "parent_package_index": 2,
     "description": "UML deployment diagram showing runtime service arrangement.",
     "builder": _build_uml_deployment, "tags": _DIAGRAM_TAGS},
    {"index": 14, "diagram_type": "process", "notation": "uml",
     "name": "Edit Workflow Activity", "parent_package_index": 2,
     "description": "UML activity diagram showing Open→Edit→Validate→Save→Thumbnail workflow.",
     "builder": _build_uml_process, "tags": _DIAGRAM_TAGS},
    {"index": 15, "diagram_type": "free_form", "notation": "uml",
     "name": "Iris UML Overview", "parent_package_index": 2,
     "description": "Free-form mix of UML classes, interfaces, use cases, and enumerations.",
     "builder": _build_uml_free_form, "tags": _DIAGRAM_TAGS},
    {"index": 16, "diagram_type": "use_case", "notation": "uml",
     "name": "Iris Use Cases", "parent_package_index": 2,
     "description": "UML use case diagram with User/Admin actors and CreateDiagram/ManageElements/Export.",
     "builder": _build_uml_use_case, "tags": _DIAGRAM_TAGS},
    {"index": 17, "diagram_type": "state_machine", "notation": "uml",
     "name": "Element Lifecycle States", "parent_package_index": 2,
     "description": "UML state machine showing Draft→Published→Versioned→Deleted element lifecycle.",
     "builder": _build_uml_state_machine, "tags": _DIAGRAM_TAGS},

    # ── ArchiMate Notation (pkg-3, indices 18–24) ────────────────────────────
    {"index": 18, "diagram_type": "component", "notation": "archimate",
     "name": "Iris Enterprise View", "parent_package_index": 3,
     "description": "ArchiMate enterprise view spanning business, application, and technology layers.",
     "builder": _build_archimate_component, "tags": _DIAGRAM_TAGS},
    {"index": 19, "diagram_type": "deployment", "notation": "archimate",
     "name": "Iris Technology Layer", "parent_package_index": 3,
     "description": "ArchiMate technology layer with AppServer, DatabaseService, Browser, and SQLite.",
     "builder": _build_archimate_deployment, "tags": _DIAGRAM_TAGS},
    {"index": 20, "diagram_type": "process", "notation": "archimate",
     "name": "Modeling Business Process", "parent_package_index": 3,
     "description": "ArchiMate process showing Architect→Modeling→DiagramDesign→App flow.",
     "builder": _build_archimate_process, "tags": _DIAGRAM_TAGS},
    {"index": 21, "diagram_type": "roadmap", "notation": "archimate",
     "name": "Implementation Roadmap", "parent_package_index": 3,
     "description": "ArchiMate roadmap with work packages and plateau for phased implementation.",
     "builder": _build_archimate_roadmap, "tags": _DIAGRAM_TAGS},
    {"index": 22, "diagram_type": "free_form", "notation": "archimate",
     "name": "Iris ArchiMate Overview", "parent_package_index": 3,
     "description": "ArchiMate free-form cross-layer overview spanning business, application, technology.",
     "builder": _build_archimate_free_form, "tags": _DIAGRAM_TAGS},
    {"index": 23, "diagram_type": "motivation", "notation": "archimate",
     "name": "Iris Motivation Viewpoint", "parent_package_index": 3,
     "description": "ArchiMate motivation viewpoint: Stakeholder, Driver, Goal, Requirement.",
     "builder": _build_archimate_motivation, "tags": _DIAGRAM_TAGS},
    {"index": 24, "diagram_type": "strategy", "notation": "archimate",
     "name": "Iris Strategy Viewpoint", "parent_package_index": 3,
     "description": "ArchiMate strategy viewpoint: Capability, Resource, Course of Action, Value Stream.",
     "builder": _build_archimate_strategy, "tags": _DIAGRAM_TAGS},

    # ── C4 Notation (pkg-4, indices 25–30) ───────────────────────────────────
    {"index": 25, "diagram_type": "component", "notation": "c4",
     "name": "Iris C4 Components", "parent_package_index": 4,
     "description": "C4 component diagram showing AuthModule, CanvasModule within BackendAPI.",
     "builder": _build_c4_component, "tags": _DIAGRAM_TAGS},
    {"index": 26, "diagram_type": "sequence", "notation": "c4",
     "name": "C4 Interaction Flow", "parent_package_index": 4,
     "description": "C4 sequence diagram: User→Frontend→Backend→Database interaction.",
     "builder": _build_c4_sequence, "tags": _DIAGRAM_TAGS},
    {"index": 27, "diagram_type": "deployment", "notation": "c4",
     "name": "Iris C4 Deployment", "parent_package_index": 4,
     "description": "C4 deployment diagram with container instances and technology labels.",
     "builder": _build_c4_deployment, "tags": _DIAGRAM_TAGS},
    {"index": 28, "diagram_type": "free_form", "notation": "c4",
     "name": "Iris C4 Overview", "parent_package_index": 4,
     "description": "C4 free-form overview mixing persons, systems, containers, and components.",
     "builder": _build_c4_free_form, "tags": _DIAGRAM_TAGS},
    {"index": 29, "diagram_type": "system_context", "notation": "c4",
     "name": "Iris C4 System Context", "parent_package_index": 4,
     "description": "C4 System Context showing Iris with external actors (User, Admin) and systems (Browser, SQLite).",
     "builder": _build_c4_system_context, "tags": _DIAGRAM_TAGS},
    {"index": 30, "diagram_type": "container", "notation": "c4",
     "name": "Iris C4 Containers", "parent_package_index": 4,
     "description": "C4 container diagram: SvelteKit Frontend, FastAPI Backend, SQLite Database.",
     "builder": _build_c4_container, "tags": _DIAGRAM_TAGS},

    # ── Overview (pkg-0, index 31) ───────────────────────────────────────────
    {"index": 31, "diagram_type": "component", "notation": "simple",
     "name": "Iris System Overview", "parent_package_index": 0,
     "description": "Top-level overview with modelrefs to key diagrams across all notations.",
     "builder": _build_system_overview, "tags": _DIAGRAM_TAGS},
]


# ── Seed logic ───────────────────────────────────────────────────────────────

async def _ensure_system_user(db: aiosqlite.Connection) -> None:
    """Create a deactivated system user for seed data ownership."""
    await db.execute(
        "INSERT OR IGNORE INTO users (id, username, password_hash, role, is_active) "
        "VALUES (?, ?, ?, ?, ?)",
        (_SYSTEM_USER_ID, "system", "!no-login-seed-user", "viewer", 0),
    )


async def _clear_old_seed_data(db: aiosqlite.Connection) -> None:
    """Delete old seed data by deterministic IDs in dependency order."""
    # Collect all possible deterministic IDs across v2 and v3
    max_elements = max(len(_ENTITIES), 15)  # v2 had 15
    max_rels = max(len(_RELATIONSHIPS), 20)  # v2 had 20
    max_diagrams = max(len(_DIAGRAMS), 7)  # v2 had 7
    max_packages = max(len(_PACKAGES), 4)  # v2 had 4

    element_ids = [_gen_id("element", i) for i in range(max_elements)]
    rel_ids = [_gen_id("rel", i) for i in range(max_rels)]
    diagram_ids = [_gen_id("diagram", i) for i in range(max_diagrams)]
    package_ids = [_gen_id("pkg", i) for i in range(max_packages)]

    # Delete in dependency order (children before parents)
    for did in diagram_ids:
        await db.execute("DELETE FROM diagram_tags WHERE diagram_id = ?", (did,))
        await db.execute("DELETE FROM diagram_versions WHERE diagram_id = ?", (did,))
        await db.execute("DELETE FROM diagram_thumbnails WHERE diagram_id = ?", (did,))
        await db.execute("DELETE FROM bookmarks WHERE diagram_id = ?", (did,))
        await db.execute("DELETE FROM comments WHERE target_id = ?", (did,))
        await db.execute(
            "UPDATE sets SET thumbnail_diagram_id = NULL "
            "WHERE thumbnail_diagram_id = ?", (did,),
        )
        await db.execute("DELETE FROM diagrams WHERE id = ?", (did,))
        await db.execute("DELETE FROM diagrams_fts WHERE diagram_id = ?", (did,))

    for rid in rel_ids:
        await db.execute("DELETE FROM relationship_versions WHERE relationship_id = ?", (rid,))
        await db.execute("DELETE FROM relationships WHERE id = ?", (rid,))

    for eid in element_ids:
        await db.execute("DELETE FROM element_tags WHERE element_id = ?", (eid,))
        await db.execute("DELETE FROM element_versions WHERE element_id = ?", (eid,))
        await db.execute("DELETE FROM elements_fts WHERE element_id = ?", (eid,))
        await db.execute("DELETE FROM elements WHERE id = ?", (eid,))

    # Delete packages (children first — all children have parent = pkg-0)
    for pid in reversed(package_ids):
        await db.execute("DELETE FROM package_versions WHERE package_id = ?", (pid,))
        await db.execute("DELETE FROM packages WHERE id = ?", (pid,))

    await db.commit()


async def seed_example_models(db: aiosqlite.Connection) -> None:
    """Seed example elements, packages, and diagrams demonstrating Iris architecture.

    Idempotency:
      - If pkg-4 (C4 Notation) exists → already v3, skip
      - If pkg-0 exists but not pkg-4 → v2, clear + reseed v3
      - If element_tags with tag='example' exist but no root package → v1, clear + reseed
      - Otherwise → fresh seed
    """
    # --- Skip if initial setup not yet completed ------------------------------
    cursor = await db.execute(
        "SELECT COUNT(*) FROM users WHERE is_active = 1"
    )
    row = await cursor.fetchone()
    if not row or row[0] == 0:
        return

    # --- v3 idempotency check: pkg-4 exists → already seeded v3 --------
    v3_marker_id = _gen_id("pkg", 4)
    cursor = await db.execute(
        "SELECT COUNT(*) FROM packages WHERE id = ?", (v3_marker_id,)
    )
    row = await cursor.fetchone()
    if row and row[0] > 0:
        return

    # --- v2→v3 migration: root package exists but no pkg-4 → clear + reseed ---
    root_pkg_id = _gen_id("pkg", 0)
    cursor = await db.execute(
        "SELECT COUNT(*) FROM packages WHERE id = ?", (root_pkg_id,)
    )
    row = await cursor.fetchone()
    if row and row[0] > 0:
        await _clear_old_seed_data(db)

    # --- v1→v3 migration: old seed exists without packages → clear + reseed ---
    cursor = await db.execute(
        "SELECT COUNT(*) FROM element_tags WHERE tag = 'example'"
    )
    row = await cursor.fetchone()
    if row and row[0] > 0:
        await _clear_old_seed_data(db)

    # --- Ensure system user exists for FK compliance --------------------------
    await _ensure_system_user(db)

    now = datetime.now(tz=UTC).isoformat()

    # --- Create packages ------------------------------------------------------
    pkg_id_map: dict[int, str] = {}
    for pkg_idx, pkg_name, pkg_desc, parent_idx in _PACKAGES:
        pkg_id = _gen_id("pkg", pkg_idx)
        pkg_id_map[pkg_idx] = pkg_id
        parent_pkg_id = pkg_id_map[parent_idx] if parent_idx is not None else None

        await db.execute(
            "INSERT INTO packages (id, current_version, "
            "created_at, created_by, updated_at, parent_package_id, set_id) "
            "VALUES (?, 1, ?, ?, ?, ?, ?)",
            (pkg_id, now, _SYSTEM_USER_ID, now, parent_pkg_id, _DEFAULT_SET_ID),
        )
        await db.execute(
            "INSERT INTO package_versions (package_id, version, name, description, "
            "data, change_type, change_summary, created_at, created_by) "
            "VALUES (?, 1, ?, ?, '{}', 'create', ?, ?, ?)",
            (pkg_id, pkg_name, pkg_desc, f"Seed package: {pkg_name}",
             now, _SYSTEM_USER_ID),
        )

    # --- Create elements ------------------------------------------------------
    element_ids: dict[str, str] = {}

    for idx, (node_id, element_type, name, description, notation) in enumerate(_ENTITIES):
        element_id = _gen_id("element", idx)
        element_ids[node_id] = element_id

        await db.execute(
            "INSERT INTO elements (id, element_type, set_id, current_version, "
            "created_at, created_by, updated_at, notation) VALUES (?, ?, ?, 1, ?, ?, ?, ?)",
            (element_id, element_type, _DEFAULT_SET_ID, now, _SYSTEM_USER_ID, now, notation),
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

    for ri, src, tgt, rel_type, label, desc in _RELATIONSHIPS:
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
    diagram_id_map: dict[int, str] = {}
    for model_def in _DIAGRAMS:
        diagram_id_map[model_def["index"]] = _gen_id("diagram", model_def["index"])

    for model_def in _DIAGRAMS:
        diagram_id = diagram_id_map[model_def["index"]]
        diagram_data = model_def["builder"](element_ids, rel_ids, mids=diagram_id_map)
        diagram_data_json = json.dumps(diagram_data)
        parent_package_id = pkg_id_map[model_def["parent_package_index"]]

        await db.execute(
            "INSERT INTO diagrams (id, diagram_type, set_id, current_version, "
            "created_at, created_by, updated_at, parent_package_id, notation) "
            "VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?)",
            (diagram_id, model_def["diagram_type"], _DEFAULT_SET_ID, now,
             _SYSTEM_USER_ID, now, parent_package_id, model_def["notation"]),
        )
        await db.execute(
            "INSERT INTO diagram_versions (diagram_id, version, name, description, "
            "data, change_type, created_at, created_by) "
            "VALUES (?, 1, ?, ?, ?, 'create', ?, ?)",
            (diagram_id, model_def["name"], model_def["description"],
             diagram_data_json, now, _SYSTEM_USER_ID),
        )

        for tag in model_def["tags"]:
            await db.execute(
                "INSERT INTO diagram_tags (diagram_id, tag, created_at, created_by) "
                "VALUES (?, ?, ?, ?)",
                (diagram_id, tag, now, _SYSTEM_USER_ID),
            )

    await db.commit()
