# ADR-137: Text diagram subclass and shared Markdown renderer

Status: Accepted (2026-05-04) — amended 2026-05-05 (issue #27)

## Context

Issue #26 asks for a "Text" class — a subclass of Diagram whose canvas
view is replaced with a markdown view. View mode renders the markdown;
edit mode shows the source. A TOC drawer (right side, like the
Comments tray) lists headings with depth-indented navigation. Text
documents can link to diagrams and elements; diagrams can link back.

The user also flagged that the existing User Guide already does
markdown rendering (`marked` + `DOMPurify` inline in
`/guide/[section]/+page.svelte`) and asked for DRY consolidation.

## Decision

Three concrete decisions:

### 1. Text is a Diagram subclass — no new tables

Add a `markdown` notation and a `text` diagram type to the existing
registry. A Text document is just a Diagram row with
`diagram_type='text'` + `notation='markdown'`. The markdown source
lives in the existing `data` JSON column under a `content` key:
`diagrams.data.content = "<markdown source>"`.

This reuses every existing Diagram surface for free: persistence,
versioning, tags, comments, search, the diagram-links table (text↔
diagram references work because Text *is* a Diagram), packages,
hierarchy, exports. No schema migration beyond the registry seed; no
new endpoints; no new permission rules.

### 2. One shared `MarkdownView` component

Extract `marked + DOMPurify` into
`frontend/src/lib/components/MarkdownView.svelte` and use it in both
the User Guide and the TextCanvas. The User Guide page becomes a
3-line wrapper. Pure helpers
(`extractHeadings`, `renderMarkdown`, `parseIrisHref`, `urlIsAllowed`)
live in a sibling `markdownHelpers.ts` so they're unit-testable
without mounting Svelte.

### 3. `iris://` URL scheme for cross-links

In-document links to other Iris models use the standard markdown link
syntax with an `iris://` URL scheme:

```markdown
See [the architecture diagram](iris://diagram/<id>) and
[this element](iris://element/<id>).
```

The renderer:

- Restricts URL schemes to `{http, https, mailto, iris}` at both the
  DOMPurify config (`ALLOWED_URI_REGEXP`) and a post-sanitiser walk
  (defence-in-depth — covers the case where a future DOMPurify update
  changes its default whitelist).
- Tags `iris://` anchors with `data-iris-kind` and `data-iris-id`
  attributes plus `md-iris-link` / `md-iris-link--{kind}` classes so
  the click handler can intercept and call SvelteKit `goto`.
- Adds `md-iris-link--text` to refs that point at a Text-class diagram
  (resolved via the optional `textDiagramIds` set), giving us the
  grey-vs-black visual distinction issue #26 asks for.

## Why a Diagram subclass, not a separate `text_documents` table

The user explicitly asked for Text to "be a sub-class of Diagram." The
existing schema is already polymorphic on (`diagram_type`, `notation`)
and the `data` JSON column accepts any shape. Reusing those gives us:

- Existing hierarchy menu treats Text the same as any other diagram.
- Existing diagram-links table handles text↔diagram references
  unchanged (Text *is* a diagram).
- Existing comments, tags, packages, search all work for free.
- Cross-linking *between* text documents works because they're all
  the same kind of row.

A separate table would force us to re-implement every one of those.

## Why store element refs as iris:// links inside the markdown, not as a join table

The plan briefly considered a `text_links` table (or extending
`diagram_links` with a `target_kind` discriminator). Rejected: the
links *are* part of the document content. Storing them separately
splits ownership and adds a join for every render.

The renderer extracts `iris://` links at render time and calls back
with the list (`onlinks` callback) so the host can build a "Linked
elements" sidecar without storing anything extra. If we later need
indexed link queries (e.g. "what links to this element?"), we can
extract them into a denormalised view in a follow-up — the canonical
data still lives in the markdown source.

## Why a shared MarkdownView, not migrating User Guide content to Text diagrams

The user picked option (1) in plan-mode Q&A: extract the rendering
component and keep the User Guide as bundled static content.

The alternative — seeding User Guide sections as Text diagrams in the
DB — would couple offline-readable docs to runtime DB state and
complicate first-boot UX. The DRY win is in the *rendering pipeline*,
not in the *content storage*. Moving the rendering into a shared
component achieves DRY without conflating doc-as-bundled-asset with
user-authored Text diagrams.

## Why iris:// scheme rather than `[[wiki-style]]` or markdown directives

User picked the iris:// option in plan-mode Q&A. Rationale:

- Standard markdown link syntax — renders correctly in any markdown
  viewer (GitHub preview of an exported document, clipboard paste
  into another tool).
- URL-shaped — DOMPurify already understands URL allowlists; we
  benefit from the existing security model rather than building a
  parallel one for wiki-syntax.
- Easy to author, easy to copy, machine-parseable.
- The iris:// scheme reads as "Iris-internal" so the intent is
  obvious to readers.

`[[wiki-style]]` is ambiguous on name collisions and needs a
resolution UI. Custom markdown directives break rendering in plain
viewers. Both rejected.

## Why allow only http/https/mailto/iris

The plan flagged `iris://` link handling as a possible javascript:
smuggling vector. We belt-and-brace it:

1. DOMPurify config restricts URI scheme via `ALLOWED_URI_REGEXP` =
   `/^(?:https?|mailto|iris):/i`.
2. Post-sanitiser walk re-validates each anchor's href via
   `urlIsAllowed` and strips the href if rejected.

`data:`, `file:`, `javascript:`, `about:`, etc. all blocked.

## Compatibility

- Existing diagrams unaffected — Text is a new option, not a
  replacement.
- Existing User Guide content unchanged — only the rendering pipeline
  is consolidated into the shared component.
- The diagram-links table is unchanged; text↔diagram references work
  via the existing same-table mechanism because Text is a Diagram.
- No backend endpoints added.

## Out of scope (deferred)

- **Indexed link extraction** for "what references this element"
  queries — the `iris://` links are inline; if we need a backwards
  index later, we'll denormalise into a view in a follow-up.
- **Conflict resolution UI** for collaborative editing of long text
  documents — OT/CRDT integration is its own substantial workstream.
- **Bidirectional link graph visualisation** — could power a "linked
  documents" sidebar; defer until usage warrants it.
- **Markdown extensions** (mermaid blocks, callouts, footnotes) —
  start with stock markdown; extend if users ask.

## See also

- [ADR-079](ADR-079-Diagram-Type-Notation-Registry.md) — registry
  pattern reused.
- [ADR-122](ADR-122-User-Guide.md) — original User Guide markdown
  pipeline; this ADR consolidates it into the shared component.
- [SPEC-137-A](specs/SPEC-137-A-Text-Diagram-And-Markdown-View.md) —
  schema, rendering rules, link extraction, UX details.

## Amendment 2026-05-05 — UAT follow-ups (issue #27)

UAT against render-supabase-uat surfaced four functional gaps and a
broad terminology change. Each is addressed without re-architecting
the v5.1.0 design — the Text-as-Diagram-subclass + shared-MarkdownView
pieces stand. The amendments tighten the editor and rename the
user-facing surface from "Diagrams" to "Views" so a Text view sits
naturally alongside a Canvas view.

### A. Save was always disabled in the markdown editor (root-cause bug)

`canvasDirty` is the single flag that gates the toolbar Save button on
the diagram detail page. The first-cut TextCanvas wiring updated
`diagram.data.content` in `oncontentchange` but never set
`canvasDirty = true`, so Save stayed greyed out forever. **Fix:** flip
`canvasDirty` from the same callback. One-line change in the parent
page; Text editing is now indistinguishable from canvas editing as far
as the dirty-tracking contract is concerned.

### B. Save wiped the markdown content (root-cause bug)

`saveCanvas` always wrote `data: { nodes: canvasNodes, edges: canvasEdges }`
to the API. For a Text diagram those arrays are empty, so saving an
edited text view replaced `data.content` with an empty
nodes/edges object — and the next browse render fell into the
"empty canvas" branch instead of MarkdownView. This is exactly what
the user saw: "I now see a normal canvas diagram with the diagram and
element boxes I added in the markdown editor, however none of the
markdown text I wrote." **Fix:** branch on `canvasType === 'text'`
inside `saveCanvas` and persist `{ content: markdownContent }`
instead.

### C. Add Diagram / Add Element / Link Element insert markdown links in Text mode

The toolbar buttons live one level above the canvas/text branch and
were creating canvas nodes regardless of mode. In Text mode the user
expects an `iris://` markdown link inserted at the cursor. **Fix:**
`TextCanvas` now exposes its `<textarea>` upward via a `$bindable`
`textareaEl` prop. The page reads `selectionStart/End`, splices the
markdown link in at the cursor, updates `diagram.data.content`, and
restores focus. `handleAddElement`, `handleLinkElement` and
`handleInsertDiagram` each gain a one-shot Text branch that calls a
shared `insertMarkdownAtCursor(snippet)` helper.

### D. BPMN was missing from `NotationPills` (covered by ADR-136 amendment)

Same root cause as the BPMN regression noted in the ADR-136 amendment
above — the picker hard-coded a five-entry list. The Text class also
needs `markdown` to be in that picker, so it benefits from the same
fix.

### E. "Diagrams" → "Views" — frontend terminology and routing

Issue #27 renames the user-facing concept so a Text view doesn't have
to live under a "Diagrams" menu. **Scope is frontend-only** at the
user's explicit request — backend tables, API routes and stored data
all keep the `diagram` term to avoid an invasive migration. The
changes:

- `src/routes/diagrams/` moved to `src/routes/views/` (git-rename to
  preserve history).
- Stub `+page.ts` files at `/diagrams` and `/diagrams/[id]` issue an
  HTTP 308 redirect to `/views` and `/views/<id>` so existing
  bookmarks and external deep-links keep working.
- All in-app navigation (`href`, `goto`, `recordVisit.href`,
  `MarkdownView` click handler, `TreeNode.nodeHref`,
  `EntityDetailPanel`, `ModelRefNode`, `AppShell` nav, dashboard cards
  and breadcrumbs) updated to `/views`.
- Visible labels swapped: page titles, the AppShell menu entry,
  dashboard "Diagrams" card → "Views", "Diagram Hierarchy" tab →
  "View Hierarchy", search/filter placeholders, batch dialog
  copy, etc.
- `DiagramDialog` field label "Diagram Type" → "View Type" and the
  markdown notation's type entry shortened from "Text Document" to
  "Text" per UAT note ("the View Type we get in the drop-down is
  'Text'").

### F. Hierarchy panel — two-button standard

Both the Dashboard hierarchy panel and the Views index now share a
new `HierarchyControls` component with exactly two dropdowns:

- **+ New** → View | Package. The notation pill in the resulting
  Create dialog handles Diagram-vs-Text selection (drops the
  earlier dashboard-only `View → Diagram | Text` submenu, which the
  user explicitly asked us to flatten).
- **Show** → checkboxes for *Diagrams* and *Text*. Packages are
  always shown — the dropdown labels this so the absence of a
  Packages toggle is intentional, not a bug.

The Dashboard's existing Reorder button is kept (drag-to-reorder tree
items) with a clearer tooltip; the user noted they weren't sure what
it does, so we don't remove the capability — we just explain it.

`TreeNode` gains `showDiagrams` / `showText` props so the hierarchy
view honours the toggle on both pages without re-implementing the
filter.

### G. EntityDialog notation pill scope

`EntityDialog` (used for "Add Element" on a canvas) keeps its
notation picker but now passes `notations={[..., excluding 'markdown']}`
to `NotationPills` — text views have no entities, so offering markdown
in this context is misleading.

## Out of scope (this amendment)

- **Backend rename** from `diagram` to `view`. The user explicitly
  deferred this ("Don't make this change on the backend (yet), as this
  may get very messy"). API routes (`/api/diagrams/*`) and stored
  fields (`diagram_type`, `diagrams.data`) stay as-is. Frontend types
  (`Diagram`, `DiagramHierarchyNode`) similarly keep their names so the
  TypeScript surface against the API stays trivially mappable.
- **Markdown editor toolbar redesign** — Add/Link buttons keep their
  current labels even in Text mode. A future pass could rename them in
  Text context ("Insert Element Link" etc.) but the existing labels
  read sensibly enough now that they actually insert what they say.
