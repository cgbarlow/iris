# ADR-029: Bookmarks Page

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-029 |
| **Initiative** | Bookmarks Page |
| **Proposed By** | Architecture Team |
| **Date** | 2026-02-28 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris frontend, where users can bookmark models from the model detail page and the dashboard shows bookmarked models in a summary section, but there is no dedicated bookmarks page and no sidebar navigation link for bookmarks,

**facing** the need for users to have a single, discoverable location to view all their bookmarked models, manage bookmarks (remove), and navigate to bookmarked model detail pages without relying on the dashboard summary,

**we decided for** creating a dedicated `/bookmarks` route with a page that fetches all bookmarks, resolves model details, displays them in a list with remove actions, and adding a "Bookmarks" link to the sidebar navigation between Entities and Settings,

**and neglected** expanding the existing dashboard bookmarks section with remove functionality (which keeps bookmarks subordinate to the dashboard and does not provide a focused experience), and creating a modal/drawer overlay for bookmarks accessible from the header (which avoids a new route but limits screen real estate and discoverability),

**to achieve** a first-class bookmarks experience where users can efficiently review and manage all their bookmarked models from a dedicated, discoverable page accessible via the main sidebar navigation,

**accepting that** this adds a new route and sidebar item, slightly increasing navigation complexity, and that the bookmark list requires N+1 API calls (one for bookmark list plus one per bookmarked model to resolve details).

---

## Options Considered

### Option 1: Dedicated Bookmarks Page (Selected)

**Pros:**
- First-class navigation via sidebar link
- Full page for managing bookmarks (view, remove, navigate)
- Consistent with how other resources (Models, Entities) have dedicated pages
- Clear separation of concerns from dashboard

**Cons:**
- N+1 API calls to resolve model details for each bookmark
- Adds a new route and sidebar navigation item

### Option 2: Expand Dashboard Bookmarks Section (Rejected)

**Pros:**
- No new route needed
- Reuses existing dashboard UI

**Cons:**
- Dashboard becomes overloaded with management functionality
- Bookmarks remain subordinate to the dashboard context
- No direct sidebar link for bookmark management

**Why rejected:** The dashboard is a summary view; adding full CRUD management to a summary section blurs its purpose and makes bookmarks harder to discover.

### Option 3: Header Bookmark Drawer/Modal (Rejected)

**Pros:**
- Accessible from any page without navigation
- No new route required

**Cons:**
- Limited screen real estate in a modal/drawer
- Inconsistent with sidebar-based navigation pattern used elsewhere
- Not discoverable unless users notice the header icon

**Why rejected:** Inconsistent with the sidebar navigation pattern established by Models, Entities, and Settings pages.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-02-28 | Accepted | Implement bookmarks page and sidebar link | 6 months | 2026-08-28 |

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

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-029-A | Bookmarks Page | Technical Specification | [specs/SPEC-029-A-Bookmarks-Page.md](specs/SPEC-029-A-Bookmarks-Page.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
