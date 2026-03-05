# SparxEA Packages in Iris — Gap Analysis & Recommendations

**Date:** 2026-03-04
**Context:** Research into how SparxEA packages are represented in Iris, using the AIXM 5.1.1 import set (`temp/AIXM_5.1.1_EA16.qea`) as reference.

---

## What a SparxEA Package Is

A package in SparxEA is a **hierarchical namespace container**. It holds:

- **Sub-packages** (nested tree, any depth)
- **Elements** (classes, interfaces, notes, boundaries, etc.)
- **Diagrams** (visual projections of contained elements)
- **Connectors** between packages (Dependency, Import, Merge, Nesting)
- **Metadata** (notes, stereotypes, tagged values, version, dates, scope)

In the AIXM 5.1.1 file: **68 packages**, up to 6 levels deep, containing 953 classes, 107 diagrams, 1420 connectors, and 4201 attributes.

### Dual Representation (Critical Concept)

Every package exists in **two tables simultaneously**:

| Table | Role |
|-------|------|
| `t_package` | Stores the package hierarchy (parent/child), package-specific metadata (version control, code paths, tree position) |
| `t_object` | Stores the package as a model element (with `Object_Type = 'Package'`), which carries stereotypes, status, tagged values, notes, and allows the package to appear on diagrams and participate in connectors |

The join between them: `t_object.PDATA1 = t_package.Package_ID` (for rows where `Object_Type = 'Package'`).

Tagged values for packages live in `t_objectproperties` linked via the `t_object` row — not in `t_taggedvalue`.

### Package Relationships

Packages can participate in several types of UML relationships (all stored in `t_connector`):

| Connector_Type | UML Meaning |
|----------------|-------------|
| `Dependency` | Package dependency (source depends on target) |
| `Usage` | Stronger form of dependency — source uses target |
| `Nesting` | Graphical containment notation (alternative to tree hierarchy) |
| `<<import>>` | Dependency with stereotype — imports target namespace |
| `<<merge>>` | Dependency with stereotype — merges element definitions |

AIXM 5.1.1 has **25 package-to-package dependency connectors**.

---

## What Iris Currently Does Well

| SparxEA Concept | Iris Mapping | Status |
|---|---|---|
| Package hierarchy (Parent_ID) | `models.parent_model_id` | Preserved |
| Package name | `model_versions.name` | Preserved |
| Package notes/description | `model_versions.description` | Preserved |
| Package Status/Stereotype | `model_versions.metadata` | Preserved |
| Package-to-Package connectors | `model_relationships` table | Preserved |
| Topological sort (parents before children) | `_topo_sort_packages()` | Correct |
| Diagrams as child models with canvas data | `model_versions.data` with nodes/edges | Working |
| Elements assigned to owning package | Entity created, linked to package model | Working |

### Import Pipeline Summary

```
SparxEA .qea file
├─ t_package (68 rows) → Iris models (hierarchy containers, data={})
├─ t_object (1026 rows)
│  ├─ Object_Type="Package" (67) → Used for Status/Stereotype metadata on models
│  ├─ Object_Type="Class" (953) → Iris entities (type="class")
│  ├─ Object_Type="Note" (5) → Iris entities (type="note")
│  └─ Object_Type="Boundary" (1) → Iris entities (type="boundary")
├─ t_connector (1420 rows)
│  ├─ Element-to-Element → Iris relationships
│  └─ Package-to-Package → Iris model_relationships
├─ t_diagram (107 rows) → Iris models with canvas data (nodes/edges)
└─ t_attribute (4201 rows) → Entity data.attributes (structured objects)
```

---

## What's Missing

### Data Gaps (things in the .qea we don't capture)

| Gap | Impact | AIXM 5.1.1 Example |
|---|---|---|
| **Package tagged values** | 19 values lost — XSD namespaces, version info, schema generation params | `XSD::targetNamespace = http://www.aixm.aero/schema/5.1.1` |
| **Package CreatedDate/ModifiedDate** | Timestamp lineage lost | Available in `t_package` but never read |
| **Package ea_guid** | Read but never stored — critical for re-import dedup | `{CD9A349B-FD8B-446e-82C3-EF61E9DA9A8F}` |
| **Package Scope** | 67/67 packages have it, not extracted | `Public`, `Private`, etc. |
| **Package Version** | 1/67 have it in AIXM, not extracted for those that do | Version string |
| **Connector stereotypes on package deps** | Import/Merge distinction lost — all stored as plain "dependency" | `<<import>>`, `<<merge>>` |

