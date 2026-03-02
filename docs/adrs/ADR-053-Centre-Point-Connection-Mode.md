# ADR-053: Centre-Point Connection Mode

## Proposal: Centre-Point Connector Handle for All Canvas Node Types

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-053 |
| **Initiative** | Centre-Point Connection Mode |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-01 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris canvas editor, where users create connections between nodes using top/bottom/left/right handles positioned at cardinal points on the node boundary,

**facing** the limitation that diagonal or arbitrary-angle connections always route via cardinal handles, creating visual clutter with forced right-angle paths when a simple straight centre-to-centre line would be clearer,

**we decided for** adding a fifth invisible centre-point handle (type="source", id="center") to every node component, positioned at the geometric centre via CSS override, that becomes visible on hover with an enlarged hit area,

**and neglected** adding a toolbar toggle for "centre mode" (unnecessary complexity — users can simply choose which handle to drag from), and replacing all handles with a single centre handle (would remove cardinal connection capability),

**to achieve** straight centre-to-centre connections alongside existing cardinal connections, giving users full freedom in connection routing without any mode switching,

**accepting that** the centre handle overlaps with node content and must be invisible by default to avoid visual noise, and that ConnectionMode.Loose (already configured) is required for source-to-source connections.

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Relates To | ADR-011 | Canvas Integration and Testing Strategy | Node component architecture |
| Relates To | ADR-042 | Connector Manipulation | Edge routing types |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-053-A | Centre-Point Handle Implementation | Technical Specification | [specs/SPEC-053-A-Centre-Point-Handle.md](./specs/SPEC-053-A-Centre-Point-Handle.md) |

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Architecture Team | 2026-03-01 | Approved | Implementation | 6 months | 2026-09-01 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Approved | Architecture Team | 2026-03-01 |
