# ADR-209: Entity image attachments + picker image references + markdown image-button chooser

Status: Accepted (2026-05-20)

Builds on: [ADR-205](./ADR-205-Smart-Markdown-View-Type.md), [ADR-206](./ADR-206-Smart-Markdown-Picker-Evolution.md), [ADR-207](./ADR-207-Picker-Bug-Fixes-And-Container-Drill.md).

## Context

Today Iris's image store is used in a narrow flow: the user pastes an image while editing a markdown view; the bytes are POSTed to `/api/images` (table `images`, ADR-undocumented m045) and a markdown link `![alt](/api/images/<id>)` is inserted at the cursor. Separately, sets and collections each carry a single `thumbnail_image` BLOB column for their tile.

Issue [#194](https://github.com/cgbarlow/iris/issues/194) extends this in three dimensions:

1. **Any entity** (collection, set, package, view, element) should be able to hold one or more attached images, presented under its **Details** screen and managed via the Edit Details flow.
2. **The picker** should be able to reference an attached image. Picking surfaces the image with a sizing chooser (original / width-by-% / width-by-px / height-by-% / height-by-px). The picked image is rendered in browse mode.
3. **The markdown image-toolbar button** today inserts `![alt](path)` blindly. It needs to ask: paste a **Link** (URL) or **Upload** a file.

## Decision

### Storage — a single junction table

Add `entity_images` table:

```
entity_images (
  id            TEXT PRIMARY KEY,
  entity_type   TEXT NOT NULL,  -- collection|set|package|diagram|element
  entity_id     TEXT NOT NULL,
  image_id      TEXT NOT NULL,  -- FK to images.id
  display_order INTEGER NOT NULL DEFAULT 0,
  created_at    TEXT NOT NULL,
  created_by    TEXT NOT NULL,
  UNIQUE (entity_type, entity_id, image_id)
)
```

with an index on `(entity_type, entity_id, display_order)`. Paired SQLite m073 + Supabase m078 (Protocol §15).

Rejected alternatives:
- **Per-entity-type tables** (e.g. `collection_images`, `set_images`, ...): five times the schema, five times the CRUD, no DRY.
- **BLOB columns on each entity table**: only allows a single image per entity. Doesn't satisfy "one or more".
- **Move bytes out of Postgres into Supabase Storage**: out of scope for v6.17.0 — Iris's blob-in-table pattern is established (`images.bytes`, `sets.thumbnail_image`).

### Endpoints — write surface gets §14 parity

```
POST   /api/{entity_type}/{entity_id}/images         (multipart, upload + auto-attach)
POST   /api/{entity_type}/{entity_id}/images/attach  (JSON, attach existing image_id)
GET    /api/{entity_type}/{entity_id}/images         (list attachments + image metadata)
DELETE /api/{entity_type}/{entity_id}/images/{attachment_id}
```

`entity_type` is whitelisted to the five canonical types. The DELETE detaches but does **not** delete the underlying `images` row — another entity may reference it. Garbage collection is a deferred housekeeping concern.

MCP tools: `attach_entity_image`, `detach_entity_image`, `list_entity_images`. CLI: corresponding subcommands on `iris-client`. The image-upload flow itself (POST /api/images) already exists in both surfaces.

### Picker token grammar — `image` as a new entity_type variant

Extend the existing Smart Markdown token grammar:

```
{{image:<id>}}                  → original size
{{image:<id>:width:50%}}        → CSS width 50%
{{image:<id>:width:300px}}      → CSS width 300px
{{image:<id>:height:50%}}       → CSS height 50%
{{image:<id>:height:300px}}     → CSS height 300px
```

Resolver in `backend/app/diagrams/smart_markdown.py` adds an `image` branch that emits:

```html
<img src="/api/images/<id>" style="width:50%" alt="">
```

(or no `style` for original). The `<img>` tag survives DOMPurify with its `style` attribute provided the value matches the existing CSS-property allow-list. At implementation, verify; if `style="width:50%"` is stripped, switch to legacy HTML attributes `width="..."` / `height="..."` (integer px only — % size would then be limited).

Unresolved images (deleted, wrong id) render `~~{{image:...}}~~` (the existing strikethrough fallback).

### Image button on the markdown toolbar — chooser dialog

Replace `MarkdownEditorToolbar.svelte`'s `image()` handler with `openImageDialog()`. Each canvas (SmartMarkdownCanvas, TextCanvas) renders a single `<ImageInsertDialog>` instance. The dialog has two tabs:

- **Link**: URL input + optional alt text → emits `![alt](url)` at the caret.
- **Upload**: file input → POST `/api/images` (existing endpoint) → emits `![alt](/api/images/<id>)` at the caret.

Both modes validate the URL / file client-side using the same 5 MB / `png|jpeg|gif|webp` constraints already enforced server-side.

### Details-screen UI — `EntityImagesEditor` component

A single reusable Svelte component (`frontend/src/lib/components/EntityImagesEditor.svelte`) hosts the gallery and upload UI. Props: `entityType`, `entityId`, `editing` (passed from the parent details screen's existing edit-mode state).

- Read mode: grid of attached images, click for full-size preview.
- Edit mode: same grid plus a `+ Upload` button (uploads + auto-attaches) and per-image `Remove` buttons. Reorder UI deferred — `display_order` column exists for forward compatibility.

The five details screens (`/collections/[id]`, `/sets/[id]`, `/packages/[id]`, `/views/[id]`, `/elements/[id]`) each mount one instance. Sets keep their existing `thumbnail_image` UI alongside — the concepts are distinct: thumbnail is the entity's tile-art; attachments are an arbitrary gallery.

### Side-fix — views index page

The `/views/` index currently renders `HierarchyControls` (with `+ New ▾` dropdown offering Package/View/Element and a `Show ▾` dropdown). The user wants a single primary `New View` button matching `/elements/`'s "New Element" button style + position. Drop `<HierarchyControls>` from the views index only — dashboard and packages-detail keep using it.

## Why a single junction table

DRY (§13). One set of CRUD endpoints, one render path, one set of MCP tools, one set of tests. The same image can be attached to multiple entities cheaply.

## Why HTML emission for sized images

Resolver runs server-side and writes `data.content`. `MarkdownView.svelte` already pipes that through marked → DOMPurify → `{@html}`. Markdown alone has no native image-sizing syntax; emitting `<img>` directly is the cleanest path. `style="width:..."` survives DOMPurify when the CSS property is whitelisted.

## Why §14 parity (full MCP + CLI mirrors)

A scripted importer or AI-driven documentation flow may want to attach images programmatically. The discipline keeps Iris's surfaces aligned. The script already enforces this — adding tools costs less than carving out another exception.

## Surface parity (§14)

All four new write endpoints have MCP tools and CLI subcommands. `scripts/check_surface_parity.py` must pass without new exceptions.

## Migration parity (§15)

Paired m073 (SQLite) + m078 (Supabase). Both idempotent. Release ordering: schema-dependent code (the attachment endpoints) reads `entity_images` — so the Supabase mirror must be applied via `scripts/supabase-migrate.sh` before any attachment request is made. Render auto-deploys on push; the schema-dependent endpoints will 500 with "table entity_images does not exist" until the migrate script runs.

## Security (§7)

Resolver output is HTML (not raw markdown) for image tokens. DOMPurify still strips dangerous attributes; the `src` URL is constrained to `/api/images/<id>` (relative path, no scheme). `style="width:..."` is the only style content emitted and is whitelist-validated in the sanitiser configuration.

For uploads: existing image endpoint already validates MIME by magic byte + 5 MB cap. No new validation gates.

## Consequences

- Backend: migrations (m073 / m078), new service + router, MCP tools, CLI methods, resolver extension.
- Frontend: ImageInsertDialog, EntityImagesEditor, picker image-pick + sizing chooser, five details-screen mounts, toolbar wiring.
- Tests: schema, attachment-endpoint round-trip, resolver token cases, MCP tool round-trip, CLI client round-trip, Vitest for dialog/editor/picker.

CHANGELOG `[6.17.0]`. Closes issue #194.

## Verification

Documented in SPEC-209-A. Key signals: round-trip an image through `POST /api/{entity}/{id}/images` then `GET` lists it; Smart Markdown `{{image:<id>:width:50%}}` renders `<img>` at the chosen size; toolbar button presents two modes; surface-parity script green.

## See also

- Issue [#194](https://github.com/cgbarlow/iris/issues/194).
- m045 — existing `images` table.
- §7 `{@html}` security, §13 DRY, §14 Surface parity, §15 Migration parity: `docs/protocols.md`.