### Structural/UX Gaps

| Gap | Impact |
|---|---|
| **No import idempotency** | AIXM was imported **8 times** creating 8 duplicate trees (~1400 duplicate models). No way to detect "already imported" |
| **Packages are invisible on diagrams** | In SparxEA, packages appear as folder-like containers on diagrams. In Iris, they only exist in the hierarchy sidebar |
| **No import set isolation** | Each import creates models/entities loose in the DB with only `set_id` grouping. No single "delete this import" action |
| **Flat entity namespace** | Entities have no package-scoping. Two classes named "Feature" in different packages become two global entities with no namespace distinction |

### AIXM 5.1.1 Database Statistics

```
t_package     68 packages (6 levels deep)
t_object    1026 elements (953 Class, 67 Package, 5 Note, 1 Boundary)
t_connector 1420 connectors (25 package-to-package dependencies)
t_diagram    107 diagrams (106 Logical, 1 Package)
t_attribute 4201 attributes
```

Package tagged values found (19 total, on 3 packages):

```
AIXM Features        XSD::targetNamespacePrefix  = aixm
AIXM Features        XSD::targetNamespace         = http://www.aixm.aero/schema/5.1.1
AIXM Features        XSD::elementFormDefault      = qualified
AIXM Features        XSD::attributeFormDefault    = unqualified
AIXM Features        AIXM::generateFileName       = AIXM_Features.xsd
AIXM Features        AIXM::coreVersion            = 5.1.1
AIXM Data Types      XSD::targetNamespacePrefix  = aixm
AIXM Data Types      XSD::targetNamespace         = http://www.aixm.aero/schema/5.1.1
...
Basic Message        AIXM::extensionVersion       = 1.0
```

---

## Options — Aligned with North Star

The North Star says: *"Repository first, visualisation second"* and *"Simple by default, powerful when needed"*. The goal is to faithfully ingest SparxEA models while keeping Iris simple. SparxEA is complicated because of its UI, not its data. The data is well-structured — Iris needs to be a better lens for viewing it.

### Option A: Metadata Enrichment (Low effort, high value)

- Extract and store package tagged values, CreatedDate, ModifiedDate, Scope, and Version in model metadata
- Store `ea_guid` in model metadata for future reference
- Capture connector stereotypes (import/merge) on package dependencies
- Display tagged values in the Extended accordion group on model detail page (pattern already exists)
- **Why:** Completes the data fidelity story. No schema changes needed — just more metadata in existing JSON fields

### Option B: Import Idempotency & Cleanup (Medium effort, critical for usability)

- Store `ea_guid` as a first-class field or in metadata on models and entities
- On re-import of same .qea file: detect existing import via GUID matching, offer "update" vs "create new"
- Add "Delete import set" action that cleanly removes all models/entities from a specific import
- **Why:** Without this, every test import creates permanent duplicates. The DB currently has 8 copies of AIXM. This is the single biggest usability gap.

### Option C: Package Visual Representation (Higher effort, nice-to-have)

- On package diagrams, render child packages as folder/container nodes (similar to BoundaryNode but with a tab/folder visual)
- Allow navigating into a package by double-clicking its container node
- **Why:** Completes the visual story, but the hierarchy sidebar already provides navigation. This is a "powerful when needed" feature.

---

## Recommendation

**Do the naming rename + Option A + Option B together as a single release:**

1. **Naming rename** (Entity → Element, Model → Diagram, Package as first-class) — foundational. Every subsequent change builds on correct terminology. Do this first while user base is zero.
2. **Option A** (Metadata enrichment) — completes data fidelity. No metadata left behind on import.
3. **Option B** (Import idempotency) — makes imports safe to repeat and easy to clean up. Essential for a tool people actually use.
4. **Option C** (Package visual representation on canvas) — can wait. The hierarchy sidebar already covers package navigation.

The philosophy: *"Import everything SparxEA has, store it faithfully, display it simply."*

---

## Naming Proposal: Entity → Element, Model → Diagram, Package as First-Class Concept

### Problem

