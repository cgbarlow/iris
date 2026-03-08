# ADR-089: Comprehensive EA Rendering Fidelity Audit

**Status:** Accepted
**Date:** 2026-03-07
**Extends:** ADR-088

## Context

ADR-088 fixed 10 specific rendering issues found in 2 AIXM diagrams. A comprehensive automated audit of all 149 diagrams (107 AIXM + 42 FIXM) revealed two systemic issues affecting the majority of diagrams:

1. **Missing edges (121 diagrams):** SvelteFlow handle IDs on nodes used `-src`/`-tgt` suffixes (e.g., `top-src`, `bottom-tgt`) while the backend import generated simple names (`top`, `bottom`, `left`, `right`). SvelteFlow silently drops edges when handle IDs don't match.

2. **Clipped node content (880 nodes across 139 diagrams):** Fixed-size nodes used hard `height: Npx` CSS with `overflow: hidden`, causing attributes/operations to be clipped when browser text metrics exceeded EA's exact dimensions.

## Decision

### Fix 1: Unified handle IDs
Align all node handle IDs to use simple position names (`top`, `bottom`, `left`, `right`) for both source and target handles. Each position gets two Handle elements (one source, one target) with the same ID. Applied to:
- UmlRenderer.svelte
- NoteNode.svelte
- BaseNode.svelte (used by SimpleRenderer, C4Renderer)
- BoundaryNode.svelte
- ArchimateRenderer.svelte

### Fix 2: min-height instead of fixed height
Changed `visualStyles.ts` to always use `min-height` for node heights instead of hard `height` when `fixedSize` is true. Width remains fixed for column alignment. Removed `overflow: hidden` from UmlRenderer's fixed-size style.

### Fix 3: Text truncation for fixed-width nodes
Added ellipsis CSS for labels, stereotypes, qualifiers, and attributes in `.uml-node--fixed` variant to gracefully handle long text in fixed-width containers.

## Consequences

- All 149 diagrams now render their edges correctly (0 missing edge issues)
- No node content is clipped (0 clipping issues)
- Long text in fixed-width nodes is truncated with ellipsis rather than hidden
- Handle naming is consistent: backend and frontend both use simple position names
