# ADR-019: Metadata and User Attribution Display

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-019 |
| **Initiative** | Metadata and User Attribution Display |
| **Proposed By** | Architecture Team |
| **Date** | 2026-02-28 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris entity and model detail pages, where created_by is stored as a UUID, updated_at is not displayed, and version history tables lack attribution of who made each change,

**facing** the need for users to understand who created or modified an entity or model and when the last modification occurred, which is essential for collaboration, accountability, and audit trail visibility in an architecture repository,

**we decided for** JOINing the users table in the entity and model service queries to resolve the created_by UUID to a human-readable username, and exposing this as a `created_by_username` field in API responses alongside the existing UUID fields,

**and neglected** resolving usernames on the frontend via a separate user lookup API call (which would require additional round-trips and caching complexity), and replacing the UUID fields entirely with usernames (which would break existing API contracts and lose the machine-readable identifier),

**to achieve** clear user attribution on detail pages and version history tables without breaking existing API consumers, with minimal query overhead from a single LEFT JOIN per query,

**accepting that** if a user account is deleted, the LEFT JOIN will return NULL and the frontend will fall back to displaying the raw UUID, and that the additional JOIN adds a marginal performance cost to detail page queries.

---

## Options Considered

### Option 1: JOIN Users Table in Backend Queries (Selected)

**Pros:**
- Single query resolves username — no additional API calls needed
- LEFT JOIN gracefully handles deleted users (returns NULL)
- Existing UUID fields preserved for backward compatibility
- Minimal performance impact — users table is small and indexed on primary key

**Cons:**
- Slightly more complex SQL queries
- New field added to API responses (additive, non-breaking)

### Option 2: Frontend User Lookup (Rejected)

**Pros:**
- No backend query changes needed
- Could cache user lookups across the session

**Cons:**
- Additional API round-trips per detail page load
- Requires frontend caching logic to avoid repeated lookups
- Race condition if user is deleted between page load and lookup

**Why rejected:** Adds unnecessary complexity and latency. The backend JOIN is simpler and more reliable.

### Option 3: Replace UUID with Username (Rejected)

**Pros:**
- Simpler API response (one field instead of two)

**Cons:**
- Breaking change to existing API consumers
- Loses machine-readable user identifier
- Cannot link to user profiles or perform programmatic lookups

**Why rejected:** Breaking change with no compensating benefit over the additive approach.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-02-28 | Accepted | Implement metadata display on detail pages | 6 months | 2026-08-28 |

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
| Depends On | ADR-005 | Entity and Model Versioning | Version history tables are extended with user attribution |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-019-A | Metadata Display | Technical Specification | [specs/SPEC-019-A-Metadata-Display.md](specs/SPEC-019-A-Metadata-Display.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
