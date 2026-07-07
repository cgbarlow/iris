# ADR-242: Content-hash guard makes startup thumbnail regeneration idempotent

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-242 |
| **Initiative** | Stop `iris-api` from re-writing every diagram thumbnail to Supabase on every boot, which was burning ~56 MB of Render egress per restart (~30–40 GB/month) |
| **Proposed By** | Engineering |
| **Date** | 2026-07-07 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** the `iris-api` Render service (free plan, Singapore)
reading persistently high bandwidth — flagged at 6 GB and climbing — where a
Render metrics + logs investigation established that: (a) the bandwidth arrives
in discrete ~56 MB units, one per hour of *service uptime*; (b) hours containing
**no** restart show ~0 MB (e.g. 2026-07-07 15:00 = 0.0002 MB, 19:00 = 0.0005 MB)
while every hour containing a restart shows ~56 MB; (c) the free service restarts
~12–24×/day (spin-down/cycle/deploy), each boot logging
`[STARTUP] regenerated 1221 diagram thumbnails`; and (d) the database is
**Supabase** (external over the public internet), so the startup sweep's writes
are billed as Render egress,

**facing** `regenerate_all_thumbnails()` in `backend/app/diagrams/thumbnail.py`,
which on **every** startup unconditionally re-rendered and re-wrote a PNG for
**all 1221 non-deleted diagrams × 3 themes** (~3,663 `INSERT OR REPLACE` blobs,
~48 MB egress) back to Supabase — even though the diagrams and the renderer had
not changed since the previous boot, and even though the module already renders
any genuinely new/changed diagram fresh on its first `GET /thumbnail`, making the
blanket sweep almost entirely redundant work,

**we decided to** make thumbnail generation **content-addressed / idempotent**:
store a `content_hash` per `(diagram_id, theme)` row equal to
`sha256(renderer_version ‖ svg_str)` — the SHA-256 of the exact SVG that would be
rasterised, prefixed with a bumpable `_THUMBNAIL_RENDERER_VERSION` constant.
`generate_and_store_thumbnail()` now computes that hash and, unless `force=True`,
**skips both the cairosvg render and the DB write** when the stored hash already
matches. `regenerate_all_thumbnails()` prefetches all existing hashes in a single
`SELECT` and only writes the rows whose content actually changed, so a steady
boot costs **one small read and zero writes** instead of ~48 MB of writes,

**and neglected** (1) hashing the diagram *input* (`data` + `diagram_type` +
`theme`) rather than the rendered `svg_str` — rejected because a `smart_markdown`
thumbnail depends on **resolved** `{{…}}` tokens (other elements), so input-only
hashing would wrongly skip regeneration when a referenced element changed;
hashing the final `svg_str` captures every determinant of the output and also
auto-invalidates whenever `generate_svg_from_diagram_data` changes; (2) gating the
sweep behind an env flag so it runs only after a renderer change — considered, but
the hash guard subsumes it (an SVG change changes the hash) and needs no operator
action, with the `_THUMBNAIL_RENDERER_VERSION` bump left as the explicit
global-invalidation knob for rasteriser changes that don't alter the SVG string;
(3) simply reducing restart frequency (paid plan) — orthogonal; it would mask, not
fix, the redundant-write waste and every deploy would still pay it; (4) skipping
the SVG generation too on unchanged rows — not taken because SVG generation is
pure in-memory string building with no I/O, so it contributes no bandwidth and
gates the hash,

**to achieve** steady-state boots that re-write **~0** thumbnails and transfer
~0 MB (down from ~56 MB), collapsing the restart-driven ~30–40 GB/month egress to
a one-time sweep after each genuine renderer or diagram change, while preserving
the existing guarantees (new/changed diagrams still render on demand; the admin
`POST /api/admin/thumbnails/regenerate` endpoint still force-refreshes via
`force=True`),

**accepting that** (i) the **first** boot after this deploy still performs one
full sweep, because pre-existing rows have `content_hash = NULL` and hash-mismatch
forces a single regeneration that back-fills the hashes; (ii) changing the
rasterisation in a way that does **not** change `svg_str` requires a manual
`_THUMBNAIL_RENDERER_VERSION` bump to propagate; and (iii) a new nullable
`content_hash` column is added to `diagram_thumbnails` on both the SQLite
(migration `m083`) and Supabase (`ALTER TABLE … ADD COLUMN IF NOT EXISTS`) paths.

---

## Consequences

- **Bandwidth:** restart-driven thumbnail egress drops from ~56 MB/boot to ~0 in
  steady state. Verified in tests: a second `regenerate_all_thumbnails()` over an
  unchanged database performs zero thumbnail writes.
- **Schema:** `diagram_thumbnails` gains `content_hash TEXT` (nullable). Legacy
  rows (`NULL`) regenerate exactly once, then settle.
- **Surface parity (Protocol §14 / ADR-182):** no new write endpoint, MCP tool,
  or CLI subcommand — this is an internal idempotency optimisation of an existing
  code path. Parity unaffected.
- **Observability:** `regenerate_all_thumbnails()` logs written-vs-skipped counts
  so the effect is visible in Render logs after deploy.

## Related

- Supersedes the unconditional-sweep behaviour introduced for issue #208
  (v6.17.8) and kept when the sweep was backgrounded (v6.30.2). The sweep still
  exists and still propagates renderer changes — it is now idempotent.
- Implemented by [SPEC-242-A](./specs/SPEC-242-A-Idempotent-Thumbnail-Regeneration.md).
