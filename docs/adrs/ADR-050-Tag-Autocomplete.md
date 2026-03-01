# ADR-050: Tag Autocomplete

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-050 |
| **Initiative** | Tag Autocomplete (WP-10) |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-01 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris tag management system (ADR-037) where users manually type tag names into a free-text `TagInput` component, leading to inconsistent tag naming (e.g., "back-end" vs "backend" vs "Back End"), tag duplication, and a slower tagging workflow,

**facing** the need for tag name consistency and faster tag entry by surfacing existing tags as suggestions while still allowing new tag creation,

**we decided for** a `suggestions` prop on the existing `TagInput` component that accepts an array of existing tag strings fetched from `GET /api/entities/tags/all`, a filtered dropdown list that appears below the input as the user types and narrows matches by substring, keyboard navigation (`ArrowUp`/`ArrowDown` to select, `Enter` to confirm, `Escape` to dismiss), and ARIA `combobox` role with `aria-activedescendant` for screen reader support,

**and neglected** a server-side search endpoint that filters tags on the backend (unnecessary network overhead when the full tag list is small enough to filter client-side), a dedicated tag management admin page for normalising tags (useful but orthogonal to the input UX improvement), and replacing `TagInput` with a multi-select dropdown (loses the ability to create new tags inline),

**to achieve** consistent tag reuse across entities, faster tag entry via typeahead suggestions, and full keyboard and screen reader accessibility for the autocomplete interaction,

**accepting that** the full tag list is fetched on component mount (acceptable for up to thousands of tags; would need pagination or server-side filtering at larger scale), the dropdown uses client-side substring filtering (not fuzzy matching), and new tags not in the suggestions list can still be created freely by typing and pressing Enter.

---

## Options Considered

### Option 1: Client-Side Filtered Suggestions Dropdown (Selected)

**Pros:**
- Fast, responsive filtering with no network latency per keystroke
- Full tag list is small enough to hold in memory
- Preserves free-text tag creation for new tags
- ARIA combobox pattern is well-established for accessibility

**Cons:**
- Full tag list fetched on mount; may not scale to very large tag sets
- Client-side substring match is simplistic (no fuzzy/typo tolerance)

**Why selected:** Optimal UX for the current scale, fully accessible, and non-breaking enhancement to the existing `TagInput` component.

### Option 2: Server-Side Tag Search Endpoint (Rejected)

**Pros:**
- Scales to arbitrarily large tag sets
- Could support fuzzy matching on the server

**Cons:**
- Adds network latency to every keystroke (or requires debouncing)
- Requires a new API endpoint and backend query
- Over-engineered for the current tag volume

**Why rejected:** Premature optimisation; the tag set is small enough for client-side filtering.

### Option 3: Multi-Select Dropdown Replacing TagInput (Rejected)

**Pros:**
- Standard select component; no custom dropdown needed

**Cons:**
- Cannot create new tags inline; only existing tags can be selected
- Changes the interaction model from the current free-text input
- Multi-select dropdowns have poor UX for large option sets

**Why rejected:** Removing free-text tag creation is a regression; users need to create new tags without an admin workflow.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-03-01 | Accepted | Add autocomplete suggestions to TagInput | 6 months | 2026-09-01 |

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
| Depends On | ADR-037 | Tag Management System | Extends the existing TagInput component with suggestions |
| Depends On | ADR-008 | Accessibility WCAG 2.2 | ARIA combobox pattern for autocomplete accessibility |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