Iris currently uses terminology that drifts from industry standards and creates ambiguity:

| Current term | Problem |
|---|---|
| **Entity** | Carries ER-diagram connotations. A Note is not naturally an "entity". A Boundary is not an "entity". In UML, ArchiMate, and SparxEA, these are all **elements**. |
| **Model** | Overloaded. Used for both visual canvases (diagrams) and hierarchy containers (packages). In architecture, "the model" is the whole repository, not one view. The North Star already says *"Diagrams are projections of that underlying truth"* — the vision says "diagram", the code says "model". |
| No package concept | Packages (hierarchy containers with no canvas) are stored as models with `data={}`. Users see "models" in the sidebar that have no visual content. |

### Proposed Terminology

| Current | New | Rationale |
|---|---|---|
| Entity | **Element** | Standard UML/ArchiMate/SparxEA term. Captures all subtypes (class, interface, note, boundary, component, etc.) naturally. Every architect knows what an element is. |
| Model (with canvas data) | **Diagram** | Matches North Star language, SparxEA, UML, and ArchiMate. A diagram is a visual projection of elements. |
| Model (hierarchy container) | **Package** | Standard UML term. A package is an organisational namespace container. Separates structure from content. |
| Relationship | **Relationship** | Keep as-is — universal term. |

### What Changes

**Backend — Database Schema:**

The `models` table splits into two separate tables. The `entities` table renames. Elements and diagrams gain a `package_id` foreign key to establish package containment.

```
packages table (NEW — from models with no canvas data)
├─ id TEXT PRIMARY KEY
├─ parent_package_id TEXT → packages(id)   -- hierarchy (self-referencing)
├─ current_version INTEGER
├─ created_at, created_by, updated_at
├─ is_deleted INTEGER
└─ set_id TEXT → sets(id)

package_versions table (NEW — from model_versions for packages)
├─ package_id TEXT → packages(id)
├─ version INTEGER
├─ name TEXT
├─ description TEXT
├─ metadata TEXT (JSON: status, stereotype, tagged_values, ea_guid, scope, etc.)
├─ change_type, change_summary, rollback_to
└─ created_at, created_by

diagrams table (RENAMED from models — rows with canvas data)
├─ id TEXT PRIMARY KEY
├─ package_id TEXT → packages(id)          -- which package this diagram belongs to
├─ diagram_type TEXT (uml, sequence, archimate, simple)
├─ current_version INTEGER
├─ created_at, created_by, updated_at
├─ is_deleted INTEGER
└─ set_id TEXT → sets(id)

diagram_versions table (RENAMED from model_versions for diagrams)
├─ diagram_id TEXT → diagrams(id)
├─ version INTEGER
├─ name TEXT
├─ description TEXT
├─ data TEXT (JSON: nodes, edges — canvas content)
├─ metadata TEXT (JSON)
├─ change_type, change_summary, rollback_to
└─ created_at, created_by

elements table (RENAMED from entities)
├─ id TEXT PRIMARY KEY
├─ package_id TEXT → packages(id)          -- NEW: which package this element belongs to
├─ element_type TEXT
├─ current_version INTEGER
├─ created_at, created_by, updated_at
├─ is_deleted INTEGER
└─ set_id TEXT → sets(id)

element_versions table (RENAMED from entity_versions)
├─ element_id TEXT → elements(id)
├─ version, name, description, data, metadata
├─ change_type, change_summary, rollback_to
└─ created_at, created_by

package_relationships table (RENAMED from model_relationships)
├─ id TEXT PRIMARY KEY
├─ source_package_id TEXT → packages(id)
├─ target_package_id TEXT → packages(id)
├─ relationship_type TEXT
├─ label, description
└─ created_by, created_at
```

Key structural change: **everything belongs to a package**. Packages contain packages (hierarchy), diagrams (visual views), and elements (data). Foreign keys all point one direction — clean ownership.

**Backend — API Routes:**
- `/api/entities/` → `/api/elements/`
- `/api/models/` → `/api/diagrams/` + `/api/packages/`
- `/api/model-relationships/` → `/api/package-relationships/`
- All service, router, and module names updated to match

**Frontend:**
- All UI labels, page titles, navigation
- Route paths: `/entities/[id]` → `/elements/[id]`, `/models/[id]` → `/diagrams/[id]`, new `/packages/[id]`
- Component names, type definitions
- Dashboard cards: **Elements** and **Diagrams** (no Packages card)

