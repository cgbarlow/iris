# ADR-012: Models Page Gallery View

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-012 |
| **Initiative** | Models Page Gallery View with Card Resize Slider |
| **Proposed By** | Architecture Team |
| **Date** | 2026-02-28 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris models list page, which currently only supports a single-line list view showing model name, type badge, and a truncated description (60 characters), limiting the ability to browse and compare models visually,

**facing** the need for users to see more model detail at a glance — including full descriptions and dates — and the desire for a more visual browsing experience when managing a growing collection of architectural models,

**we decided for** adding a gallery/card view mode toggle to the models list page, using CSS grid with `repeat(auto-fill, minmax())` for responsive card layout, a native HTML `<input type="range">` slider to adjust card size (200px–400px), and localStorage persistence for both view mode and card size preferences,

**and neglected** adding a dedicated gallery page or route (which would fragment the models browsing experience and duplicate filter/sort logic), using a third-party card/grid library (unnecessary complexity for a CSS grid layout), and adding thumbnail/preview images to cards (models don't have image data; canvas thumbnails are a future feature),

**to achieve** a richer model browsing experience where users can toggle between compact list view and detailed card view, resize cards to their preference, and have their view preferences persist across sessions without any new dependencies,

**accepting that** the gallery view is implemented entirely within the existing `+page.svelte` file (no new component extraction), localStorage preferences are per-browser (not per-user on the server), and the card size slider is only visible in gallery mode.

---

## Options Considered

### Option 1: Gallery View with CSS Grid and Range Slider (Selected)

**Pros:**
- No new dependencies — native HTML range input and CSS grid
- Responsive layout with `auto-fill` adapts to any screen width
- localStorage persistence is simple and reliable
- Single-file change avoids premature component extraction

**Cons:**
- localStorage is per-browser, not synced across devices
- Card size slider adds toolbar complexity

### Option 2: Separate Gallery Page/Route (Rejected)

**Pros:**
- Clean URL separation (`/models/gallery`)

**Cons:**
- Duplicates filter, sort, and search logic
- Fragments the browsing experience
- Users must navigate between two pages

**Why rejected:** The gallery view is an alternative rendering of the same data — a toggle within the page is more intuitive than a separate route.

### Option 3: Third-Party Card/Grid Library (Rejected)

**Pros:**
- May offer additional layout features (masonry, virtual scrolling)

**Cons:**
- Adds a dependency for something CSS grid handles natively
- Increases bundle size
- Violates the "no new dependencies" constraint

**Why rejected:** CSS grid with `auto-fill` and `minmax()` provides exactly the responsive card layout needed.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-02-28 | Accepted | Implement gallery view with persistence | 6 months | 2026-08-28 |

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

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-012-A | Gallery View Implementation | Technical Specification | [specs/SPEC-012-A-Gallery-View-Implementation.md](specs/SPEC-012-A-Gallery-View-Implementation.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
