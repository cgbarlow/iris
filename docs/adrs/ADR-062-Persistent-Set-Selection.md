# ADR-062: Persistent Set Selection

## Proposal: Global Set Filter with Session Persistence, Detail Page Cleanup, and Rate Limit Tuning

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-062 |
| **Initiative** | Persistent Set Selection & UI Polish |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-02 |
| **Status** | Approved |
| **Dependencies** | ADR-060 (Sets), ADR-061 (Sets Page & Dashboard Integration) |

---

## ADR (WH(Y) Statement format)

**In the context of** Iris having set-scoped filtering on individual pages (models, entities) but losing the active set selection when navigating between pages,

**facing** the inconvenience of re-selecting the same set on every page, the inability to see which set is currently active at a glance, the lack of inline set creation during import, editable tags cluttering the overview/details tabs, and 429 rate limit errors during normal browsing,

**we decided for** a sessionStorage-backed global store (`activeSet`) that persists the selected set across navigation, displaying the active set name in the AppShell header, highlighting the active set on the Sets page, adding "+ New Set" inline creation on the import page, moving tag editing and template toggle from overview tabs to edit dialogs (keeping read-only display), and increasing the general API rate limit from 100 to 300 requests/minute,

**and neglected** URL-based set persistence (adds complexity to every route, breaks bookmarks when sets change), localStorage persistence (too permanent — set context is session-scoped), and keeping tags editable inline on detail pages (inconsistent with edit-dialog pattern used elsewhere),

**to achieve** a seamless set-filtered browsing experience where selecting a set once carries through all pages, with cleaner detail page layouts and no rate limit interruptions during normal use,

**accepting that** sessionStorage resets on new tabs/windows (by design — each browsing session starts fresh), and tag editing now requires opening the edit dialog (one extra click but more consistent).

---

## Decisions

1. **Global activeSet store**: `activeSet.svelte.ts` using Svelte 5 runes with sessionStorage persistence, following the auth store pattern
2. **AppShell header integration**: Show "Iris / {SetName}" when a set is active, linking to the Sets page
3. **Page initialization from store**: Models and Entities pages initialize their set filter from the global store on mount
4. **Bidirectional sync**: Changing the set selector on any page updates the global store; clearing the filter clears the store
5. **Sets page highlighting**: Active set gets a primary-colored border; "Reset filter" button appears when a set is active
6. **SetSelector enhancement**: New `showNewSet`/`onNewSet` props for inline set creation; `onchange` passes both ID and name; exported `reload()` function
7. **Import page "New Set"**: SetDialog integration for creating sets inline during import; View Models link includes `set_id`
8. **Detail page cleanup**: Tags and template toggle moved from overview/details tabs to edit dialogs; read-only display with badge pills on overview; ID field styling normalized
9. **Rate limit increase**: General API rate limit raised from 100 to 300 requests/minute to prevent 429 errors during normal browsing

---

## References

- SPEC-062-A: Persistent Set Selection specification
- ADR-060: Sets, Batch Operations & Pagination
- ADR-061: Sets Page & Dashboard Integration