**Timing:** The user base is zero. Doing this now is a clean break — every future ADR, doc, and conversation uses the right terms. Deferring lets wrong names calcify into the API, docs, and mental models.

### Package UI Design

**Dashboard:** Packages do **not** appear on dashboard cards. Two primary cards: **Elements** and **Diagrams**. Packages are organisational scaffolding, not content — you count the books, not the shelves.

**Hierarchy sidebar:** Shows packages (folder icons) and diagrams (canvas icons) as a tree. Elements are NOT shown in the sidebar — that would be thousands of items for large imports like AIXM. Elements are accessed via the package Contents tab or via search.

- **Create:** Extend the existing **+Child** button to offer "New Package" and "New Diagram" as options (dropdown). When viewing a package node in the tree, +Child creates a child inside it.
- **Rename:** Inline rename in the hierarchy tree (click on name, type, enter).
- **Move:** Drag-and-drop packages/diagrams between parent packages in the tree.
- **Delete:** Right-click or toolbar action with options: "Move contents up to parent" or "Delete package and all contents".

**Navigation:** Clicking a package in the hierarchy sidebar opens the package detail page. Clicking a diagram opens the canvas. The distinction is immediately clear from the visual cue (folder icon vs diagram icon).

**Package detail page — the primary interface for managing package contents:**

| Tab | Purpose |
|-----|---------|
| **Overview** | Package name, description, metadata accordion (Overview, Details, Extended). Same inline-edit pattern as elements and diagrams. |
| **Contents** | **The key tab.** File-manager-style view of everything inside this package. This is how users see and manage items within a package. |
| **Relationships** | Package-to-package relationships (dependencies, imports, merges). Same pattern as existing relationship management. |
| **Version History** | Version history of the package itself. |

**Contents tab — managing items inside a package:**

```
┌─────────────────────────────────────────────────────┐
│  Contents of: AIXM Features                         │
│                                                     │
│  [+ New ▾]  (dropdown: Package / Diagram / Element) │
│                                                     │
│  📁 Packages (12)                                   │
│  ├─ 📁 Aerial Refuelling                    [⋯]    │
│  ├─ 📁 AirportHeliport                      [⋯]    │
│  ├─ 📁 Airspace                              [⋯]    │
│  └─ ...                                             │
│                                                     │
│  📊 Diagrams (3)                                    │
│  ├─ 📊 Feature Overview                     [⋯]    │
│  ├─ 📊 Feature Relationships                [⋯]    │
│  └─ 📊 Feature Hierarchy                    [⋯]    │
│                                                     │
│  🔷 Elements (15)                                   │
│  ├─ 🔷 AIXMFeature «class»                  [⋯]    │
│  ├─ 🔷 AIXMObject «class»                   [⋯]    │
│  ├─ 🔷 FeatureMetadata «class»              [⋯]    │
│  └─ ...                                             │
└─────────────────────────────────────────────────────┘
```

- **Click** any item to navigate to its detail page (package, diagram, or element)
- **[⋯] menu** on each item: Move to another package, Remove from package, Delete
- **[+ New]** dropdown at top: creates a new package, diagram, or element inside this package
- **Search/filter** within contents for large packages
- Items grouped by type (packages first, then diagrams, then elements) with counts
- Each element shows its type as a badge (class, interface, note, etc.)

---

## Canvas Rendering Bugs & Edge Fidelity

### Bug 1: Elements rendered without boxes (text only)

**Symptom:** On some diagrams (e.g., `/models/a1aa482b`), class elements display as bare text without their styled box/container.

**Root cause: Node type registry mismatch between edit and browse modes.**

| Mode | Canvas component | Node registry | Has `class`? | Has `note`? | Has `boundary`? |
|------|-----------------|---------------|-------------|------------|----------------|
| Edit (UML) | `FullViewCanvas` | `umlNodeTypes` | YES | **NO** | **NO** |
| Browse | `BrowseCanvas` | `simpleViewNodeTypes` | **NO** | YES | YES |

The imported AIXM data has `type: "class"` on 953 nodes. In browse mode, `BrowseCanvas` uses `simpleViewNodeTypes` which does NOT register `class` — Svelte Flow falls back to a default renderer (bare text, no styled box). Conversely, `note` and `boundary` types are in the simple registry but NOT in the UML registry, so they fail in edit mode.

