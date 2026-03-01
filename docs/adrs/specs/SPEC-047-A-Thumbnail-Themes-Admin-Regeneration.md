# SPEC-047-A: Thumbnail Themes & Admin Regeneration

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-047-A |
| **ADR Reference** | [ADR-047: Thumbnail Themes & Admin Regeneration](../ADR-047-Thumbnail-Themes-Admin-Regeneration.md) |
| **Date** | 2026-03-01 |
| **Status** | Accepted |

---

## Overview

This specification details theme-aware PNG thumbnail generation supporting three visual themes (light, dark, high-contrast), a database migration for composite primary keys on the thumbnails table, and an admin endpoint for bulk thumbnail regeneration with a corresponding frontend settings page button.

---

## A. Theme Definitions

### THEME_COLORS Constant

Define a `THEME_COLORS` dictionary mapping theme names to their colour palettes for SVG parameterisation.

**File:** `app/services/thumbnail_service.py`

```python
THEME_COLORS = {
    "light": {
        "background": "#ffffff",
        "node_fill": "#f8fafc",
        "node_stroke": "#6b7280",
        "edge_stroke": "#94a3b8",
        "text": "#1e293b",
        "label": "#475569",
    },
    "dark": {
        "background": "#1e293b",
        "node_fill": "#334155",
        "node_stroke": "#64748b",
        "edge_stroke": "#475569",
        "text": "#f1f5f9",
        "label": "#94a3b8",
    },
    "high-contrast": {
        "background": "#000000",
        "node_fill": "#1a1a1a",
        "node_stroke": "#ffffff",
        "edge_stroke": "#ffffff",
        "text": "#ffffff",
        "label": "#e0e0e0",
    },
}
```

### SVG Parameterisation

The existing SVG template generation is updated to accept a `theme` parameter. All hardcoded colour values in the SVG template are replaced with values from `THEME_COLORS[theme]`.

```python
def generate_thumbnail_svg(model_data: dict, theme: str = "light") -> str:
    colors = THEME_COLORS[theme]
    # ... SVG generation using colors dict ...
```

---

## B. Database Migration (m010)

### Migration File

**File:** `app/migrations/m010_thumbnail_themes.py`

```python
async def migrate(db: aiosqlite.Connection) -> None:
    """Add theme column to thumbnails table with composite PK."""
    # Create new table with composite PK
    await db.execute("""
        CREATE TABLE IF NOT EXISTS thumbnails_new (
            model_id TEXT NOT NULL,
            theme TEXT NOT NULL DEFAULT 'light',
            png_data BLOB,
            svg_data TEXT,
            generated_at TEXT NOT NULL,
            PRIMARY KEY (model_id, theme),
            FOREIGN KEY (model_id) REFERENCES models(id)
        )
    """)

    # Migrate existing data (all existing thumbnails become 'light' theme)
    await db.execute("""
        INSERT OR IGNORE INTO thumbnails_new (model_id, theme, png_data, svg_data, generated_at)
        SELECT model_id, 'light', png_data, svg_data, generated_at
        FROM thumbnails
    """)

    # Replace old table
    await db.execute("DROP TABLE IF EXISTS thumbnails")
    await db.execute("ALTER TABLE thumbnails_new RENAME TO thumbnails")

    await db.commit()
```

### Composite Primary Key

The `thumbnails` table uses a composite primary key of `(model_id, theme)`, allowing up to three rows per model (one per theme).

---

## C. Thumbnail API Updates

### Query Parameter

The existing thumbnail GET endpoint accepts an optional `?theme=` query parameter:

**Endpoint:** `GET /api/models/{model_id}/thumbnail?theme=light`

```python
@router.get("/models/{model_id}/thumbnail")
async def get_thumbnail(
    model_id: str,
    theme: str = Query(default="light", regex="^(light|dark|high-contrast)$"),
    db: aiosqlite.Connection = Depends(get_db),
):
    cursor = await db.execute(
        "SELECT png_data FROM thumbnails WHERE model_id = ? AND theme = ?",
        (model_id, theme),
    )
    row = await cursor.fetchone()
    if not row or not row[0]:
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    return Response(content=row[0], media_type="image/png")
```

### Thumbnail Generation

When generating thumbnails (on model save or bulk regeneration), all three themes are generated:

```python
async def generate_all_themes(db: aiosqlite.Connection, model_id: str, model_data: dict) -> None:
    for theme in THEME_COLORS:
        svg = generate_thumbnail_svg(model_data, theme)
        png = svg_to_png(svg)
        await db.execute(
            """INSERT OR REPLACE INTO thumbnails (model_id, theme, png_data, svg_data, generated_at)
               VALUES (?, ?, ?, ?, datetime('now'))""",
            (model_id, theme, png, svg),
        )
    await db.commit()
```

