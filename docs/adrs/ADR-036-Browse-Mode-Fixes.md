# ADR-036: Browse Mode Fixes

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-036 |
| **Initiative** | Browse Mode — Used In Models Fix and Node Navigation |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-01 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris browse mode EntityDetailPanel where the "Used In Models" list filters out the current model via `{#if model.model_id !== currentModelId}`, causing the list to appear empty when an entity is only used in the current model, and where canvas entity nodes in browse mode have no hover-based navigation affordance to let users quickly navigate to the entity detail page,

**facing** the need for (a) accurate cross-reference information that shows all models an entity belongs to — including the current one — so users can confirm the entity is in use, and (b) a discoverable, low-friction way to navigate from a canvas node directly to the entity detail page without first opening the side panel,

**we decided for** two changes:

1. **Used In Models fix:** Remove the `{#if model.model_id !== currentModelId}` filter and instead display all models returned by the API. The current model is annotated with a "(current)" label so users can distinguish it from other models. The empty-state message is updated from "Not used in any other models" to "Not used in any models" since the list now includes the current model.
2. **Browse mode node navigation overlay:** Pass a `browseMode` flag through SvelteFlow node data. When `browseMode` is true and the node has an `entityId`, each canvas node renders an absolute-positioned `<a>` element linking to `/entities/{entityId}` that appears on CSS `:hover`, providing direct navigation without requiring the side panel.

**and neglected** keeping the current-model filter and adding a separate "This model" indicator outside the list (inconsistent UX), implementing navigation via JavaScript click handlers instead of native `<a>` elements (loses right-click/open-in-new-tab, hurts accessibility), and adding a permanent visible navigation button on every node (visual clutter on dense diagrams),

**to achieve** a browse mode where users can always see the complete list of models using an entity — including the current model clearly marked — and can hover over any entity node to access a direct link to the entity detail page, improving both information completeness and navigation efficiency,

**accepting that** the hover overlay is not discoverable on touch-only devices (mitigated by the existing "View Entity" link in the side panel), and that the "(current)" label adds minor visual noise to the model list.

---

## Options Considered

### Used In Models

#### Option 1: Show All Models with "(current)" Label (Selected)

**Pros:**
- Users always see the complete picture of entity usage
- The "(current)" annotation provides context without removing information
- Simple implementation — remove the filter, add a conditional label

**Cons:**
- Slightly more visual noise with the "(current)" label

**Why selected:** Information completeness is more important than brevity. Users need to confirm an entity is used in a model, even when that model is the one they are currently viewing.

#### Option 2: Keep Filter, Add Separate "This Model" Indicator (Rejected)

**Pros:**
- Keeps the model list focused on "other" models

**Cons:**
- Inconsistent — the entity is in the current model but not shown in the "Used In Models" list
- Requires a separate UI element to convey the same information

**Why rejected:** Splitting the information across two UI patterns is confusing and less maintainable.

### Browse Mode Navigation

#### Option 1: CSS Hover Overlay with `<a>` Element (Selected)

**Pros:**
- Native link semantics (right-click, open in new tab, screen reader accessible)
- No JavaScript needed for navigation
- Clean appearance — only visible on hover, not cluttering the canvas

**Cons:**
- Not discoverable on touch-only devices (mitigated by side panel)

**Why selected:** Leverages native browser capabilities and maintains accessibility. The side panel already provides touch-friendly navigation.

#### Option 2: JavaScript Click Handler Navigation (Rejected)

**Pros:**
- Works identically on touch and mouse

**Cons:**
- Loses native link behaviour (right-click, open in new tab, middle-click)
- Requires `goto()` call which is less accessible than a native `<a>`

**Why rejected:** Native `<a>` elements provide better accessibility and browser integration than programmatic navigation.

#### Option 3: Permanent Visible Navigation Button (Rejected)

**Pros:**
- Always visible and discoverable

**Cons:**
- Adds visual clutter to every node on the canvas
- Dense diagrams become harder to read

**Why rejected:** Visual noise outweighs discoverability benefits, especially given that the side panel already provides navigation.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-03-01 | Accepted | Implement browse mode fixes | 6 months | 2026-09-01 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Architecture Team | 2026-03-01 |
| Accepted | Project Lead | 2026-03-01 |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-001 | Enhanced ADR Format | This ADR follows the enhanced WH(Y) format |
| Depends On | ADR-023 | Browse Mode Entity Navigation | Fixes bugs in the entity navigation panel |
| Depends On | ADR-011 | Canvas Integration and Testing Strategy | Browse mode canvas integration |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-036-A | Browse Mode Fixes Implementation | Technical Specification | [specs/SPEC-036-A-Browse-Mode-Fixes.md](specs/SPEC-036-A-Browse-Mode-Fixes.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