**Fix options:**

| Option | Description | Effort |
|--------|-------------|--------|
| **A: Unified registry (Recommended)** | Create a single merged registry that includes ALL node types from both simple and UML views. Use this for both edit and browse modes on UML/ArchiMate models. | Low |
| **B: BrowseCanvas mode-aware** | Make `BrowseCanvas` accept a `viewType` prop and select the correct registry per model type, same as `FullViewCanvas` does. | Low |
| **C: Add missing types to both** | Add `class` to `simpleViewNodeTypes`, add `note`/`boundary` to `umlNodeTypes`. | Low |

Recommendation: **Option A** — a single unified registry avoids this class of bug forever. Any new node type only needs to be registered once.

### Bug 2: Notes showing "Unknown" label instead of content

**Symptom:** On diagrams with Note elements (e.g., `/models/94e97e51`), notes display as "Unknown" with no content, instead of showing their rich HTML body.

**Root cause: Two import bugs.**

1. **Label "Unknown":** SparxEA Note elements have `Name=NULL` in `t_object`. The import falls back to a generic name but the canvas node gets `label: "Unknown"` instead of deriving a meaningful label from the Note content.

2. **Missing description in canvas data:** The import creates note nodes with `data: { label: "Unknown", entityType: "note", entityId: "..." }` — no `description` field. The entity DOES have the HTML content (e.g., `<b><u>Aeronautical Information Exchange Model</u></b>`), but it's not copied to the canvas node data at import time.

The `refreshNodeDescriptions()` function would fix this on load (it syncs entity name/description to node data), but the entity name is "Element 3" (also unhelpful) and the data was never saved back after refresh.

**Fix options:**

| Option | Description | Effort |
|--------|-------------|--------|
| **A: Fix import (Recommended)** | For Note/Boundary elements with `Name=NULL`, derive the label from the first line of `Note` content (stripped of HTML). Always populate `description` on canvas nodes from the entity's `Note` field. | Low |
| **B: Fix entity naming** | For Note elements, use a truncated version of the Note content as the entity name instead of "Element N". | Low |
| **C: NoteNode fallback** | Make `NoteNode` component fetch its own description from the entity if `description` is missing from canvas data. | Medium |

Recommendation: **A + B together** — fix the data at the source (import) rather than papering over it in the UI.

### Bug 3: Edges rendered differently from SparxEA

**Symptom:** Relationships/connectors in Iris look visually different from the same model in SparxEA. Missing arrows, no cardinality labels, wrong line routing, no role names.

**Root cause: The import reads only 7 of 79 `t_connector` columns and does not read `t_diagramlinks` at all.**

#### What SparxEA connectors have vs what Iris captures:

| Feature | In SparxEA | Read? | Stored? | Rendered? |
|---------|-----------|-------|---------|-----------|
| Connector type | `Connector_Type` | YES | YES | YES (selects component) |
| Label/name | `Name` | YES | YES | Simple view only, **NOT in UML view** |
| Direction arrows | `Direction`, `SourceIsNavigable`, `DestIsNavigable` | NO | NO | NO |
| Source cardinality | `SourceCard` (e.g., "0..1", "1..*") | NO | NO | NO |
| Target cardinality | `DestCard` | NO | NO | NO |
| Source role name | `SourceRole` (e.g., "curve", "segment") | NO | NO | NO |
| Target role name | `DestRole` | NO | NO | NO |
| Stereotype | `Stereotype` (e.g., `<<import>>`, `<<merge>>`) | NO | NO | NO |
| Line routing | `RouteStyle` (0=direct, 3=tree/orthogonal) | NO | NO | NO (defaults to bezier) |
| Line colour | `LineColor` | NO | NO | NO |
| Line style (dash) | `LineStyle` | NO | NO | NO |
| Arrow head style | `HeadStyle` | NO | NO | NO |
| Diagram placement | `t_diagramlinks.Geometry` (waypoints, label positions) | NO | NO | NO |
| Per-diagram visibility | `t_diagramlinks.Hidden` | NO | NO | NO |