---

## D. Admin Regeneration Endpoint

### Endpoint

**Route:** `POST /api/admin/thumbnails/regenerate`

**Auth:** Admin role required (uses existing admin guard middleware).

```python
@router.post("/admin/thumbnails/regenerate")
async def regenerate_thumbnails(
    db: aiosqlite.Connection = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """Regenerate all thumbnails for all models across all themes."""
    cursor = await db.execute(
        "SELECT id, data FROM model_versions mv "
        "INNER JOIN (SELECT model_id, MAX(version) as max_v FROM model_versions GROUP BY model_id) latest "
        "ON mv.model_id = latest.model_id AND mv.version = latest.max_v "
        "INNER JOIN models m ON m.id = mv.model_id "
        "WHERE m.is_deleted = 0"
    )
    rows = await cursor.fetchall()
    count = 0
    for row in rows:
        model_id, data_json = row
        model_data = json.loads(data_json) if data_json else {}
        await generate_all_themes(db, model_id, model_data)
        count += 1
    return {"regenerated": count, "themes": list(THEME_COLORS.keys())}
```

### Response

```json
{
    "regenerated": 12,
    "themes": ["light", "dark", "high-contrast"]
}
```

---

## E. Frontend Settings Page

### Admin Regeneration Button

Add a "Regenerate Thumbnails" button to the admin settings page.

**File:** `src/routes/admin/settings/+page.svelte`

#### State

```typescript
let regenerating = $state(false);
let regenerateResult = $state<{ regenerated: number } | null>(null);
let regenerateError = $state<string | null>(null);
```

#### Handler

```typescript
async function handleRegenerateThumbnails() {
    regenerating = true;
    regenerateResult = null;
    regenerateError = null;
    try {
        const result = await apiFetch<{ regenerated: number; themes: string[] }>(
            '/api/admin/thumbnails/regenerate',
            { method: 'POST' }
        );
        regenerateResult = result;
    } catch (e) {
        regenerateError = e instanceof ApiError ? e.message : 'Failed to regenerate thumbnails';
    } finally {
        regenerating = false;
    }
}
```

#### UI

```svelte
<section>
    <h3>Thumbnail Management</h3>
    <p>Regenerate PNG thumbnails for all models across all themes (light, dark, high-contrast).</p>
    <button
        onclick={handleRegenerateThumbnails}
        disabled={regenerating}
        class="rounded px-4 py-2 text-sm"
        style="background: var(--color-primary); color: white"
    >
        {#if regenerating}
            Regenerating...
        {:else}
            Regenerate Thumbnails
        {/if}
    </button>
    {#if regenerateResult}
        <p class="text-green-600 mt-2">
            Regenerated thumbnails for {regenerateResult.regenerated} models.
        </p>
    {/if}
    {#if regenerateError}
        <p class="text-red-600 mt-2">{regenerateError}</p>
    {/if}
</section>
```

### Loading and Success States

| State | UI |
|-------|-----|
| Idle | Button shows "Regenerate Thumbnails" |
| Loading | Button disabled, shows "Regenerating..." |
| Success | Green text: "Regenerated thumbnails for N models." |
| Error | Red text with error message |

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| Three theme colour palettes defined | `THEME_COLORS` has `light`, `dark`, `high-contrast` keys |
| SVG generation accepts theme parameter | `generate_thumbnail_svg(data, "dark")` produces dark-themed SVG |
| Migration m010 creates composite PK | `thumbnails` table has `PRIMARY KEY (model_id, theme)` |
| Existing thumbnails preserved as light theme | After migration, existing rows have `theme = 'light'` |
| Thumbnail API accepts `?theme=` param | `GET /api/models/{id}/thumbnail?theme=dark` returns dark PNG |
| Invalid theme rejected | `?theme=invalid` returns 422 validation error |
| Admin regeneration endpoint requires admin role | Non-admin user receives 403 |
| Regeneration generates all three themes | After POST, three rows per model in thumbnails table |
| Settings page button shows loading state | Click button; verify "Regenerating..." text and disabled state |
| Settings page shows success count | After regeneration; verify green message with model count |
| Settings page shows error on failure | Simulate network error; verify red error message |

---

*This specification implements [ADR-047](../ADR-047-Thumbnail-Themes-Admin-Regeneration.md).*
