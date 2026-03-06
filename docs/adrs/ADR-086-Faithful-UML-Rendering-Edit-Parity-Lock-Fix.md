# ADR-086: Faithful UML Rendering, Edit Parity, and Lock Integration

## Status
Accepted

## Context
Iris v2.3.0 solved colour and sizing fidelity for Sparx EA imports, but rendered diagrams still look fundamentally different from EA ground truth. Comparing the AIXM 5.1.1 "Diagram_Main" shows:
1. Class nodes without attribute compartments on the canvas
2. Edges without arrowheads or diamonds
3. Missing cardinality and role name labels at edge endpoints
4. No edit locking despite ADR-080 specifying it

This ADR addresses all three workstreams: faithful rendering, edit parity, and lock integration.

## Decision

### 1. Attributes on Canvas Nodes
Thread element attributes from the import into canvas node data. The `UmlRenderer` already supports attribute compartments — the data simply was not being passed through during diagram node construction.

Add `format_uml_visibility()` to convert EA Scope values (Public/Private/Protected/Package) to UML visibility prefixes (+/-/#/~).

### 2. UML SVG Markers (Arrowheads)
Create SVG `<marker>` definitions for the four standard UML line endings:
- Filled diamond (composition source)
- Open diamond (aggregation source)
- Closed triangle (generalization/realization target)
- Open arrow (dependency/usage target)

The `UmlEdgeRenderer` derives `markerStart`/`markerEnd` from `relationshipType` and passes them through `BaseEdge` to Svelte Flow's `<BaseEdge>`.

### 3. Cardinality and Role Name Labels
A new `EdgeEndpointLabels` component renders SVG text labels near edge endpoints. Labels are positioned with offsets along and perpendicular to the edge direction. Visibility is controlled by the ViewConfig toggles `show_cardinality` and `show_role_names`.

### 4. Edit Canvas Parity
Extend `RelationshipDialog` with optional UML fields (cardinality, roles, stereotype). Create `EdgeStylePanel` (modeled after `NodeStylePanel`) for editing edge metadata after creation.

### 5. Lock Integration Fix
The `createLockManager()` in `locks.svelte.ts` exists but is never called. Wire it into the diagram edit flow: acquire lock on edit, show conflict banner, heartbeat, auto-release on save/discard/navigate/close. Add POST release endpoint for `sendBeacon` compatibility.

## Consequences
- Imported EA diagrams render with attribute compartments, arrowheads, cardinality, and role names
- Users can create UML relationships with full metadata (cardinality, roles, stereotypes)
- Edit locking prevents concurrent editing conflicts per ADR-080 specification
- The POST release endpoint enables reliable lock cleanup on page close via sendBeacon

## Dependencies
- ADR-080 (Edit Locking)
- ADR-085 (Visual Overrides and Theme System)
