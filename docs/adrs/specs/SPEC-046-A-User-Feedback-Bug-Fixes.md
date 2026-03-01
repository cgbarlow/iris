# SPEC-046-A: User Feedback Bug Fixes

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-046-A |
| **ADR Reference** | [ADR-046: User Feedback Bug Fixes](../ADR-046-User-Feedback-Bug-Fixes.md) |
| **Date** | 2026-03-01 |
| **Status** | Accepted |

---

## Overview

This specification details four targeted bug fixes identified from user feedback: gallery thumbnail sizing (WP-2), audit log username resolution (WP-6), entity tag enrichment in detail views (WP-11), and edge handle hover visual feedback (WP-13). Each fix is independently scoped with no architectural changes required.

---

## A. Gallery Thumbnail Sizing (WP-2)

### Problem

Gallery thumbnails use `object-cover` CSS which crops non-square images, cutting off parts of the model diagram. Thumbnails are also not centred within their grid cells.

### Fix

Replace `object-cover` with `object-contain` and add flex centering to the thumbnail container.

**File:** `src/routes/models/+page.svelte` (gallery card image container)

```css
/* Before */
.gallery-card img {
    object-fit: cover;
}

/* After */
.gallery-card img {
    object-fit: contain;
}

.gallery-card .thumbnail-container {
    display: flex;
    align-items: center;
    justify-content: center;
}
```

### Behaviour

- Thumbnails render at full aspect ratio without cropping
- Non-square thumbnails are centred both horizontally and vertically within the card
- Whitespace may appear around non-square thumbnails (acceptable trade-off for correct proportions)

---

## B. Audit Log Username Resolution (WP-6)

### Problem

Audit log entries display raw `user_id` GUIDs instead of human-readable usernames, making audit review difficult.

### Fix

Add a `_resolve_username()` helper function in the audit service/middleware that queries the users table to resolve GUIDs to usernames before storing or returning audit entries.

**File:** `app/services/audit_service.py` (or `app/middleware/audit.py`)

```python
async def _resolve_username(db: aiosqlite.Connection, user_id: str) -> str:
    """Resolve a user_id GUID to a username.

    Returns the username if found, otherwise returns the original user_id.
    """
    cursor = await db.execute(
        "SELECT username FROM users WHERE id = ?",
        (user_id,)
    )
    row = await cursor.fetchone()
    return row[0] if row else user_id
```

### Integration

The `_resolve_username()` function is called when constructing audit log entries before they are written. The resolved username is stored alongside or instead of the raw GUID in the audit entry's user identifier field.

### Behaviour

- Audit entries display usernames (e.g., `admin`) instead of GUIDs
- If a user has been deleted, the raw GUID is displayed as a fallback
- One additional query per audit entry (acceptable at current scale)

---

## C. Entity Tag Display (WP-11)

### Problem

The `get_entity()` service function returns entity data without associated tags from the `entity_tags` table, so the entity detail view shows no tags.

### Fix

Enrich the `get_entity()` response by querying the `entity_tags` table and including tags in the returned entity object.

**File:** `app/services/entity_service.py`

```python
async def get_entity(db: aiosqlite.Connection, entity_id: str) -> dict | None:
    # ... existing entity query ...

    # Enrich with tags
    cursor = await db.execute(
        "SELECT tag FROM entity_tags WHERE entity_id = ? ORDER BY tag",
        (entity_id,)
    )
    rows = await cursor.fetchall()
    entity["tags"] = [row[0] for row in rows]

    return entity
```

### Behaviour

- Entity detail API response includes a `tags` array
- Tags are sorted alphabetically
- If no tags exist, an empty array is returned
- No changes required to the frontend if it already renders a `tags` field from the response

---

## D. Edge Handle Hover Highlight (WP-13)

### Problem

Edge connection handles (the dots at node edges for creating/reconnecting edges) lack visual feedback on hover, making them hard to discover and target.

### Fix

Add CSS rules for `.svelte-flow__handle:hover` and `.svelte-flow__edgeupdater` to provide visible highlight effects.

**File:** `src/lib/canvas/canvas-styles.css` (or equivalent global canvas stylesheet)

```css
/* Edge handle hover glow */
.svelte-flow__handle:hover {
    transform: scale(1.6);
    box-shadow: 0 0 6px 2px var(--color-primary);
    border-color: var(--color-primary);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}

/* Larger default handle dot */
.svelte-flow__handle {
    width: 10px;
    height: 10px;
}

/* Edge updater (reconnection) handle */
.svelte-flow__edgeupdater:hover {
    transform: scale(1.4);
    box-shadow: 0 0 6px 2px var(--color-primary);
}

/* Selected edge handle styling */
.svelte-flow__handle.connectingto,
.svelte-flow__handle.connectingfrom {
    border-color: var(--color-primary);
    background: var(--color-primary);
}
```

### Behaviour

- Handles scale up and glow with the primary colour on hover
- Default handle dot size is increased from the @xyflow default for easier targeting
- Transition animations provide smooth visual feedback
- Styling respects the current theme via CSS custom properties

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| Gallery thumbnails use `object-contain` | Inspect gallery card images; verify no cropping on non-square thumbnails |
| Gallery thumbnails are flex centred | Verify thumbnails are horizontally and vertically centred in their cells |
| Audit entries show usernames | View audit log; verify entries display usernames instead of GUIDs |
| Deleted user audit entries show GUID fallback | Delete a user, view their audit entries; verify GUID displayed |
| Entity detail includes tags | `GET /api/entities/{id}` response includes `tags` array |
| Entity with no tags returns empty array | Create entity without tags; verify `tags: []` in response |
| Edge handles glow on hover | Hover over a connection handle; verify scale and glow effect |
| Edge handles use primary colour | Verify handle hover colour matches `--color-primary` |
| Handle hover transition is smooth | Verify CSS transition on handle hover/unhover |

---

*This specification implements [ADR-046](../ADR-046-User-Feedback-Bug-Fixes.md).*
