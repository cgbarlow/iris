"""Idempotent seed: example diagrams covering all diagram-type/notation permutations.

Creates elements representing the Iris system and 32 diagrams organised
into a 5-package hierarchy by notation:

  Iris (root package)
  ├── Iris Navigation (root — navigation_cell tiles → each notation)
  ├── Simple Notation   — 10 diagrams
  ├── UML Notation      — 8 diagrams
  ├── ArchiMate Notation — 7 diagrams
  └── C4 Notation       — 6 diagrams

v4 revision: intentional layouts, explicit edge routing via sourceHandle/
targetHandle, navigation_cell overview with diagram_links, boundary nodes.

Idempotency:
  - If _gen_id("diagram", 31) has v4 marker in metadata → already v4, skip
  - Otherwise → clear + reseed v4
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


def _icon(name: str) -> dict:
    """Build a Lucide icon ref."""
    return {"set": "lucide", "name": name}


def _node(
    nid: str,
    ntype: str,
    data: dict,
    x: int,
    y: int,
    w: int = 180,
    h: int = 80,
    icon: str | None = None,
    **extra: object,
) -> dict:
    """Build a positioned node dict with explicit size and optional icon."""
    result: dict = {
        "id": nid,
        "type": ntype,
        "position": {"x": x, "y": y},
        "data": data,
        "measured": {"width": w, "height": h},
    }
    if "visual" not in data:
        data["visual"] = {"width": w, "height": h}
    else:
        data["visual"]["width"] = w
        data["visual"]["height"] = h
    if icon:
        data["visual"]["icon"] = _icon(icon)
    result.update(extra)
    return result


def _edge(
    eid: str,
    source: str,
    target: str,
    etype: str,
    label: str,
    *,
    rel_id: str = "",
    source_handle: str | None = None,
    target_handle: str | None = None,
    **extra_data: object,
) -> dict:
    """Build an edge dict with explicit routing handles."""
    data: dict = {"relationshipType": etype, "label": label}
    if rel_id:
        data["relationshipId"] = rel_id
    data.update(extra_data)
    result: dict = {"id": eid, "source": source, "target": target, "type": etype, "data": data}
    if source_handle:
        result["sourceHandle"] = source_handle
    if target_handle:
        result["targetHandle"] = target_handle
    return result


def _boundary(nid: str, label: str, x: int, y: int, w: int, h: int) -> dict:
    """Build a boundary (group) node."""
    return {
        "id": nid,
        "type": "boundary",
        "position": {"x": x, "y": y},
        "data": {
            "label": label,
            "entityType": "boundary",
            "visual": {"width": w, "height": h},
        },
        "measured": {"width": w, "height": h},
        "zIndex": -1,
    }


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


# ── Diagram builder helpers ─────────────────────────────────────────────────

def _e(eids: dict, nid: str) -> dict:
    """Build entity data dict for a node referencing an element."""
    _, etype, name, desc, _ = next(e for e in _ENTITIES if e[0] == nid)
    return {"label": name, "entityType": etype,
            "description": desc, "entityId": eids.get(nid, "")}


def _r(rids: dict, idx: int) -> str:
    """Get relationship ID by index."""
    return rids.get(f"r{idx}", "")


def _ae(eids: dict, nid: str, layer: str, archimate_type: str) -> dict:
    """Build ArchiMate entity data with layer info."""
    return {**_e(eids, nid), "layer": layer, "archimateType": archimate_type}


# ── Simple Notation Diagrams (10, indices 0–9) ───────────────────────────────

def _build_simple_component(eids: dict, rids: dict, **_kw: object) -> dict:
    """Simple component: Iris Architecture — layered top-down layout."""
    nodes = [
        # Row 1: Actors
        _node("n10", "actor", _e(eids, "n10"), 100, 30, 140, 70, icon="user"),
        _node("n11", "actor", _e(eids, "n11"), 380, 30, 140, 70, icon="shield"),
        # Row 2: Frontend + API
        _node("n1", "component", _e(eids, "n1"), 60, 170, 200, 80, icon="monitor"),
        _node("n9", "interface", _e(eids, "n9"), 360, 170, 180, 80, icon="plug"),
        # Row 3: Backend services
        _node("n2", "component", _e(eids, "n2"), 200, 340, 200, 80, icon="server"),
        _node("n5", "component", _e(eids, "n5"), 10, 340, 170, 80, icon="pen-tool"),
        _node("n4", "service", _e(eids, "n4"), 440, 340, 160, 80, icon="lock"),
        # Row 4: Data
        _node("n3", "database", _e(eids, "n3"), 250, 510, 160, 70, icon="database"),
    ]
    edges = [
        _edge("e0", "n10", "n1", "uses", "Browses", rel_id=_r(rids, 0),
              source_handle="bottom", target_handle="top"),
        _edge("e1", "n11", "n9", "uses", "Manages", rel_id=_r(rids, 1),
              source_handle="bottom", target_handle="top"),
        _edge("e2", "n1", "n9", "uses", "API calls", rel_id=_r(rids, 2),
              source_handle="right", target_handle="left"),
        _edge("e3", "n9", "n2", "uses", "Serves", rel_id=_r(rids, 3),
              source_handle="bottom", target_handle="top"),
        _edge("e4", "n1", "n5", "uses", "Embeds", rel_id=_r(rids, 4),
              source_handle="bottom", target_handle="top"),
        _edge("e5", "n2", "n4", "uses", "Auth", rel_id=_r(rids, 7),
              source_handle="right", target_handle="left"),
        _edge("e6", "n2", "n3", "uses", "SQL", rel_id=_r(rids, 8),
              source_handle="bottom", target_handle="top"),
        _edge("e7", "n4", "n3", "uses", "Users", rel_id=_r(rids, 9),
              source_handle="bottom", target_handle="right"),
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
    """Simple deployment: Iris data infrastructure — hub-and-spoke layout."""
    nodes = [
        # Centre: Database hub
        _node("n3", "database", _e(eids, "n3"), 250, 220, 180, 80, icon="database"),
        # Spokes around the DB
        _node("n6", "service", _e(eids, "n6"), 30, 50, 180, 70, icon="search"),
        _node("n7", "service", _e(eids, "n7"), 490, 50, 180, 70, icon="file-text"),
        _node("n12", "component", _e(eids, "n12"), 30, 400, 180, 70, icon="git-branch"),
        _node("n8", "component", _e(eids, "n8"), 490, 400, 180, 70, icon="image"),
        _node("n13", "component", _e(eids, "n13"), 490, 220, 180, 70, icon="radio"),
    ]
    edges = [
        _edge("e0", "n6", "n3", "depends_on", "FTS5", rel_id=_r(rids, 14),
              source_handle="bottom", target_handle="top"),
        _edge("e1", "n7", "n13", "uses", "Events", rel_id=_r(rids, 15),
              source_handle="bottom", target_handle="top"),
        _edge("e2", "n13", "n3", "uses", "Persist", rel_id=_r(rids, 16),
              source_handle="left", target_handle="right"),
        _edge("e3", "n12", "n3", "uses", "Versions", rel_id=_r(rids, 13),
              source_handle="top", target_handle="bottom"),
        _edge("e4", "n8", "n3", "uses", "Read", rel_id=_r(rids, 17),
              source_handle="top", target_handle="bottom"),
    ]
    return {"nodes": nodes, "edges": edges}


def _build_simple_process(eids: dict, rids: dict, **_kw: object) -> dict:
    """Simple process: Diagram creation — left-to-right flow."""
    nodes = [
        _node("n10", "actor", _e(eids, "n10"), 0, 60, 130, 70),
        _node("n1", "component", _e(eids, "n1"), 200, 60, 170, 70),
        _node("n5", "component", _e(eids, "n5"), 440, 60, 170, 70),
        _node("n2", "component", _e(eids, "n2"), 680, 60, 170, 70),
        _node("n3", "database", _e(eids, "n3"), 920, 60, 140, 70),
    ]
    edges = [
        _edge("e0", "n10", "n1", "uses", "Opens app", rel_id=_r(rids, 0),
              source_handle="right", target_handle="left"),
        _edge("e1", "n1", "n5", "uses", "Opens canvas", rel_id=_r(rids, 4),
              source_handle="right", target_handle="left"),
        _edge("e2", "n5", "n2", "depends_on", "Save diagram", rel_id=_r(rids, 6),
              source_handle="right", target_handle="left"),
        _edge("e3", "n2", "n3", "uses", "Persist", rel_id=_r(rids, 8),
              source_handle="right", target_handle="left"),
    ]
    return {"nodes": nodes, "edges": edges}


def _build_simple_roadmap(eids: dict, rids: dict, **_kw: object) -> dict:
    """Simple roadmap: Iris product milestones — left-to-right timeline."""
    nodes = [
        _node("v1", "component", {"label": "v1.0 — Foundation", "entityType": "component",
              "description": "Core CRUD, authentication, canvas, and versioning"}, 0, 60, 200, 80),
        _node("v2", "component", {"label": "v2.0 — Multi-Notation", "entityType": "component",
              "description": "UML, ArchiMate, C4 support, import, sets, packages"}, 280, 60, 210, 80),
        _node("v3", "component", {"label": "v3.0 — Enterprise", "entityType": "component",
              "description": "Collaboration, real-time editing, cloud deployment"}, 570, 60, 200, 80),
        _node("v4", "component", {"label": "v4.0 — AI-Assisted", "entityType": "component",
              "description": "AI-powered diagram generation and analysis"}, 850, 60, 200, 80),
    ]
    edges = [
        _edge("e0", "v1", "v2", "uses", "Builds on",
              source_handle="right", target_handle="left"),
        _edge("e1", "v2", "v3", "uses", "Evolves to",
              source_handle="right", target_handle="left"),
        _edge("e2", "v3", "v4", "uses", "Evolves to",
              source_handle="right", target_handle="left"),
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
    cols, x_gap, y_gap = 4, 310, 200
    nodes = [
        _node(tid, "database",
              {"label": name, "entityType": "database", "description": desc},
              60 + (i % cols) * x_gap, 50 + (i // cols) * y_gap, 250, 70)
        for i, (tid, name, desc) in enumerate(tables)
    ]
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
        _edge(f"fk{i}", src, tgt, "depends_on", "FK",
              source_handle="bottom", target_handle="top")
        for i, (src, tgt) in enumerate(fk_edges)
    ]
    return {"nodes": nodes, "edges": edges}


def _build_simple_use_case(eids: dict, rids: dict, **_kw: object) -> dict:
    """Simple use_case: User interactions — actors left, use cases right."""
    nodes = [
        _node("n10", "actor", _e(eids, "n10"), 30, 60, 120, 70),
        _node("n11", "actor", _e(eids, "n11"), 30, 260, 120, 70),
        _node("uc1", "component", {"label": "Create Diagram", "entityType": "component",
              "description": "User creates a new diagram on the canvas"}, 300, 30, 200, 70),
        _node("uc2", "component", {"label": "Import Model", "entityType": "component",
              "description": "User imports a SparxEA .qea file"}, 300, 160, 200, 70),
        _node("uc3", "component", {"label": "Manage Users", "entityType": "component",
              "description": "Admin creates and manages user accounts"}, 300, 290, 200, 70),
    ]
    edges = [
        _edge("e0", "n10", "uc1", "uses", "Performs",
              source_handle="right", target_handle="left"),
        _edge("e1", "n10", "uc2", "uses", "Performs",
              source_handle="right", target_handle="left"),
        _edge("e2", "n11", "uc3", "uses", "Performs",
              source_handle="right", target_handle="left"),
        _edge("e3", "n11", "uc1", "uses", "Performs",
              source_handle="right", target_handle="left"),
    ]
    return {"nodes": nodes, "edges": edges}


def _build_simple_state_machine(eids: dict, rids: dict, **_kw: object) -> dict:
    """Simple state_machine: Diagram lifecycle — circular flow."""
    nodes = [
        _node("s1", "component", {"label": "Draft", "entityType": "component",
              "description": "Diagram is being created or edited"}, 60, 30, 160, 70),
        _node("s2", "component", {"label": "Published", "entityType": "component",
              "description": "Diagram is finalized and shared"}, 360, 30, 160, 70),
        _node("s3", "component", {"label": "Archived", "entityType": "component",
              "description": "Diagram is archived for reference"}, 360, 210, 160, 70),
        _node("s4", "component", {"label": "Deleted", "entityType": "component",
              "description": "Diagram is soft-deleted in recycle bin"}, 60, 210, 160, 70),
    ]
    edges = [
        _edge("e0", "s1", "s2", "uses", "Publish",
              source_handle="right", target_handle="left"),
        _edge("e1", "s2", "s3", "uses", "Archive",
              source_handle="bottom", target_handle="top"),
        _edge("e2", "s2", "s1", "uses", "Edit",
              source_handle="top", target_handle="top"),
        _edge("e3", "s3", "s4", "uses", "Delete",
              source_handle="left", target_handle="right"),
    ]
    return {"nodes": nodes, "edges": edges}


def _build_simple_system_context(eids: dict, rids: dict, **_kw: object) -> dict:
    """Simple system_context: Iris system boundary — centre-focused."""
    nodes = [
        _node("n10", "actor", _e(eids, "n10"), 30, 50, 130, 70, icon="user"),
        _node("n11", "actor", _e(eids, "n11"), 30, 250, 130, 70, icon="shield"),
        _node("sys", "component", {"label": "Iris Platform", "entityType": "component",
              "description": "Architecture modelling platform"}, 260, 130, 200, 100, icon="boxes"),
        _node("browser", "component", {"label": "Web Browser", "entityType": "component",
              "description": "Client-side rendering"}, 560, 50, 170, 70, icon="globe"),
        _node("sqlite", "database", {"label": "SQLite", "entityType": "database",
              "description": "Embedded database engine"}, 560, 250, 160, 70, icon="database"),
    ]
    edges = [
        _edge("e0", "n10", "sys", "uses", "Uses",
              source_handle="right", target_handle="left"),
        _edge("e1", "n11", "sys", "uses", "Administers",
              source_handle="right", target_handle="left"),
        _edge("e2", "sys", "browser", "uses", "Delivers to",
              source_handle="right", target_handle="left"),
        _edge("e3", "sys", "sqlite", "uses", "Persists in",
              source_handle="right", target_handle="left"),
    ]
    return {"nodes": nodes, "edges": edges}


def _build_simple_container(eids: dict, rids: dict, **_kw: object) -> dict:
    """Simple container: Iris container view — top-down 3-tier."""
    nodes = [
        _node("n1", "component", _e(eids, "n1"), 150, 30, 200, 80, icon="monitor"),
        _node("n5", "component", _e(eids, "n5"), 420, 30, 170, 80, icon="pen-tool"),
        _node("n2", "component", _e(eids, "n2"), 200, 200, 200, 80, icon="server"),
        _node("n4", "service", _e(eids, "n4"), 470, 200, 160, 80, icon="lock"),
        _node("n3", "database", _e(eids, "n3"), 250, 370, 160, 70, icon="database"),
    ]
    edges = [
        _edge("e0", "n1", "n2", "depends_on", "REST", rel_id=_r(rids, 6),
              source_handle="bottom", target_handle="top"),
        _edge("e1", "n2", "n3", "uses", "SQL", rel_id=_r(rids, 8),
              source_handle="bottom", target_handle="top"),
        _edge("e2", "n2", "n4", "uses", "Auth", rel_id=_r(rids, 7),
              source_handle="right", target_handle="left"),
        _edge("e3", "n1", "n5", "uses", "Embeds", rel_id=_r(rids, 4),
              source_handle="right", target_handle="left"),
    ]
    return {"nodes": nodes, "edges": edges}


# ── UML Notation Diagrams (8, indices 10–17) ─────────────────────────────────

def _build_uml_component(eids: dict, rids: dict, **_kw: object) -> dict:
    """UML component: Iris service modules — controller on top, services below."""
    nodes = [
        _node("u3", "class", _e(eids, "u3"), 200, 30, 200, 80),
        _node("u5", "interface_uml", _e(eids, "u5"), 30, 200, 180, 70),
        _node("u6", "interface_uml", _e(eids, "u6"), 30, 340, 180, 70),
        _node("u1", "class", _e(eids, "u1"), 300, 270, 200, 80),
        _node("u2", "class", _e(eids, "u2"), 560, 270, 200, 80),
    ]
    edges = [
        _edge("e0", "u3", "u1", "dependency", "Uses", rel_id=_r(rids, 22),
              source_handle="bottom", target_handle="top"),
        _edge("e1", "u3", "u2", "dependency", "Uses", rel_id=_r(rids, 23),
              source_handle="bottom", target_handle="top"),
        _edge("e2", "u5", "u1", "realization", "Renders", rel_id=_r(rids, 25),
              source_handle="right", target_handle="left"),
        _edge("e3", "u6", "u1", "realization", "Exports", rel_id=_r(rids, 26),
              source_handle="right", target_handle="left"),
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
    """UML class: Iris domain model — base class top, subclasses below, enum to side."""
    nodes = [
        # Base class centred at top
        _node("u7", "abstract_class", _e(eids, "u7"), 230, 30, 220, 80),
        # Subclasses fanned below
        _node("u1", "class", _e(eids, "u1"), 30, 230, 200, 80),
        _node("u2", "class", _e(eids, "u2"), 270, 230, 200, 80),
        _node("u4", "class", _e(eids, "u4"), 510, 230, 200, 80),
        # Enum to the right
        _node("u8", "enumeration", _e(eids, "u8"), 530, 30, 180, 80),
        # Controller below
        _node("u3", "class", _e(eids, "u3"), 150, 410, 200, 80),
    ]
    edges = [
        _edge("e0", "u1", "u7", "generalization", "Extends", rel_id=_r(rids, 20),
              source_handle="top", target_handle="bottom"),
        _edge("e1", "u2", "u7", "generalization", "Extends", rel_id=_r(rids, 21),
              source_handle="top", target_handle="bottom"),
        _edge("e2", "u4", "u7", "generalization", "Extends", rel_id=_r(rids, 24),
              source_handle="top", target_handle="bottom"),
        _edge("e3", "u1", "u8", "dependency", "Uses", rel_id=_r(rids, 27),
              source_handle="right", target_handle="bottom"),
        _edge("e4", "u3", "u1", "dependency", "Delegates", rel_id=_r(rids, 22),
              source_handle="top", target_handle="bottom"),
        _edge("e5", "u3", "u2", "dependency", "Delegates", rel_id=_r(rids, 23),
              source_handle="top", target_handle="bottom"),
    ]
    return {"nodes": nodes, "edges": edges}


def _build_uml_deployment(eids: dict, rids: dict, **_kw: object) -> dict:
    """UML deployment: Iris runtime — controller left, services right."""
    nodes = [
        _node("u3", "class", _e(eids, "u3"), 30, 100, 200, 80),
        _node("u1", "class", _e(eids, "u1"), 350, 30, 200, 80),
        _node("u2", "class", _e(eids, "u2"), 350, 200, 200, 80),
        _node("u4", "class", _e(eids, "u4"), 350, 370, 200, 80),
    ]
    edges = [
        _edge("e0", "u3", "u1", "dependency", "Delegates", rel_id=_r(rids, 22),
              source_handle="right", target_handle="left"),
        _edge("e1", "u3", "u2", "dependency", "Delegates", rel_id=_r(rids, 23),
              source_handle="right", target_handle="left"),
    ]
    return {"nodes": nodes, "edges": edges}


def _build_uml_process(eids: dict, rids: dict, **_kw: object) -> dict:
    """UML process: Edit workflow activity — left-to-right pipeline."""
    nodes = [
        _node("act1", "component", {"label": "Open Diagram", "entityType": "component",
              "description": "User opens an existing diagram for editing"}, 0, 60, 170, 70),
        _node("act2", "component", {"label": "Edit Canvas", "entityType": "component",
              "description": "User modifies nodes and edges on canvas"}, 240, 60, 170, 70),
        _node("act3", "component", {"label": "Validate", "entityType": "component",
              "description": "System validates diagram structure"}, 480, 60, 160, 70),
        _node("act4", "component", {"label": "Save Version", "entityType": "component",
              "description": "System persists new version to database"}, 710, 60, 170, 70),
        _node("act5", "component", {"label": "Generate Thumbnail", "entityType": "component",
              "description": "System regenerates SVG/PNG thumbnail"}, 950, 60, 190, 70),
    ]
    edges = [
        _edge("e0", "act1", "act2", "uses", "→",
              source_handle="right", target_handle="left"),
        _edge("e1", "act2", "act3", "uses", "→",
              source_handle="right", target_handle="left"),
        _edge("e2", "act3", "act4", "uses", "→",
              source_handle="right", target_handle="left"),
        _edge("e3", "act4", "act5", "uses", "→",
              source_handle="right", target_handle="left"),
    ]
    return {"nodes": nodes, "edges": edges}


def _build_uml_free_form(eids: dict, rids: dict, **_kw: object) -> dict:
    """UML free_form: Mix of UML elements — structured with boundary."""
    nodes = [
        _boundary("b1", "Iris Core Domain", 10, 10, 580, 350),
        _node("u7", "abstract_class", _e(eids, "u7"), 30, 50, 200, 80),
        _node("u1", "class", _e(eids, "u1"), 30, 210, 200, 80),
        _node("u5", "interface_uml", _e(eids, "u5"), 310, 50, 180, 70),
        _node("u8", "enumeration", _e(eids, "u8"), 310, 210, 180, 80),
        _node("u9", "use_case", _e(eids, "u9"), 200, 420, 200, 70),
    ]
    edges = [
        _edge("e0", "u1", "u7", "generalization", "Extends", rel_id=_r(rids, 20),
              source_handle="top", target_handle="bottom"),
        _edge("e1", "u5", "u1", "realization", "Renders", rel_id=_r(rids, 25),
              source_handle="bottom", target_handle="right"),
        _edge("e2", "u9", "u1", "association", "Invokes", rel_id=_r(rids, 28),
              source_handle="top", target_handle="bottom"),
    ]
    return {"nodes": nodes, "edges": edges}


def _build_uml_use_case(eids: dict, rids: dict, **_kw: object) -> dict:
    """UML use_case: Iris use cases — actors left, use cases right."""
    nodes = [
        _node("n10", "actor", _e(eids, "n10"), 30, 80, 120, 70),
        _node("n11", "actor", _e(eids, "n11"), 30, 300, 120, 70),
        _node("u9", "use_case", _e(eids, "u9"), 300, 40, 200, 70),
        _node("u10", "use_case", _e(eids, "u10"), 300, 170, 200, 70),
        _node("uc_export", "use_case", {"label": "Export Diagram", "entityType": "use_case",
              "description": "User exports diagram to SVG/PNG/PDF"}, 300, 300, 200, 70),
    ]
    edges = [
        _edge("e0", "n10", "u9", "association", "Performs",
              source_handle="right", target_handle="left"),
        _edge("e1", "n10", "u10", "association", "Performs",
              source_handle="right", target_handle="left"),
        _edge("e2", "n10", "uc_export", "association", "Performs",
              source_handle="right", target_handle="left"),
        _edge("e3", "n11", "u9", "association", "Performs",
              source_handle="right", target_handle="left"),
    ]
    return {"nodes": nodes, "edges": edges}


def _build_uml_state_machine(eids: dict, rids: dict, **_kw: object) -> dict:
    """UML state_machine: Element lifecycle — diamond flow."""
    nodes = [
        _node("u11", "state", _e(eids, "u11"), 60, 30, 170, 70),
        _node("u12", "state", _e(eids, "u12"), 370, 30, 170, 70),
        _node("s_versioned", "state", {"label": "Versioned", "entityType": "state",
              "description": "Element has multiple versions in history"}, 370, 210, 170, 70),
        _node("s_deleted", "state", {"label": "Deleted", "entityType": "state",
              "description": "Element is soft-deleted in recycle bin"}, 60, 210, 170, 70),
    ]
    edges = [
        _edge("e0", "u11", "u12", "uses", "Publish",
              source_handle="right", target_handle="left"),
        _edge("e1", "u12", "s_versioned", "uses", "Update",
              source_handle="bottom", target_handle="top"),
        _edge("e2", "s_versioned", "u11", "uses", "Edit",
              source_handle="left", target_handle="bottom"),
        _edge("e3", "s_versioned", "s_deleted", "uses", "Delete",
              source_handle="left", target_handle="right"),
    ]
    return {"nodes": nodes, "edges": edges}


# ── ArchiMate Notation Diagrams (7, indices 18–24) ───────────────────────────

def _build_archimate_component(eids: dict, rids: dict, **_kw: object) -> dict:
    """ArchiMate component: Iris enterprise view — layered top-down with boundaries."""
    nodes = [
        # Business layer
        _boundary("bl", "Business Layer", 20, 10, 640, 160),
        _node("a1", "business_actor", _ae(eids, "a1", "business", "Business Actor"), 40, 50, 180, 80),
        _node("a2", "business_role", _ae(eids, "a2", "business", "Business Role"), 270, 50, 180, 80),
        _node("a3", "business_process", _ae(eids, "a3", "business", "Business Process"), 500, 50, 180, 80),
        # Application layer
        _boundary("al", "Application Layer", 20, 210, 640, 160),
        _node("a5", "application_component", _ae(eids, "a5", "application", "Application Component"), 40, 250, 200, 80),
        _node("a6", "application_service", _ae(eids, "a6", "application", "Application Service"), 290, 250, 180, 80),
        _node("a7", "application_interface", _ae(eids, "a7", "application", "Application Interface"), 520, 250, 180, 80),
        # Technology layer
        _boundary("tl", "Technology Layer", 20, 410, 640, 140),
        _node("a9", "technology_node", _ae(eids, "a9", "technology", "Technology Node"), 40, 440, 180, 80),
        _node("a10", "technology_service", _ae(eids, "a10", "technology", "Technology Service"), 290, 440, 200, 80),
    ]
    edges = [
        _edge("e0", "a1", "a2", "assignment", "Fills", rel_id=_r(rids, 30),
              source_handle="right", target_handle="left"),
        _edge("e1", "a2", "a3", "assignment", "Performs", rel_id=_r(rids, 31),
              source_handle="right", target_handle="left"),
        _edge("e2", "a3", "a5", "serving", "Realizes", rel_id=_r(rids, 33),
              source_handle="bottom", target_handle="top"),
        _edge("e3", "a5", "a6", "archimate_composition", "Contains", rel_id=_r(rids, 34),
              source_handle="right", target_handle="left"),
        _edge("e4", "a5", "a7", "archimate_composition", "Exposes", rel_id=_r(rids, 35),
              source_handle="right", target_handle="left"),
        _edge("e5", "a9", "a5", "serving", "Hosts", rel_id=_r(rids, 37),
              source_handle="top", target_handle="bottom"),
        _edge("e6", "a9", "a10", "archimate_composition", "Provides", rel_id=_r(rids, 38),
              source_handle="right", target_handle="left"),
    ]
    return {"nodes": nodes, "edges": edges}


def _build_archimate_deployment(eids: dict, rids: dict, **_kw: object) -> dict:
    """ArchiMate deployment: Technology layer — layered."""
    nodes = [
        _node("a12", "technology_device", _ae(eids, "a12", "technology", "Technology Device"), 30, 30, 180, 80),
        _node("a5", "application_component", _ae(eids, "a5", "application", "Application Component"), 300, 30, 200, 80),
        _node("a9", "technology_node", _ae(eids, "a9", "technology", "Technology Node"), 30, 210, 180, 80),
        _node("a10", "technology_service", _ae(eids, "a10", "technology", "Technology Service"), 300, 210, 200, 80),
        _node("a11", "technology_artifact", _ae(eids, "a11", "technology", "Technology Artifact"), 580, 210, 180, 80),
    ]
    edges = [
        _edge("e0", "a12", "a5", "serving", "Renders", rel_id=_r(rids, 40),
              source_handle="right", target_handle="left"),
        _edge("e1", "a9", "a5", "serving", "Hosts", rel_id=_r(rids, 37),
              source_handle="top", target_handle="bottom"),
        _edge("e2", "a9", "a10", "archimate_composition", "Provides", rel_id=_r(rids, 38),
              source_handle="right", target_handle="left"),
        _edge("e3", "a10", "a11", "access", "Stores in", rel_id=_r(rids, 39),
              source_handle="right", target_handle="left"),
    ]
    return {"nodes": nodes, "edges": edges}


def _build_archimate_process(eids: dict, rids: dict, **_kw: object) -> dict:
    """ArchiMate process: Modeling business process — left-to-right flow."""
    nodes = [
        _node("a1", "business_actor", _ae(eids, "a1", "business", "Business Actor"), 0, 100, 180, 80),
        _node("a3", "business_process", _ae(eids, "a3", "business", "Business Process"), 260, 100, 200, 80),
        _node("a4", "business_service", _ae(eids, "a4", "business", "Business Service"), 540, 100, 180, 80),
        _node("a5", "application_component", _ae(eids, "a5", "application", "Application Component"), 400, 280, 200, 80),
        _node("a6", "application_service", _ae(eids, "a6", "application", "Application Service"), 140, 280, 180, 80),
    ]
    edges = [
        _edge("e0", "a1", "a3", "assignment", "Performs",
              source_handle="right", target_handle="left"),
        _edge("e1", "a3", "a4", "serving", "Realizes", rel_id=_r(rids, 32),
              source_handle="right", target_handle="left"),
        _edge("e2", "a4", "a5", "serving", "Provided by", rel_id=_r(rids, 33),
              source_handle="bottom", target_handle="top"),
        _edge("e3", "a5", "a6", "archimate_composition", "Contains", rel_id=_r(rids, 34),
              source_handle="left", target_handle="right"),
    ]
    return {"nodes": nodes, "edges": edges}


def _build_archimate_roadmap(eids: dict, rids: dict, **_kw: object) -> dict:
    """ArchiMate roadmap: Implementation phases — left-to-right timeline."""
    nodes = [
        _node("wp1", "component", {"label": "Foundation Phase", "entityType": "component",
              "layer": "implementation_migration", "archimateType": "Work Package",
              "description": "Core platform with auth, CRUD, canvas"}, 0, 60, 200, 80),
        _node("wp2", "component", {"label": "Multi-Notation Phase", "entityType": "component",
              "layer": "implementation_migration", "archimateType": "Work Package",
              "description": "UML, ArchiMate, C4 support, imports"}, 280, 60, 220, 80),
        _node("wp3", "component", {"label": "Enterprise Phase", "entityType": "component",
              "layer": "implementation_migration", "archimateType": "Work Package",
              "description": "Collaboration, locking, advanced views"}, 580, 60, 200, 80),
        _node("wp4", "component", {"label": "Target Architecture", "entityType": "component",
              "layer": "implementation_migration", "archimateType": "Plateau",
              "description": "Fully featured architecture platform"}, 860, 60, 210, 80),
    ]
    edges = [
        _edge("e0", "wp1", "wp2", "uses", "Enables",
              source_handle="right", target_handle="left"),
        _edge("e1", "wp2", "wp3", "uses", "Enables",
              source_handle="right", target_handle="left"),
        _edge("e2", "wp3", "wp4", "uses", "Delivers",
              source_handle="right", target_handle="left"),
    ]
    return {"nodes": nodes, "edges": edges}


def _build_archimate_free_form(eids: dict, rids: dict, **_kw: object) -> dict:
    """ArchiMate free_form: Cross-layer overview with boundaries."""
    nodes = [
        _boundary("bl", "Business", 10, 10, 300, 140),
        _node("a1", "business_actor", _ae(eids, "a1", "business", "Business Actor"), 30, 50, 180, 80),
        _node("a4", "business_service", _ae(eids, "a4", "business", "Business Service"), 30, 200, 180, 80),
        _boundary("al", "Application", 350, 10, 300, 320),
        _node("a5", "application_component", _ae(eids, "a5", "application", "Application Component"), 370, 50, 200, 80),
        _node("a8", "application_function", _ae(eids, "a8", "application", "Application Function"), 370, 200, 200, 80),
        _boundary("tl", "Technology", 10, 380, 640, 140),
        _node("a9", "technology_node", _ae(eids, "a9", "technology", "Technology Node"), 30, 420, 180, 80),
        _node("a11", "technology_artifact", _ae(eids, "a11", "technology", "Technology Artifact"), 370, 420, 180, 80),
    ]
    edges = [
        _edge("e0", "a1", "a4", "serving", "Uses",
              source_handle="bottom", target_handle="top"),
        _edge("e1", "a5", "a8", "archimate_composition", "Contains", rel_id=_r(rids, 36),
              source_handle="bottom", target_handle="top"),
        _edge("e2", "a9", "a5", "serving", "Hosts", rel_id=_r(rids, 37),
              source_handle="top", target_handle="bottom"),
    ]
    return {"nodes": nodes, "edges": edges}


def _build_archimate_motivation(eids: dict, rids: dict, **_kw: object) -> dict:
    """ArchiMate motivation: Stakeholder goals — top-down cascade."""
    nodes = [
        _node("a13", "stakeholder", _ae(eids, "a13", "motivation", "Stakeholder"), 200, 20, 200, 80),
        _node("a14", "driver", _ae(eids, "a14", "motivation", "Driver"), 50, 170, 210, 80),
        _node("a15", "goal", _ae(eids, "a15", "motivation", "Goal"), 350, 170, 200, 80),
        _node("a16", "requirement_archimate", _ae(eids, "a16", "motivation", "Requirement"), 200, 330, 220, 80),
        _node("a5", "application_component", _ae(eids, "a5", "application", "Application Component"), 200, 490, 200, 80),
    ]
    edges = [
        _edge("e0", "a13", "a14", "association", "Motivates", rel_id=_r(rids, 41),
              source_handle="bottom", target_handle="top"),
        _edge("e1", "a13", "a15", "association", "Drives",
              source_handle="bottom", target_handle="top"),
        _edge("e2", "a15", "a16", "association", "Requires",
              source_handle="bottom", target_handle="top"),
        _edge("e3", "a16", "a5", "serving", "Realized by",
              source_handle="bottom", target_handle="top"),
    ]
    return {"nodes": nodes, "edges": edges}


def _build_archimate_strategy(eids: dict, rids: dict, **_kw: object) -> dict:
    """ArchiMate strategy: Capabilities and resources — V layout."""
    nodes = [
        _node("vs", "component", {"label": "Architecture Governance", "entityType": "component",
              "layer": "strategy", "archimateType": "Value Stream",
              "description": "Value stream for enterprise architecture governance"}, 200, 20, 230, 80),
        _node("coa", "component", {"label": "Adopt Multi-Notation", "entityType": "component",
              "layer": "strategy", "archimateType": "Course of Action",
              "description": "Strategic course of action to adopt multi-notation modelling"}, 30, 190, 220, 80),
        _node("a17", "capability", _ae(eids, "a17", "strategy", "Capability"), 330, 190, 220, 80),
        _node("a18", "resource", _ae(eids, "a18", "strategy", "Resource"), 180, 370, 220, 80),
    ]
    edges = [
        _edge("e0", "vs", "coa", "association", "Includes",
              source_handle="bottom", target_handle="top"),
        _edge("e1", "coa", "a17", "serving", "Develops",
              source_handle="right", target_handle="left"),
        _edge("e2", "a17", "a18", "association", "Requires",
              source_handle="bottom", target_handle="top"),
    ]
    return {"nodes": nodes, "edges": edges}


# ── C4 Notation Diagrams (6, indices 25–30) ──────────────────────────────────

def _build_c4_component(eids: dict, rids: dict, **_kw: object) -> dict:
    """C4 component: Internal components of the backend — boundary grouping."""
    nodes = [
        _boundary("bb", "FastAPI Backend", 160, 10, 400, 340),
        _node("c6", "container", _e(eids, "c6"), 0, 100, 140, 80, icon="monitor"),
        _node("c7", "container", _e(eids, "c7"), 200, 50, 180, 80, icon="server"),
        _node("c9", "c4_component", _e(eids, "c9"), 200, 200, 170, 80, icon="lock"),
        _node("c10", "c4_component", _e(eids, "c10"), 410, 200, 170, 80, icon="pen-tool"),
        _node("c8", "container", _e(eids, "c8"), 600, 100, 170, 80, icon="database"),
    ]
    edges = [
        _edge("e0", "c6", "c7", "c4_relationship", "Calls API", rel_id=_r(rids, 46),
              source_handle="right", target_handle="left"),
        _edge("e1", "c7", "c9", "c4_relationship", "Contains", rel_id=_r(rids, 48),
              source_handle="bottom", target_handle="top"),
        _edge("e2", "c7", "c10", "c4_relationship", "Contains", rel_id=_r(rids, 49),
              source_handle="bottom", target_handle="top"),
        _edge("e3", "c7", "c8", "c4_relationship", "Reads/writes", rel_id=_r(rids, 47),
              source_handle="right", target_handle="left"),
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
    """C4 deployment: Production deployment — top-down 3-tier."""
    nodes = [
        _node("c3", "software_system", _e(eids, "c3"), 200, 20, 220, 90, icon="boxes"),
        _node("c6", "container", _e(eids, "c6"), 50, 200, 190, 80, icon="monitor"),
        _node("c7", "container", _e(eids, "c7"), 310, 200, 190, 80, icon="server"),
        _node("c8", "container", _e(eids, "c8"), 310, 370, 190, 80, icon="database"),
    ]
    edges = [
        _edge("e0", "c6", "c7", "c4_relationship", "Calls", rel_id=_r(rids, 46),
              source_handle="right", target_handle="left",
              technology="REST/HTTPS"),
        _edge("e1", "c7", "c8", "c4_relationship", "Reads/writes", rel_id=_r(rids, 47),
              source_handle="bottom", target_handle="top",
              technology="SQLite WAL"),
    ]
    return {"nodes": nodes, "edges": edges}


def _build_c4_free_form(eids: dict, rids: dict, **_kw: object) -> dict:
    """C4 free_form: Mix of all C4 levels — layered with persons on top."""
    nodes = [
        _node("c1", "person", _e(eids, "c1"), 50, 20, 150, 80, icon="user"),
        _node("c2", "person", _e(eids, "c2"), 300, 20, 150, 80, icon="shield"),
        _node("c3", "software_system", _e(eids, "c3"), 150, 180, 210, 90, icon="boxes"),
        _node("c6", "container", _e(eids, "c6"), 50, 360, 170, 80, icon="monitor"),
        _node("c9", "c4_component", _e(eids, "c9"), 300, 360, 170, 80, icon="lock"),
        _node("c10", "c4_component", _e(eids, "c10"), 300, 500, 170, 80, icon="pen-tool"),
    ]
    edges = [
        _edge("e0", "c1", "c3", "c4_relationship", "Uses", rel_id=_r(rids, 42),
              source_handle="bottom", target_handle="top"),
        _edge("e1", "c2", "c3", "c4_relationship", "Administers", rel_id=_r(rids, 43),
              source_handle="bottom", target_handle="top"),
        _edge("e2", "c6", "c9", "c4_relationship", "Uses",
              source_handle="right", target_handle="left"),
    ]
    return {"nodes": nodes, "edges": edges}


def _build_c4_system_context(eids: dict, rids: dict, **_kw: object) -> dict:
    """C4 system_context: Iris in its environment — centre-focused star."""
    nodes = [
        _node("c1", "person", _e(eids, "c1"), 30, 30, 150, 80, icon="user"),
        _node("c2", "person", _e(eids, "c2"), 30, 280, 150, 80, icon="shield"),
        _node("c3", "software_system", _e(eids, "c3"), 280, 140, 220, 100, icon="boxes"),
        _node("c4_ext_browser", "software_system_external",
              {**_e(eids, "c4_ext_browser"), "c4External": True}, 580, 30, 180, 80, icon="globe"),
        _node("c5", "software_system_external",
              {**_e(eids, "c5"), "c4External": True}, 580, 280, 180, 80, icon="database"),
    ]
    edges = [
        _edge("e0", "c1", "c3", "c4_relationship", "Uses", rel_id=_r(rids, 42),
              source_handle="right", target_handle="left",
              technology="HTTPS/REST"),
        _edge("e1", "c2", "c3", "c4_relationship", "Administers", rel_id=_r(rids, 43),
              source_handle="right", target_handle="left",
              technology="HTTPS/REST"),
        _edge("e2", "c3", "c4_ext_browser", "c4_relationship", "Delivers to", rel_id=_r(rids, 44),
              source_handle="right", target_handle="left",
              technology="HTML/CSS/JS"),
        _edge("e3", "c3", "c5", "c4_relationship", "Stores in", rel_id=_r(rids, 45),
              source_handle="right", target_handle="left",
              technology="SQLite WAL"),
    ]
    return {"nodes": nodes, "edges": edges}


def _build_c4_container(eids: dict, rids: dict, **_kw: object) -> dict:
    """C4 container: Container-level — person top, 3-tier below."""
    nodes = [
        _node("c1", "person", _e(eids, "c1"), 180, 20, 150, 80, icon="user"),
        _node("c6", "container", _e(eids, "c6"), 60, 180, 190, 80, icon="monitor"),
        _node("c7", "container", _e(eids, "c7"), 320, 180, 190, 80, icon="server"),
        _node("c8", "container", _e(eids, "c8"), 320, 350, 190, 80, icon="database"),
        _node("c5", "software_system_external",
              {**_e(eids, "c5"), "c4External": True}, 60, 350, 190, 80, icon="database"),
    ]
    edges = [
        _edge("e0", "c1", "c6", "c4_relationship", "Uses",
              source_handle="bottom", target_handle="top",
              technology="HTTPS"),
        _edge("e1", "c6", "c7", "c4_relationship", "Calls API", rel_id=_r(rids, 46),
              source_handle="right", target_handle="left",
              technology="REST"),
        _edge("e2", "c7", "c8", "c4_relationship", "Reads/writes", rel_id=_r(rids, 47),
              source_handle="bottom", target_handle="top",
              technology="SQLite"),
    ]
    return {"nodes": nodes, "edges": edges}


# ── Navigation Overview (index 31, root package) ─────────────────────────────

def _build_navigation_overview(
    eids: dict, rids: dict, mids: dict[int, str] | None = None,
) -> dict:
    """Root navigation diagram with navigation_cell tiles linking to each notation group."""
    mids = mids or {}
    # Navigation cells arranged in a 2×2 grid with a title note at top
    nodes = [
        _node("note1", "note", {
            "label": "Iris Architecture Examples",
            "entityType": "note",
            "description": "Click any tile below to explore diagrams in that notation. "
                           "Each group demonstrates Iris architecture using a different modelling standard.",
        }, 120, 10, 400, 70),
        # Row 1: Simple, UML
        _node("nav_simple", "navigation_cell", {
            "label": "Simple Notation",
            "entityType": "navigation_cell",
            "description": "10 diagrams using basic boxes-and-lines notation",
            "linkedModelId": mids.get(0, ""),
            "visual": {"width": 220, "height": 130,
                       "icon": {"set": "lucide", "name": "layout-grid"}},
        }, 50, 120, 220, 130),
        _node("nav_uml", "navigation_cell", {
            "label": "UML Notation",
            "entityType": "navigation_cell",
            "description": "8 diagrams using Unified Modeling Language",
            "linkedModelId": mids.get(10, ""),
            "visual": {"width": 220, "height": 130,
                       "icon": {"set": "lucide", "name": "git-merge"}},
        }, 370, 120, 220, 130),
        # Row 2: ArchiMate, C4
        _node("nav_archimate", "navigation_cell", {
            "label": "ArchiMate Notation",
            "entityType": "navigation_cell",
            "description": "7 diagrams using ArchiMate enterprise architecture notation",
            "linkedModelId": mids.get(18, ""),
            "visual": {"width": 220, "height": 130,
                       "icon": {"set": "lucide", "name": "building"}},
        }, 50, 310, 220, 130),
        _node("nav_c4", "navigation_cell", {
            "label": "C4 Notation",
            "entityType": "navigation_cell",
            "description": "6 diagrams using the C4 model (Context, Container, Component)",
            "linkedModelId": mids.get(29, ""),
            "visual": {"width": 220, "height": 130,
                       "icon": {"set": "lucide", "name": "layers"}},
        }, 370, 310, 220, 130),
        # Quick links to key diagrams
        _node("nav_schema", "navigation_cell", {
            "label": "Database Schema",
            "entityType": "navigation_cell",
            "description": "Complete database schema with all 20 tables",
            "linkedModelId": mids.get(5, ""),
            "visual": {"width": 200, "height": 100,
                       "icon": {"set": "lucide", "name": "database"}},
        }, 50, 500, 200, 100),
        _node("nav_class", "navigation_cell", {
            "label": "UML Domain Model",
            "entityType": "navigation_cell",
            "description": "Class diagram of Iris domain model",
            "linkedModelId": mids.get(12, ""),
            "visual": {"width": 200, "height": 100,
                       "icon": {"set": "lucide", "name": "boxes"}},
        }, 370, 500, 200, 100),
    ]
    return {"nodes": nodes, "edges": []}


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

    # ── Navigation Overview (pkg-0, index 31) ────────────────────────────────
    {"index": 31, "diagram_type": "component", "notation": "simple",
     "name": "Iris Navigation", "parent_package_index": 0,
     "description": "Root navigation diagram with click-through tiles to each notation group.",
     "builder": _build_navigation_overview, "tags": _DIAGRAM_TAGS},
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
    max_elements = max(len(_ENTITIES), 55)
    max_rels = max(len(_RELATIONSHIPS), 50)
    max_diagrams = max(len(_DIAGRAMS), 32)
    max_packages = max(len(_PACKAGES), 5)

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
        await db.execute("DELETE FROM diagram_links WHERE source_diagram_id = ? OR target_diagram_id = ?", (did, did))
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


_V4_MARKER = "seed_v4"


async def seed_example_models(db: aiosqlite.Connection) -> None:
    """Seed example elements, packages, and diagrams demonstrating Iris architecture.

    Idempotency:
      - If diagram-31 metadata contains 'seed_v4' → already v4, skip
      - Otherwise → clear + reseed v4
    """
    # --- Skip if initial setup not yet completed ------------------------------
    cursor = await db.execute(
        "SELECT COUNT(*) FROM users WHERE is_active = 1"
    )
    row = await cursor.fetchone()
    if not row or row[0] == 0:
        return

    # --- v4 idempotency check: diagram-31 has v4 marker in metadata ----
    overview_id = _gen_id("diagram", 31)
    cursor = await db.execute(
        "SELECT metadata FROM diagram_versions WHERE diagram_id = ? ORDER BY version DESC LIMIT 1",
        (overview_id,),
    )
    row = await cursor.fetchone()
    if row and row[0]:
        try:
            meta = json.loads(row[0])
            if meta.get("seed_version") == _V4_MARKER:
                return
        except (json.JSONDecodeError, TypeError):
            pass

    # --- Clear any existing seed data (v1/v2/v3/partial v4) ---------
    # Check if any seed data exists
    root_pkg_id = _gen_id("pkg", 0)
    cursor = await db.execute(
        "SELECT COUNT(*) FROM packages WHERE id = ?", (root_pkg_id,)
    )
    row = await cursor.fetchone()
    if row and row[0] > 0:
        await _clear_old_seed_data(db)

    # Also check for old v1 data
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

        # v4 marker in metadata for overview diagram
        metadata: dict[str, object] = {}
        if model_def["index"] == 31:
            metadata["seed_version"] = _V4_MARKER

        await db.execute(
            "INSERT INTO diagrams (id, diagram_type, set_id, current_version, "
            "created_at, created_by, updated_at, parent_package_id, notation) "
            "VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?)",
            (diagram_id, model_def["diagram_type"], _DEFAULT_SET_ID, now,
             _SYSTEM_USER_ID, now, parent_package_id, model_def["notation"]),
        )
        metadata_json = json.dumps(metadata) if metadata else None
        await db.execute(
            "INSERT INTO diagram_versions (diagram_id, version, name, description, "
            "data, metadata, change_type, created_at, created_by) "
            "VALUES (?, 1, ?, ?, ?, ?, 'create', ?, ?)",
            (diagram_id, model_def["name"], model_def["description"],
             diagram_data_json, metadata_json, now, _SYSTEM_USER_ID),
        )

        for tag in model_def["tags"]:
            await db.execute(
                "INSERT INTO diagram_tags (diagram_id, tag, created_at, created_by) "
                "VALUES (?, ?, ?, ?)",
                (diagram_id, tag, now, _SYSTEM_USER_ID),
            )

    # --- Create diagram_links for navigation cells ----------------------------
    # The overview diagram (index 31) links to primary diagrams in each notation
    overview_diag_id = diagram_id_map[31]
    nav_targets = [
        (0, "Simple Notation"),
        (10, "UML Notation"),
        (18, "ArchiMate Notation"),
        (29, "C4 Notation"),
        (5, "Database Schema"),
        (12, "UML Domain Model"),
    ]
    for target_idx, label in nav_targets:
        target_id = diagram_id_map.get(target_idx)
        if target_id:
            link_id = _gen_id("diagram_link", target_idx)
            await db.execute(
                "INSERT OR IGNORE INTO diagram_links "
                "(id, source_diagram_id, target_diagram_id, link_type, label, created_by) "
                "VALUES (?, ?, ?, 'navigation', ?, ?)",
                (link_id, overview_diag_id, target_id, label, _SYSTEM_USER_ID),
            )

    await db.commit()
