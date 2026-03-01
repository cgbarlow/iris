# ADR-034: GUID to Username Resolution

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-034 |
| **Initiative** | GUID to Username Resolution |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-01 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris entity detail, model detail, and relationships views, where Created By displays a raw GUID instead of a human-readable username, version history User columns also display GUIDs, and the Relationships tab shows entity GUIDs instead of entity names for source and target,

**facing** the need for users to quickly identify who created a resource and which entities participate in a relationship without having to manually look up GUIDs, which is essential for usability, collaboration, and architectural review workflows,

**we decided for** completing the GUID-to-username resolution by adding `created_by_username` to the Pydantic response schemas for entities, models, and their versions (which the service layer already returns but Pydantic was stripping), and JOINing the entities table in the relationship list query to resolve `source_entity_name` and `target_entity_name`,

**and neglected** resolving entity names on the frontend via separate API calls per relationship (which would cause N+1 request patterns and degrade performance), and embedding entity name snapshots directly into the relationships table (which would create stale data if entity names change),

**to achieve** a complete, consistent user experience where all human-readable identifiers are resolved server-side and returned in API responses with zero additional round-trips, building on the pattern established in ADR-019,

**accepting that** entity names in relationship responses reflect the current entity version (not the name at relationship creation time), and that if an entity is deleted the name will fall back to an empty string.

---

## Options Considered

### Option 1: Add Fields to Pydantic Schemas + JOIN in Relationship Query (Selected)

**Pros:**
- Single query resolves all names — no additional API calls needed
- Consistent with existing ADR-019 pattern for `created_by_username`
- Entity names always reflect current version (no stale data)
- Additive, non-breaking API change

**Cons:**
- Slightly more complex relationship list query with additional JOINs
- Entity names reflect current state, not historical state at relationship creation

### Option 2: Frontend Entity Name Resolution (Rejected)

**Pros:**
- No backend query changes needed
- Could cache entity lookups in frontend

**Cons:**
- N+1 API call pattern for relationship lists (one lookup per unique entity ID)
- Requires frontend caching logic and loading states per entity name
- Poor user experience with names loading asynchronously

**Why rejected:** Unacceptable performance characteristics and UX degradation for relationship-heavy entities.

### Option 3: Denormalize Entity Names into Relationships Table (Rejected)

**Pros:**
- Fast queries — no JOINs needed
- Historical accuracy — preserves name at time of relationship creation

**Cons:**
- Data staleness — renamed entities show old names in relationships
- Requires update triggers or background sync to keep names current
- Additional storage overhead and migration complexity

**Why rejected:** Stale data problem outweighs the query simplicity benefit. The JOIN approach always returns current names.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-03-01 | Accepted | Implement GUID resolution across all response schemas | 6 months | 2026-09-01 |

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
| Extends | ADR-019 | Metadata and User Attribution Display | Completes the GUID resolution work started in ADR-019 |
| Depends On | ADR-001 | Enhanced ADR Format | This ADR follows the enhanced WH(Y) format |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-034-A | GUID Username Resolution | Technical Specification | [specs/SPEC-034-A-GUID-Username-Resolution.md](specs/SPEC-034-A-GUID-Username-Resolution.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
