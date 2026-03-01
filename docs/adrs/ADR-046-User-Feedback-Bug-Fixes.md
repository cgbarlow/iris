# ADR-046: User Feedback Bug Fixes

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-046 |
| **Initiative** | User Feedback Bug Fixes (WP-2, WP-6, WP-11, WP-13) |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-01 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** user feedback identifying four distinct UI and data bugs: gallery thumbnails being cropped and misaligned (WP-2), audit log entries displaying raw user_id GUIDs instead of human-readable usernames (WP-6), entity detail views missing their associated tags (WP-11), and edge connection handles lacking visual hover feedback making them hard to discover and target (WP-13),

**facing** the need to resolve these issues as a cohesive batch of quality-of-life fixes without introducing architectural changes or new components,

**we decided for** four targeted fixes: (WP-2) changing thumbnail CSS from `object-cover` to `object-contain` with flex centering to preserve aspect ratio and centre thumbnails in their grid cells; (WP-6) adding a `_resolve_username()` helper in the audit middleware that resolves user_id GUIDs to usernames via the users service before writing audit entries; (WP-11) adding a tag enrichment query to `get_entity()` in the entities service so that tags are included in the entity response; (WP-13) adding CSS rules for `.svelte-flow__handle:hover` and `.svelte-flow__edgeupdater` to provide visible highlight and scale effects on edge connection handles,

**and neglected** restructuring the gallery grid layout (over-engineered for a simple sizing fix), caching resolved usernames in the audit middleware (premature optimisation for current scale), returning tags via a separate API call from the frontend (unnecessary network overhead), and using custom handle components instead of CSS styling (adds component complexity for a purely visual enhancement),

**to achieve** correct thumbnail display in the gallery, human-readable audit log entries, complete entity data including tags in detail views, and discoverable edge handles with clear visual affordance on hover,

**accepting that** `_resolve_username()` adds one extra query per audit entry (acceptable at current scale), `object-contain` may leave whitespace around non-square thumbnails, and the edge handle CSS relies on @xyflow/svelte's internal class naming conventions which could change in future library updates.

---

## Options Considered

### Option 1: Targeted Per-Bug Fixes (Selected)

**Pros:**
- Minimal code change per fix, low regression risk
- Each fix is independently testable and deployable
- No architectural changes required
- Directly addresses reported user pain points

**Cons:**
- Four separate changes bundled in one work package requires careful testing
- CSS handle styling depends on @xyflow/svelte internal class names

**Why selected:** Each bug has a clear, isolated root cause with a straightforward fix; bundling them avoids ADR overhead for trivially scoped changes.

### Option 2: Individual ADRs Per Bug (Rejected)

**Pros:**
- Each fix gets dedicated traceability

**Cons:**
- Excessive documentation overhead for four small, self-contained fixes
- No architectural decisions involved

**Why rejected:** These are corrective fixes, not design decisions; a single grouped ADR provides sufficient traceability.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-03-01 | Accepted | Apply four targeted bug fixes | 6 months | 2026-09-01 |

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
| Depends On | ADR-007 | Audit Log Integrity | WP-6 username resolution enhances audit entries |
| Depends On | ADR-012 | Models Gallery View | WP-2 fixes gallery thumbnail sizing |
| Depends On | ADR-037 | Tag Management System | WP-11 fixes tag enrichment in entity queries |
| Depends On | ADR-026 | Canvas Four-Position Handles | WP-13 adds hover styles to edge handles |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
