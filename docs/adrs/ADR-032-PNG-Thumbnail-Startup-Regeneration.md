# ADR-032: PNG Thumbnail Startup Regeneration and Frontend Fallback

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-032 |
| **Initiative** | Fix PNG Gallery Mode Showing No Images |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-01 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris model gallery PNG thumbnail feature (ADR-022), where `cairosvg` was listed as an optional dependency with a graceful fallback but was never actually installed, meaning all thumbnails stored in the database contained raw SVG bytes instead of PNG data, and models created before the thumbnail migration (m007) have no entry in the `model_thumbnails` table at all, resulting in 404 responses from the thumbnail endpoint,

**facing** the need for PNG gallery mode to actually display images rather than showing a blank gallery with broken image placeholders — both for existing models that lack thumbnail entries and for deployments that previously ran without `cairosvg`,

**we decided for** a three-part fix:

1. **Add `cairosvg` as a required dependency** in `pyproject.toml` (not optional) so that PNG conversion always works. The system library `libcairo2-dev` is available in the deployment environment.
2. **Add a `regenerate_all_thumbnails()` function** in `thumbnail.py` that iterates all non-deleted models and generates+stores PNG thumbnails, called during application startup after migrations complete. This ensures pre-existing models and models with stale SVG-byte thumbnails are brought up to date.
3. **Add an `onerror` fallback on the frontend `<img>` tag** so that if a thumbnail request fails (404, network error, corrupt data), the gallery card gracefully falls back to the existing `<ModelThumbnail>` SVG component instead of showing a broken image icon.

**and neglected** making `cairosvg` remain optional and improving only the SVG-bytes fallback path (would not produce actual PNG images, defeating the purpose of the PNG mode setting), adding a manual admin action to trigger thumbnail regeneration (adds operational burden and does not solve the zero-state problem on fresh deployments), and converting thumbnails lazily on first request (adds latency to user requests and complicates the endpoint with generation logic),

**to achieve** a PNG gallery mode that works out of the box — thumbnails are guaranteed to exist for all models after startup, the `cairosvg` dependency is explicit rather than silently missing, and the frontend gracefully handles any remaining edge cases where a thumbnail is temporarily unavailable,

**accepting that** startup time increases proportionally to the number of models (thumbnail generation is CPU-bound), `cairosvg` and its system dependency `libcairo2` are now required rather than optional, and the `onerror` fallback adds a small amount of JavaScript to each gallery card.

---

## Options Considered

### Option 1: Required cairosvg + Startup Regeneration + Frontend Fallback (Selected)

**Pros:**
- Guarantees PNG thumbnails exist for all models after startup
- Makes the dependency explicit — no silent degradation
- Frontend fallback provides defence in depth
- No manual intervention required

**Cons:**
- Startup time increases with model count
- Adds a required system dependency (libcairo2)

**Why selected:** Addresses all three root causes (missing dependency, missing thumbnails, no frontend fallback) in a single coherent change.

### Option 2: Keep cairosvg Optional, Improve SVG Fallback (Rejected)

**Pros:**
- No new system dependency requirement
- Simpler change

**Cons:**
- PNG mode would never actually serve PNG images without cairosvg
- Does not address missing thumbnails for pre-existing models
- The `gallery_thumbnail_mode=png` admin setting becomes misleading

**Why rejected:** Defeats the purpose of ADR-022's PNG thumbnail feature.

### Option 3: Lazy Thumbnail Generation on Request (Rejected)

**Pros:**
- No startup overhead
- Only generates thumbnails when actually needed

**Cons:**
- Adds latency to the first thumbnail request for each model
- Complicates the GET endpoint with generation logic
- Race conditions if multiple requests hit an un-generated thumbnail simultaneously

**Why rejected:** Shifts the cost to user-facing request latency and adds complexity to the read path.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-03-01 | Accepted | Implement startup regeneration and frontend fallback | 6 months | 2026-09-01 |

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
| Depends On | ADR-022 | Server-Generated PNG Thumbnails | This ADR fixes issues in the original implementation |
| Depends On | ADR-013 | Model Preview Thumbnails | Frontend SVG fallback component |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-032-A | PNG Thumbnail Fix | Technical Specification | [specs/SPEC-032-A-PNG-Thumbnail-Fix.md](specs/SPEC-032-A-PNG-Thumbnail-Fix.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
