# SPEC-086-A: Faithful UML Formatting

**ADR:** [ADR-086](../ADR-086-Faithful-UML-Rendering-Edit-Parity-Lock-Fix.md)

## Scope
This specification covers the rendering improvements, edit parity features, and lock integration described in ADR-086.

## Phase 1: Attributes on Canvas Nodes

### Backend Changes
- `service.py`: After building `node_data["visual"]`, look up element attributes by Object_ID and attach them to `node_data["attributes"]`
- `converter.py`: Add `format_uml_visibility(scope)` utility mapping Public->+, Private->-, Protected->#, Package->~, None->+

### Frontend Changes
- `UmlRenderer.svelte`: Prepend visibility prefix when rendering attribute objects with a scope field

## Phase 2: UML SVG Markers

### New Component
- `UmlMarkerDefs.svelte`: SVG `<defs>` block with four marker definitions (filled diamond, open diamond, closed triangle, open arrow)

### Modified Components
- `UnifiedCanvas.svelte`: Render `<UmlMarkerDefs />` inside `<SvelteFlow>`
- `UmlEdgeRenderer.svelte`: Derive `markerEnd`/`markerStart` from `relationshipType`, pass to `IrisBaseEdge`
- `BaseEdge.svelte`: Accept and forward `markerStart` prop to `FlowBaseEdge`

## Phase 3: Cardinality and Role Name Labels

### New Component
- `EdgeEndpointLabels.svelte`: Renders text labels near edge endpoints for cardinality and role names

### Modified Components
- `BaseEdge.svelte`: Render `EdgeEndpointLabels` when data contains cardinality/role fields, respecting ViewConfig toggles

## Phase 4: Edit Canvas Parity

### Modified Components
- `RelationshipDialog.svelte`: Add optional UML metadata fields (cardinality, roles, stereotype) when notation is 'uml'
- New `EdgeStylePanel.svelte`: Edge metadata editor (modeled after NodeStylePanel)

## Phase 5: Lock Integration

### Backend
- `router.py`: Add `POST /api/locks/{lock_id}/release` endpoint

### Frontend
- `+page.svelte`: Wire `createLockManager()` into edit flow with acquire/release/conflict banner
- `locks.svelte.ts`: Already has correct URL; backend endpoint is the missing piece

## Acceptance Criteria
1. Imported EA class nodes show attribute compartments with visibility prefixes
2. UML edges render with correct arrowheads per relationship type
3. Cardinality and role name labels appear at edge endpoints
4. Users can set cardinality, roles, and stereotype when creating/editing UML relationships
5. Edit mode acquires a lock; conflict banner shows when locked by another user
6. Lock appears in admin locks page during editing
7. Lock is released on save, discard, navigate away, or page close
