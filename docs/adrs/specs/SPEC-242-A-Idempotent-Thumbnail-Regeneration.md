# SPEC-242-A: Idempotent (content-hashed) thumbnail regeneration

**Implements:** [ADR-242](../ADR-242-Idempotent-Thumbnail-Regeneration.md)
**Status:** Implemented
**Date:** 2026-07-07

## Summary

Add a `content_hash` to each stored diagram thumbnail so startup regeneration
skips the cairosvg render **and** the Supabase write for any `(diagram, theme)`
whose rendered SVG is unchanged. Eliminates the ~56 MB-per-boot egress that the
free-tier `iris-api` was paying on every one of its ~12–24 daily restarts.

## Schema

`diagram_thumbnails` gains one nullable column:

```
content_hash TEXT   -- sha256(_THUMBNAIL_RENDERER_VERSION ‖ "\0" ‖ svg_str), hex
```

- **SQLite:** migration `m083_thumbnail_content_hash` — idempotent
  `PRAGMA table_info` guard + `ALTER TABLE diagram_thumbnails ADD COLUMN content_hash TEXT`.
- **Supabase:** `_initialize_supabase()` runs
  `ALTER TABLE diagram_thumbnails ADD COLUMN IF NOT EXISTS content_hash TEXT`.

PK is unchanged (`diagram_id, theme`); the `INSERT OR REPLACE` upsert now writes
`(diagram_id, theme, thumbnail, content_hash, updated_at)`.

## Behaviour

`backend/app/diagrams/thumbnail.py`:

- `_THUMBNAIL_RENDERER_VERSION = "1"` — bump to force a global regeneration when
  the rasteriser changes in a way that does not alter the SVG string.
- `_compute_thumbnail_hash(svg_str) -> str` — `sha256(version + "\0" + svg_str)`.
- `generate_and_store_thumbnail(..., *, force=False, known_hash=_UNSET) -> bool`:
  1. build `svg_str` (unchanged; includes the `smart_markdown` token resolve so
     the hash reflects resolved content),
  2. `content_hash = _compute_thumbnail_hash(svg_str)`,
  3. if not `force`: resolve the existing hash (`known_hash` if the caller
     prefetched it, else a one-row `SELECT`); if it equals `content_hash`,
     **return `False` without rendering or writing**,
  4. otherwise render the PNG and upsert the row with the new hash; **return `True`**.
- `regenerate_all_thumbnails(db, *, force=False) -> int`:
  - prefetches all `(diagram_id, theme) → content_hash` in a single `SELECT`,
  - passes each as `known_hash` so a steady sweep does **one** read and **zero**
    writes,
  - logs `written` vs `skipped`,
  - returns the number of diagrams processed (`len(rows)`), unchanged, so the
    admin endpoint's `{"count": …}` contract holds.

`backend/app/diagrams/router.py`: `POST /api/admin/thumbnails/regenerate` calls
`regenerate_all_thumbnails(db, force=True)` — an explicit admin action always
force-refreshes.

Startup (`backend/app/startup.py`) calls the sweep with the default
`force=False` on both the SQLite (awaited) and Supabase (backgrounded) paths.

## Acceptance criteria

1. Calling `generate_and_store_thumbnail` twice with identical data returns
   `True` then `False`; the second call performs no DB write (the row's
   `updated_at` is unchanged).
2. Changing the diagram `data` between calls returns `True` again (hash differs).
3. `force=True` always returns `True` and rewrites, even when unchanged.
4. A legacy row with `content_hash = NULL` regenerates once (`True`), then a
   subsequent call skips (`False`).
5. `regenerate_all_thumbnails` over an unchanged database writes **zero**
   thumbnails (all skipped) on the second run.
6. Existing thumbnail guarantees still hold: new diagrams get PNGs, deleted
   diagrams are skipped, all three themes are produced, and the admin regenerate
   endpoint returns a count ≥ 1.
7. The `content_hash` column exists on a freshly initialised database.