AIXM statistics: 1420 connectors. 619 have explicit direction. 550+ associations have cardinality. 1417 use orthogonal routing (RouteStyle=3) but Iris renders bezier curves.

Additionally: UML edge components (`umlEdgeTypes`) do NOT render labels or use `EdgeLabel` — even when the import captures `Name`, it's invisible in UML view. The `markerEnd` prop is accepted by all edge components but nothing in the system ever sets it.

#### Fix: Full Edge Support from SparxEA

All connector metadata will be imported, stored, rendered, and exposed in the UI for user-created diagrams.

**Import (backend):**
- Extend `QeaConnector` dataclass to read: `Direction`, `SourceCard`, `DestCard`, `SourceRole`, `DestRole`, `Stereotype`, `RouteStyle`, `LineColor`, `LineStyle`, `HeadStyle`, `SourceIsNavigable`, `DestIsNavigable`, `SourceStyle`, `DestStyle`
- Read `t_diagramlinks` table: parse `Geometry` field for waypoints, label positions, edge attachment sides; respect `Hidden` flag to skip hidden connectors
- Store all metadata in relationship `data` JSON and canvas edge `data` JSON
- Map `RouteStyle` to Iris `routingType` (0=bezier, 3=step/orthogonal)

**Rendering (frontend):**
- All edge components render labels via `EdgeLabel` (already working in simple view, extend to UML/ArchiMate)
- Add UML-correct arrow markers: open arrow (dependency/usage), closed triangle (generalization), filled diamond (composition), open diamond (aggregation), no arrow (association)
- Render cardinality labels at source and target ends of edges (small text near connection points)
- Render role names alongside cardinality
- Display stereotype as `<<name>>` on the edge label
- Support orthogonal/step routing (infrastructure exists, just needs to be wired up)
- Respect line colour when set (override default theme colour)

**UI for user-created diagrams:**
- When creating a new edge, users can set: relationship type, label, direction, source/target cardinality, source/target role, stereotype, routing type
- Edge properties panel (click edge → sidebar or popover) for editing all fields after creation
- Edge type dropdown with UML-correct visual preview (solid, dashed, arrow styles)
- Cardinality and role name input fields at each end

**Priority order:** Import metadata → Labels on edges → Direction arrows → Cardinality/roles → Routing → Diagram links (stretch goal — exact waypoint reproduction is complex).

---

---

## Simple View Removal & Admin-Configurable Views

### Decision: Remove Simple View

The current codebase has two parallel canvas implementations:

| Canvas | Used for | Node registry | Edge registry | Features |
|--------|---------|---------------|---------------|----------|
| `ModelCanvas` (Simple View) | `model_type = "simple"`, `"component"`, `"roadmap"` | `simpleViewNodeTypes` (10 types) | `simpleViewEdgeTypes` (7 types) | Edge labels, routing type switching, `EdgeLabel` with drag/edit |
| `FullViewCanvas` (Full View) | `model_type = "uml"`, `"archimate"` | `umlNodeTypes` (11 types) / `archimateNodeTypes` | `umlEdgeTypes` (7 types) / `archimateEdgeTypes` | No edge labels, no routing switching, minimal edge components |
| `BrowseCanvas` (Browse Mode) | All model types in browse mode | `simpleViewNodeTypes` | `simpleViewEdgeTypes` | Read-only, browseMode flag, "View details" links |

**Problems with this split:**
1. Bug 1 exists precisely because of the registry mismatch between edit and browse
2. Simple View edge components have richer features (labels, routing) that Full View lacks
3. Maintaining two parallel implementations doubles the work for every new feature
4. The distinction between "simple" and "full" view is artificial — users want one good canvas

**Action: Remove Simple View entirely.** Consolidate to a single canvas implementation with Full View capabilities, enhanced with the best features from Simple View (edge labels, routing type switching). The node registry becomes a single unified registry containing ALL node types.

### Future: Admin-Configurable Views

"Simple by default, powerful when needed" will be reimplemented not as separate code paths, but as **admin-configurable visibility profiles** that filter the same underlying full-featured UI.

**Concept: Views**

A **View** is a named configuration that controls which UI elements, element types, relationship types, toolbar options, and visual features are visible to the user. Views don't change the data or capabilities — they filter the presentation.

