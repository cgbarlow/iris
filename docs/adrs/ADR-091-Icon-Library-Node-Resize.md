# ADR-091: Icon Asset Library, Node Resizing & Icon Picker UI

**Status:** Accepted
**Date:** 2026-03-08
**Depends on:** ADR-068, ADR-085, ADR-086

## Context

Iris diagrams currently render nodes at fixed sizes determined by import data or defaults. Users
cannot resize nodes on the canvas in edit mode. Additionally, there is no icon system — imported
EA diagrams lose their element icons, and users creating new diagrams have no way to assign icons
to nodes.

A proper icon system needs to support multiple icon sets (ArchiMate notation icons, general-purpose
icons, and future custom sets) with a scalable architecture that avoids bundling thousands of
unused icons.

## Decision

Deliver this feature in three phases:

### Phase A: Node Resizing

Use SvelteFlow's built-in `NodeResizer` component to allow users to resize nodes in edit mode.
Persist the updated width/height to the node's visual override data. Browse mode remains
read-only — resizing handles are hidden.

### Phase B: Icon Infrastructure

Adopt **Lucide** as the primary general-purpose icon library:
- **ISC license** — permissive, no attribution requirement in UI
- **5,000+ icons** — broad coverage for architecture, infrastructure, and business concepts
- **Tree-shakable** — only referenced icons are bundled, keeping the frontend lean
- **Svelte 5 support** — first-class `lucide-svelte` package with runes compatibility

Implement a **multi-set icon architecture**:
- `lucide` — general-purpose icons via lucide-svelte
- `archimate` — ArchiMate notation icons (existing SVG assets)
- `custom` — user-uploaded icons (future phase, out of scope here)

During EA import, apply **semantic matching** to map EA element stereotypes and types to
appropriate Lucide icons (e.g., `«ApplicationComponent»` → `app-window`,
`«Node»` → `server`). Store the icon reference as `{ set: "lucide", name: "server" }` in
the node's visual data.

### Phase C: Icon Picker UI

Provide an icon picker panel accessible from the node context menu or properties panel in edit
mode. The picker supports:
- Search/filter across all available icon sets
- Category browsing within each set
- Preview at the node's current size
- Clear icon (remove assignment)

## Consequences

- Nodes become resizable in edit mode, improving layout flexibility.
- Imported EA diagrams gain meaningful icons via semantic matching.
- Users can manually assign or change icons on any node.
- Lucide dependency adds ~20 KB gzipped for typical usage due to tree-shaking.
- The multi-set architecture supports future icon sources without refactoring.
