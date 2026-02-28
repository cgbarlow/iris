# ADR-023: Browse Mode Entity Navigation

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-023 |
| **Initiative** | Browse Mode Entity Panel Enhancement and Click-Through Navigation |
| **Proposed By** | Architecture Team |
| **Date** | 2026-02-28 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris browse mode where the EntityDetailPanel currently shows only minimal information (label, type, description, entity ID) with no way to navigate to the entity's detail page, see which other models reference the same entity, or drill down into a linked model,

**facing** user requests for richer entity context while browsing a model canvas — specifically: (a) a list of all models using the selected entity for cross-reference discovery, (b) a direct link to the entity's detail page for full inspection, and (c) a configurable "linked model" per entity node that enables drill-down navigation between related models,

**we decided for** enhancing the EntityDetailPanel with three navigation capabilities:

1. **"View Entity" link:** A direct link to `/entities/{entityId}` for full entity inspection.
2. **"Used In Models" list:** Fetches `GET /api/entities/{entityId}/models` and displays all models referencing the entity (excluding the current model) as navigable links.
3. **"Open Linked Model" button:** When `linkedModelId` is set on the canvas node data, a prominent button links to `/models/{linkedModelId}` for drill-down navigation.

**and neglected** opening entities/models in modals instead of navigating (loses URL shareability), pre-loading all entity cross-references on canvas mount (wasteful for large canvases), and implementing linked model configuration UI in this iteration (can be added later in entity node editing),

**to achieve** a browse-mode entity panel that serves as a navigation hub — enabling users to discover entity reuse across models, inspect entity details, and drill down into related models without leaving the natural browsing flow,

**accepting that** the "Used In Models" list requires an API call on each node selection (mitigated by the endpoint being lightweight), and the `linkedModelId` field must be set programmatically or via future node editing UI until a dedicated configuration interface is built.

---

## Options Considered

### Entity Navigation

#### Option 1: In-Panel Links and API Fetch (Selected)

**Pros:**
- Lightweight — fetches only when a node is selected
- Navigates via standard SvelteKit links (URL-shareable)
- Builds on existing `GET /api/entities/{entityId}/models` endpoint

**Cons:**
- Requires an API call per node selection

**Why selected:** The API endpoint already exists and is lightweight. Standard navigation preserves browser history and URL shareability.

#### Option 2: Modal-Based Entity/Model Viewer (Rejected)

**Pros:**
- Keeps user on the canvas page

**Cons:**
- Loses URL shareability
- Adds UI complexity (nested modals)
- Breaks standard navigation patterns

**Why rejected:** Modal-based navigation loses URL shareability and creates a non-standard UX pattern.

#### Option 3: Pre-Load All Cross-References (Rejected)

**Pros:**
- Instant display on node selection

**Cons:**
- Wasteful for large canvases (many entities, most never selected)
- Increases initial page load time

**Why rejected:** The overhead of pre-loading cross-references for all entities is disproportionate to the benefit.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-02-28 | Accepted | Implement entity panel enhancements | 6 months | 2026-08-28 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Architecture Team | 2026-02-28 |
| Accepted | Project Lead | 2026-02-28 |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-001 | Enhanced ADR Format | This ADR follows the enhanced WH(Y) format |
| Depends On | ADR-002 | Frontend Tech Stack | Uses Svelte 5 runes and SvelteKit navigation |
| Depends On | ADR-011 | Canvas Integration and Testing Strategy | Extends browse mode interactions |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-023-A | Browse Entity Panel | Technical Specification | [specs/SPEC-023-A-Browse-Entity-Panel.md](specs/SPEC-023-A-Browse-Entity-Panel.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
