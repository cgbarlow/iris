# ADR-137: Text diagram subclass and shared Markdown renderer

Status: Accepted (2026-05-04)

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
