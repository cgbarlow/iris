# ADR-145: Image upload storage

Status: Accepted (2026-05-06)

## Context

v5.3.0 (issue #32 reopen) added a markdown editor toolbar but left
image insertion as a manual `![](path)` typed URL. UAT against v5.3.x
asked for GitHub-style clipboard image paste — paste a screenshot →
Iris uploads it → markdown link is auto-inserted at the cursor.

That requires durable image storage server-side. Three viable options
were considered before this v5.4.0 implementation:

1. **Backend `images` table with binary blob** (chosen).
2. **Supabase Storage bucket**.
3. **Inline base64 data URLs** (no infrastructure, embed bytes in
   markdown source).

## Decision

**Add an `images` table** (BLOB in SQLite, BYTEA in Supabase) and
**`/api/images` upload + serve routes**. Markdown links use the
absolute path `![alt](/api/images/<id>)` — no new URL scheme needed
(the v5.3.0 widened `ALLOWED_URI_REGEXP` already accepts absolute
paths).

Limits: max **5 MB** per image; MIME ∈ {png, jpeg, gif, webp}.
Validation is **magic-byte sniffed** — a text file with a fake
`image/png` Content-Type is rejected because the bytes don't match.

Authentication: `POST /api/images` requires a signed-in user (any
role). `GET /api/images/<id>` is public — embedded `<img src>` tags
need to resolve without auth so MarkdownView renders inline. Image
bytes are not user-authored secrets; they're attached to public
repository content.

## Why a backend table over Supabase Storage

- **Symmetry across deployment modes.** SQLite mode would need a
  separate `iris-images/` static directory if we used Supabase
  Storage in cloud mode. Two storage paths means two backup paths,
  two migration paths, two access-control models. The blob-in-table
  approach keeps both modes in lockstep.
- **Backups include images.** A single `pg_dump` or SQLite backup
  captures everything. With Storage buckets we'd need a separate
  rclone/gcs backup pipeline.
- **Auth flows through the existing JWT + RLS layer.** No need for a
  Supabase Storage bucket policy that'd have to be kept in sync with
  our role model.
- **Database row size is fine for screenshots.** 5 MB cap × thousands
  of images is well within Postgres BYTEA / SQLite BLOB territory.
  Database size grows linearly with image volume; Postgres has no
  hard limit on BYTEA. Performance for the read path is fine —
  binary indexes aren't needed; lookup is by primary-key UUID.

## Why not Supabase Storage

- Asymmetric across deployment modes (see above).
- Bucket policies are a separate access-control surface to maintain.
- For Iris's volume (markdown attachments, not user-uploaded video),
  the operational simplicity of a table beats the bucket's marginal
  scalability advantage.
- Direct frontend → bucket upload bypasses our normal request
  pipeline (auth, audit log, MIME validation hook).

## Why not base64 data URLs

- Bloats every diagram/text-view payload that contains an image.
- Breaks our deliberate `data:` URL ban (v5.3.0 §C); we'd be
  re-introducing the exact attack surface we strip from `<img src>`.
- Not shareable across diagrams — the same logo embedded in N text
  views means N copies of the bytes.
- Markdown source becomes unreadable when an editor opens it.

## Why not a separate filesystem path

- SQLite mode could plausibly serve from `static/images/`, but then
  the backup story diverges from the database.
- File permissions on the deployment machine become a concern.
- No native auth integration — we'd have to write our own gating in
  front of the static file server.

## Consequences

- New table, new module (`backend/app/images/`), new router. Code
  surface is small (~150 lines) and follows the existing
  `app/docref/` shape.
- Database size grows with image volume. At 5 MB cap × 10,000 images
  that's 50 GB — acceptable for Postgres; an SQLite deployment that
  grows that large would already be looking at Postgres anyway.
- `GET /api/images/<id>` is public. We accept this trade-off because
  (a) image content is attached to public repository content,
  (b) requiring auth on every embedded `<img src>` would force the
  browser to send the JWT cookie/header on every render — flaky and
  cache-defeating. If a future feature needs private images, the
  GET route can grow an `?auth=true` mode without breaking existing
  links.
- Cache: serving sets `Cache-Control: public, max-age=31536000,
  immutable` since image ids are content-addressed (UUID per upload;
  same bytes → same id is not enforced today, but would be safe to
  add).

## Out of scope (deferred)

- **Image dedupe by content hash.** We could SHA-256 each upload and
  return the existing id if the hash matches. Saves storage but adds
  complexity; revisit when usage warrants.
- **Image resizing / thumbnailing.** The browser scales for display.
  Iris doesn't currently generate thumbnails for any other content.
- **Referential integrity tracking.** An image is currently orphaned
  when the diagram referencing it is deleted. A garbage-collection
  background job is plausible but out of scope for v5.4.0.
- **Direct-to-bucket upload for very large files.** If we ever support
  >5 MB uploads, a presigned-URL flow to a separate object store is
  the right move.

## See also

- [ADR-137](ADR-137-Text-Diagram-Subclass-And-Shared-Markdown-Renderer.md) —
  v5.3.0 widened DOMPurify's `ALLOWED_URI_REGEXP` so absolute paths
  like `/api/images/<id>` pass through unstripped, and added a
  defence-in-depth post-walk on `<img src>`. The combination means
  the new image URLs work end-to-end without further security work.
- [ADR-135](ADR-135-DocRef-Supabase-Migration-Parity.md) — the
  shape this ADR copies for the SQLite/Supabase migration parity
  (m045_images.py + m046_images.sql; admin-write/all-read RLS for
  the upload endpoint, public-read at the GET).
- [SPEC-145-A](specs/SPEC-145-A-Image-Upload-Storage.md) — schema,
  endpoint signatures, MIME limits, RLS policies.
