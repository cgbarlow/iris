# Imports & Data

Iris can ingest architecture content from several sources and recover deleted or older-version content from the recycle bin and version history.

## Imports

> **Sign in to use this.** Imports require at minimum the **architect** role.

The **Import** page at `/import` handles file uploads.

### Sparx EA (.eap / .qea)

Imports a full Enterprise Architect model including packages, classes, components, ArchiMate elements, and relationships. Iris maps EA types to its internal schema automatically; unrecognised types are preserved as generic elements with their original type stored in metadata.

- **File format.** Drop a `.eap` or `.qea` file onto the upload area, or click to browse.
- **Set assignment.** Choose an existing set or let Iris create a new one named after the source file.
- **Progress.** A progress bar advances as EA content is parsed, converted, and inserted. Large models (> 10,000 elements) take a minute or two.
- **Result summary.** Reports elements created, relationships created, packages created, and any warnings (unmapped types, circular references, etc.).

### PowerPoint DoView (.pptx)

Imports a single DoView PowerPoint file and converts each slide into a diagram, each shape into an element, and each arrow into a causal relationship.

- **Single file.** Use the PPTX upload area on `/import`. Result shows slides processed, shapes classified, and any slides skipped (unrecognised master layouts).
- **Bulk / batch.** Drop multiple `.pptx` files at once or a single `.zip` archive containing many PPTX files. All files are grouped under a single set (you choose or create it) with per-file error reporting — any single file failing doesn't block the others.

### DocRef legislation (extension)

When the DocRef extension is enabled, admins can browse legislation documents from `legislation.docref.nz` and import them as AI context chunks. See [Ask AI](ask-ai) for how to select imported legislation into a query.

### Session file upload (Ask AI)

A lighter-weight alternative — upload a file (PDF, DOCX, XLSX, PPTX, CSV, plain text, ≤ 5 MB) directly on the **Ask AI** page as *session-scoped* context. The file is held in your browser tab only; it's not persisted to Iris. See [Ask AI](ask-ai).

## Recycle bin

> **Sign in to use this.** Non-admin users see only items they deleted; admins see everything.

Deletes in Iris are **soft by default** — the item disappears from normal views but a copy lives in the recycle bin for recovery.

- **Access.** `/recycle-bin` in the sidebar (signed-in users only).
- **Restore.** Individual **Restore** button, or **Restore All** for cascade groups (e.g. a deleted package and all its children deleted in the same operation).
- **Permanent delete.** The **Delete** button opens a confirmation dialog; after this the item is irrecoverable.
- **Bulk empty.** An **Empty Recycle Bin** button purges every item for users with the permission. The dialog warns this cannot be undone.

The recycle bin paginates at 50 items per page.

## Version history & rollback

> **Sign in to use this.** Read-only users can *view* prior versions; rollback requires **architect** or above.

Every write to an element, diagram, or package creates an **immutable version**. Version history is a first-class part of the data model — each entity has a `current_version` pointer and a `*_versions` table storing every prior state.

- **View.** Open any element / diagram / package detail page; the **Versions** section lists every version with timestamp, author, and change summary.
- **Compare.** Click two versions to see their diff (element properties, canvas JSON, tags, etc.).
- **Rollback.** Click **Rollback to this version** — Iris creates a *new* version whose content matches the selected one, bumping `current_version` forward. The original bad version is preserved in history; rollback never deletes anything.

Optimistic concurrency ensures two users can't silently overwrite each other: all write requests carry an `If-Match: <version>` header, and the server rejects with HTTP 409 if the version moved on since you fetched.

## Example data seeding

> **Sign in as admin to use this.**

Admin → Settings → **Seed Example Diagrams** populates the Default set with representative diagrams across every supported notation (Simple, UML, ArchiMate, Sequence, DoView, C4). Safe to run multiple times — existing diagrams aren't duplicated.

Use this on a fresh install to explore Iris's notations without having to draw anything yourself.

## Next steps

- [Canvas Editing](canvas-editing) — edit imported diagrams once they're in Iris.
- [Ask AI](ask-ai) — feed an imported set to the AI for semantic Q&A across it.
- [Admin & Permissions](admin) — who can import, who can empty the recycle bin.
