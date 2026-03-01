# ADR-031: Admin Settings Header Link

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-031 |
| **Initiative** | Admin Settings Header Navigation |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-01 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris application where the admin settings page (`/admin/settings`) is only reachable through the sidebar's Admin section, requiring users to have the sidebar open and to scroll down past the main navigation items to find it,

**facing** the need for administrators to have quick, persistent access to admin settings regardless of sidebar state — particularly since settings affect system-wide behaviour (session timeout, gallery thumbnail mode) and are a common admin task,

**we decided for** adding a "Settings" link in the application header (the top bar `flex items-center gap-4` area), placed immediately before the existing "Help" link, conditionally rendered only when the current user's role is `admin`, using the same anchor styling pattern as the existing Help link,

**and neglected** adding a gear icon button without text (reduces discoverability and accessibility), placing the link after Help or Sign out (disrupts the existing layout flow where Help is the first link in the right-side group), and adding a dropdown menu for admin links (over-engineering for a single additional link),

**to achieve** immediate, one-click access to admin settings from any page regardless of sidebar state, improving admin workflow efficiency while maintaining a clean header for non-admin users who should not see administrative navigation,

**accepting that** this adds one more element to the header for admin users, and that admin settings is also accessible from the sidebar (intentional redundancy for discoverability).

---

## Options Considered

### Option 1: Header Link Before Help (Selected)

**Pros:**
- Consistent with existing header link pattern (same styling as Help link)
- Always visible regardless of sidebar state
- Minimal visual impact — one additional text link for admin users only
- Follows natural reading order: Settings, Help, username, Sign out

**Cons:**
- Slight header width increase for admin users
- Duplicates sidebar navigation path

**Why selected:** Simplest solution with maximum discoverability, consistent with existing patterns, and minimal implementation cost.

### Option 2: Gear Icon Button (Rejected)

**Pros:**
- Compact, minimal header space usage
- Common UI convention for settings

**Cons:**
- Less accessible — icon-only buttons require additional ARIA labelling and are harder to discover
- Inconsistent with the text-based Help link pattern

**Why rejected:** Introduces a different navigation pattern from the existing Help link, reducing consistency.

### Option 3: Admin Dropdown Menu (Rejected)

**Pros:**
- Could house multiple admin links (Users, Audit, Settings)
- Compact header footprint

**Cons:**
- Over-engineering for a single link
- Adds click cost (open menu, then click)
- Introduces a new interaction pattern not used elsewhere in the header

**Why rejected:** Adds unnecessary complexity for a single navigation item.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-03-01 | Accepted | Implement header link | 6 months | 2026-09-01 |

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
| Depends On | ADR-021 | Admin Settings and Configurable Session Timeout | The admin settings page this link navigates to |
| Depends On | ADR-005 | RBAC Design | Admin role check for conditional rendering |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-031-A | Admin Settings Header Link | Technical Specification | [specs/SPEC-031-A-Admin-Settings-Header-Link.md](specs/SPEC-031-A-Admin-Settings-Header-Link.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