```
┌─────────────────────────────────────────────────────┐
│  Admin Settings → Views                              │
│                                                      │
│  📋 Standard (Default)                       [Edit]  │
│     Hides: UML-specific types, stereotypes,          │
│     tagged values, cardinality, role names            │
│     Shows: class, interface, component, service,     │
│     basic relationship types, labels                 │
│                                                      │
│  📋 Advanced                                 [Edit]  │
│     Shows: Everything. All element types, all        │
│     relationship types, all metadata, all visual     │
│     features.                                        │
│                                                      │
│  📋 ArchiMate                                [Edit]  │
│     Shows: ArchiMate-specific element types and      │
│     relationship types. Hides UML-specific items.    │
│                                                      │
│  [+ New View]                                        │
└─────────────────────────────────────────────────────┘
```

**What a View controls:**

| Category | Examples of toggleable items |
|----------|----------------------------|
| **Element types** | class, interface, component, actor, use_case, state, activity, enumeration, abstract_class, note, boundary, etc. |
| **Relationship types** | association, dependency, generalization, composition, aggregation, realization, usage, etc. |
| **Edge features** | Cardinality display, role names, stereotypes on edges, direction arrows |
| **Node features** | Stereotype badges, tagged values in node, description display |
| **Toolbar options** | Which element/relationship types appear in the "Add" dropdowns |
| **Metadata sections** | Which accordion groups are visible (Overview, Details, Extended) |
| **Canvas features** | Orthogonal routing, grid snap, auto-layout |

**How it works:**
- Admin creates/edits Views in a settings page
- Each View is a JSON document listing enabled features, element types, and relationship types
- Users toggle between available Views via a dropdown in the top navigation (e.g., "Standard ▾")
- The active View filters all UI components — toolbar options, canvas palettes, detail page sections
- The underlying data is always full-fidelity. Views are cosmetic — they hide, never delete.
- Default: all new users start on "Standard" view. Power users switch to "Advanced".

**Implementation approach (future):**
- `views` table in DB: `id`, `name`, `description`, `config` (JSON), `is_default`, `created_by`
- Config JSON schema defines which features/types are enabled
- Frontend reads active View and filters component visibility via a global `$derived` store
- Admin page for CRUD on Views
- User preference stored in session/local storage for which View is active

**This is a future feature.** For now, the codebase operates in "Advanced" mode — everything visible, full functionality. The Views infrastructure will be built when the core platform is stable.

---

## Recommendation

**Implement the following as a single release:**

1. **Remove Simple View** — consolidate to one canvas with unified node/edge registries. Merge the best features of both (edge labels, routing from simple; full type coverage from UML).
2. **Bug 1 fix** — unified node registry resolves all type mismatches between edit and browse.
3. **Bug 2 fix** — fix Note/Boundary import to derive labels from content and always populate descriptions.
4. **Bug 3 fix** — full edge support: import all connector metadata, render labels/arrows/cardinality/roles, expose in UI for user-created diagrams.
5. **Naming rename** (Entity → Element, Model → Diagram, Package as first-class) — foundational terminology alignment.
6. **Package metadata enrichment** — tagged values, dates, GUID, scope.
7. **Import idempotency** — GUID-based re-import detection, "Delete import set" action.
8. **Option C** (Package visual representation on canvas) — can wait.
9. **Admin-Configurable Views** — future feature. For now, full functionality always visible.

The philosophy: *"Import everything SparxEA has, store it faithfully, display it simply."*

---

## References

- [Understanding Sparx EA Database Schema (NILUS)](https://www.nilus.be/blog_posts/sparx_ea_database_schema_guide.html)
- [Sparx EA Package Diagram User Guide](https://sparxsystems.com/enterprise_architect_user_guide/14.0/model_domains/packagediagram.html)
- [Package Merge (Sparx EA 16.0 Guide)](https://sparxsystems.com/enterprise_architect_user_guide/16.0/modeling_languages/pkgmerge.html)
- [EA Data Model (Sparx DE Blog)](https://blog.sparxsystems.de/en_GB/ea/ea-features/ea-model-search/enterprise-architect-datenmodell-ea-api/)
- [Inside Enterprise Architect by Thomas Kilian (Leanpub)](https://leanpub.com/InsideEA/read)
- Local: `docs/north-star.md`, `backend/app/import_sparx/`, `temp/AIXM_5.1.1_EA16.qea`
