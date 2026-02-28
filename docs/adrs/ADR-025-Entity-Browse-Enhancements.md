# ADR-025: Entity Browse Enhancements

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-025 |
| **Initiative** | Entity Browse Improvements with Grouping, Tags, and Enriched Cards |
| **Proposed By** | Architecture Team |
| **Date** | 2026-02-28 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris entities list page, which currently provides a flat list of entities with basic search, type filter, and sort controls but no way to organise entities by tags, group them visually, or see relationship and model usage statistics at a glance,

**facing** the need for architects to quickly browse and triage large numbers of entities by grouping them logically (by type, by tag), tagging entities for cross-cutting categorisation, and seeing enriched information (relationship count, model usage count) directly in the entity cards without navigating to each detail page,

**we decided for** adding a backend entity tags system (new `entity_tags` table with REST endpoints for add, remove, and list), enriching the entity list API response with tags and statistics, and enhancing the frontend entities page with a grouping mode dropdown (none, by type, by tag), collapsible group sections, tag badges on entity cards, and relationship/model usage counts,

**and neglected** implementing a full-featured tag management page (premature for the current number of entities), adding tag-based search/filtering as a separate mechanism (the existing search and grouping covers the use case), and building a drag-and-drop entity organisation interface (complexity not justified by current user needs),

**to achieve** a richer entity browsing experience where architects can group entities by type or tag, see at-a-glance statistics about each entity's connections, and manage lightweight tags for cross-cutting categorisation without leaving the entities list page,

**accepting that** tags are simple strings (no hierarchy or colour), grouping preferences are stored per-browser in localStorage (not per-user on the server), and the enrichment queries add N+1 database calls to the list endpoint (acceptable for the current entity count ceiling of ~100 entities per page).

---

## Options Considered

### Option 1: Tags + Grouping + Enriched Cards (Selected)

**Pros:**
- Tags provide flexible cross-cutting categorisation
- Grouping modes reduce cognitive load when browsing many entities
- Enriched cards eliminate the need to open each entity for basic stats
- Minimal backend complexity (single new table, three endpoints)

**Cons:**
- N+1 queries for enrichment (mitigated by small page sizes)
- localStorage grouping preferences are per-browser

### Option 2: Server-Side Grouping Only (Rejected)

**Pros:**
- Single query, no N+1 issue

**Cons:**
- Requires API changes for every new grouping mode
- Less flexible than client-side grouping of already-fetched data

**Why rejected:** Client-side grouping is simpler and more flexible for the current data volumes.

### Option 3: Full Tag Management UI (Rejected)

**Pros:**
- Complete tag CRUD with colour, description, hierarchy

**Cons:**
- Significant additional UI complexity
- Over-engineered for current use case

**Why rejected:** Simple string tags with add/remove are sufficient. A full tag management UI can be added later if needed.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-02-28 | Accepted | Implement entity browse enhancements | 6 months | 2026-08-28 |

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
| Depends On | ADR-002 | Frontend Tech Stack | Uses Svelte 5 runes and Tailwind CSS |
| Depends On | ADR-006 | Version Control Rollback Semantics | Entity versioning model |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-025-A | Entity Browse Enhancements | Technical Specification | [specs/SPEC-025-A-Entity-Browse.md](specs/SPEC-025-A-Entity-Browse.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
