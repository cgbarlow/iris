# SPEC-209-A: Entity image attachments — implementation

Implements: [ADR-209](../ADR-209-Entity-Image-Attachments.md)
Status: Living

## Schema

### SQLite — `backend/app/migrations/m073_entity_images.py`

```sql
CREATE TABLE IF NOT EXISTS entity_images (
  id            TEXT PRIMARY KEY,
  entity_type   TEXT NOT NULL,
  entity_id     TEXT NOT NULL,
  image_id      TEXT NOT NULL,
  display_order INTEGER NOT NULL DEFAULT 0,
  created_at    TEXT NOT NULL,
  created_by    TEXT NOT NULL,
  UNIQUE (entity_type, entity_id, image_id)
);
CREATE INDEX IF NOT EXISTS idx_entity_images_entity
  ON entity_images (entity_type, entity_id, display_order);
```

### Supabase — `backend/app/migrations/supabase/m078_entity_images.sql`

```sql
-- Mirrors SQLite m073.
CREATE TABLE IF NOT EXISTS public.entity_images (
  id            TEXT PRIMARY KEY,
  entity_type   TEXT NOT NULL,
  entity_id     TEXT NOT NULL,
  image_id      TEXT NOT NULL,
  display_order INTEGER NOT NULL DEFAULT 0,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_by    TEXT NOT NULL,
  UNIQUE (entity_type, entity_id, image_id)
);
CREATE INDEX IF NOT EXISTS idx_entity_images_entity
  ON public.entity_images (entity_type, entity_id, display_order);

-- RLS — read for authenticated; insert/delete restricted to the
-- entity's owner-via-set (or service role). Match images-table RLS.
ALTER TABLE public.entity_images ENABLE ROW LEVEL SECURITY;
-- Policies copied from `images` table — adjust at implementation
-- time after verifying that table's policies.
```

Startup registers m073 alongside the existing migrations.

## Pydantic models — `backend/app/images/entity_attachment_models.py`

```python
EntityType = Literal["collection", "set", "package", "diagram", "element"]

class AttachImageRequest(BaseModel):
    image_id: str

class EntityImageResponse(BaseModel):
    id: str
    entity_type: EntityType
    entity_id: str
    image_id: str
    image_mime: str
    image_size_bytes: int
    display_order: int
    created_at: str
    created_by: str
```

## Service — `backend/app/images/entity_attachment_service.py`

```python
async def attach_image(
    db, *, entity_type, entity_id, image_id, created_by,
) -> dict:
    # Verify (entity_type, entity_id) exists in its table.
    # Verify image_id exists in images.
    # INSERT OR IGNORE into entity_images (UNIQUE protects duplicates).
    # Return the row + image metadata.
    ...

async def detach_image(db, *, entity_type, entity_id, attachment_id) -> bool:
    # DELETE WHERE id=? AND entity_type=? AND entity_id=?
    # Returns True if deleted.
    ...

async def list_entity_images(db, *, entity_type, entity_id) -> list[dict]:
    # SELECT joining images. Order by display_order, created_at.
    ...
```

Helper `_verify_entity_exists(db, entity_type, entity_id) -> bool` switches on
entity_type to query the right table (with soft-delete checks).

## Router — `backend/app/images/entity_attachment_router.py`

```
POST   /api/{entity_type}/{entity_id}/images         (multipart)
POST   /api/{entity_type}/{entity_id}/images/attach  (JSON {image_id})
GET    /api/{entity_type}/{entity_id}/images
DELETE /api/{entity_type}/{entity_id}/images/{attachment_id}
```

- `entity_type` path param validated against `_ALLOWED` set.
- POST multipart calls the existing image-create service + attach in one transaction.
- 404 if entity doesn't exist; 404 if attachment doesn't exist on DELETE; 409 on already-attached (existing junction row).

## Token resolver — `backend/app/diagrams/smart_markdown.py`

Update the entity-type alternation in `_TOKEN_RE`:

```python
_TOKEN_RE = re.compile(
    r"\{\{(element|package|diagram|set|collection|image):"
    r"([^:}]+):?"
    r"((?:attr:[^}]+)|name|description|width:[^}]+|height:[^}]+|original)?\}\}"
)
```

(Or keep `[^}]+` permissive and branch inside the resolver. Either works.)

In the resolver's dispatch:

```python
async def _resolve_image(db, image_id: str, sizing: str | None) -> str | None:
    cursor = await db.execute(
        "SELECT id FROM images WHERE id = ?", (image_id,),
    )
    if not await cursor.fetchone():
        return None  # → strikethrough
    style = _format_image_style(sizing or "")
    style_attr = f' style="{style}"' if style else ""
    return f'<img src="/api/images/{image_id}"{style_attr} alt="">'


def _format_image_style(sizing: str) -> str:
    # sizing ∈ "" | "original" | "width:50%" | "width:300px" | "height:50%" | "height:300px"
    if not sizing or sizing == "original":
        return ""
    m = re.fullmatch(r"(width|height):(\d{1,4}(?:%|px))", sizing)
    if not m:
        return ""
    return f"{m.group(1)}:{m.group(2)}"
```

The result is plain HTML, which passes through marked unchanged (marked renders raw HTML when allowed) and survives DOMPurify with `style="width:|height:"` whitelisted.

## DOMPurify config — `frontend/src/lib/components/markdownHelpers.ts`

If DOMPurify strips `style` on `<img>` by default, configure it explicitly:

```ts
DOMPurify.setConfig({
  // existing config…
  ADD_ATTR: ['style'],
  ALLOWED_STYLES: ['width', 'height'],   // tighten CSS allowlist
});
```

(At implementation: verify the existing DOMPurify version + config first; only add what's missing.)

## MCP tools — `mcp/src/iris_mcp/tools.py`

```python
{
    "name": "attach_entity_image",
    "description": "Attach an existing image (by image_id) to an Iris entity.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "entity_type": {"type": "string", "enum": [...]},
            "entity_id": {"type": "string"},
            "image_id": {"type": "string"},
        },
        "required": ["entity_type", "entity_id", "image_id"],
    },
},
{
    "name": "detach_entity_image",
    "description": "Detach an image from an Iris entity by attachment id.",
    ...
},
{
    "name": "list_entity_images",
    "description": "List images attached to an Iris entity.",
    ...
},
```

Each calls the corresponding HTTP endpoint via the existing IrisClient.

## CLI — `iris-client/src/iris_client/client.py`

```python
async def attach_entity_image(self, entity_type: str, entity_id: str, image_id: str): ...
async def detach_entity_image(self, entity_type: str, entity_id: str, attachment_id: str): ...
async def list_entity_images(self, entity_type: str, entity_id: str): ...
```

## Frontend — `ImageInsertDialog.svelte`

Two-tab dialog:

```svelte
<script>
  let { open, oninsert, oncancel } = $props();
  let tab = $state<'link' | 'upload'>('link');
  let url = $state(''), alt = $state(''), file = $state<File | null>(null);

  function submitLink() {
    oninsert(`![${alt}](${url})`);
  }
  async function submitUpload() {
    const fd = new FormData();
    fd.append('file', file!);
    const r = await apiFetch<{id: string}>('/api/images', { method: 'POST', body: fd });
    oninsert(`![${alt}](/api/images/${r.id})`);
  }
</script>
```

Validates client-side: URL must be http(s) or relative; file size ≤ 5 MB; MIME in `{png, jpeg, gif, webp}`.

## Frontend — `EntityImagesEditor.svelte`

```svelte
<script>
  let { entityType, entityId, editing } = $props();
  let attachments = $state<EntityImage[]>([]);

  onMount(load);
  async function load() {
    attachments = await apiFetch(`/api/${entityType}/${entityId}/images`);
  }
  async function upload(file: File) {
    const fd = new FormData();
    fd.append('file', file);
    await apiFetch(`/api/${entityType}/${entityId}/images`, { method: 'POST', body: fd });
    await load();
  }
  async function remove(att: EntityImage) {
    await apiFetch(`/api/${entityType}/${entityId}/images/${att.id}`, { method: 'DELETE' });
    await load();
  }
</script>

<div class="grid grid-cols-3 gap-2">
  {#each attachments as att (att.id)}
    <div class="relative">
      <img src="/api/images/{att.image_id}" alt="" class="rounded border" />
      {#if editing}
        <button onclick={() => remove(att)} class="absolute top-0 right-0">×</button>
      {/if}
    </div>
  {/each}
  {#if editing}
    <label class="flex items-center justify-center rounded border-dashed">
      <input type="file" accept="image/png,image/jpeg,image/gif,image/webp" onchange={(e) => upload(e.target.files[0])} />
      + Upload
    </label>
  {/if}
</div>
```

Mounted in all five details screens.

## Picker — image picking + sizing

In `SmartMarkdownSlashPicker.svelte`:

- Extend `EntityType` to include `image`.
- In drill mode for any entity_type ∈ {element, set, package, diagram, collection}, fetch attachments via `/api/{entity_type}/{entity_id}/images`. If non-empty, render an "Images" container in the drill menu.
- Clicking the Images container shows the attached images as picker items, each a thumbnail + name.
- Clicking an image opens a small inline sizing chooser:
  - Radio: original / width / height
  - When width/height selected: number input + unit toggle (% / px)
  - Confirm → emit `{{image:<image_id>}}` or `{{image:<image_id>:<axis>:<value><unit>}}`

## Views index — single primary button

```svelte
<!-- frontend/src/routes/views/+page.svelte -->
<button
  onclick={() => (showCreateDialog = true)}
  class="rounded px-4 py-2 text-sm text-white"
  style="background-color: var(--color-primary)"
>
  New View
</button>
```

Replaces the existing `<HierarchyControls .../>` invocation on this page. Keep the `<DiagramDialog>` instance for the create flow.

## Tests

- `backend/tests/test_migrations/test_entity_images_schema.py` — schema parity m073 + m078.
- `backend/tests/test_images/test_entity_attachments.py` — attach/detach/list round-trip; cross-entity reattach (same image, different entities); duplicate-attach idempotency (UNIQUE); entity-type whitelist 422; 404 for missing entity / image.
- `backend/tests/test_diagrams/test_smart_markdown.py` (extend) — `{{image:<id>}}` renders `<img src=...>`; sizing variants render correct style; missing image → strikethrough.
- `mcp/tests/test_entity_image_tools.py` — tool round-trip.
- `iris-client/tests/test_entity_images.py` — client round-trip.
- Frontend Vitest:
  - ImageInsertDialog: Link inserts `![](url)`; Upload posts FormData and inserts the resulting URL.
  - EntityImagesEditor: list, upload, remove.
  - Picker: drill into entity with attachments, see Images, pick image, choose sizing, token emitted.

## Verification

End-to-end smoke (after dev restart):

1. Add an image to a `set` via Edit Details → Images → Upload. Confirm the grid shows it.
2. Add the same image to a `package` via the same UI. Verify cross-entity attachment works.
3. In a Smart Markdown view in that set, `/` → Pick this set → drill → Images → pick the image → choose width:50% → `{{image:<id>:width:50%}}` inserted.
4. Switch to view mode → image renders at 50% width.
5. Standard Markdown view → click toolbar image button → Link → paste a URL → confirm `![alt](url)` inserted. Repeat with Upload.
6. `scripts/check_surface_parity.py` exits 0.
7. `uv run pytest -x` + `npm run test:unit` green.
8. After deploy: run `scripts/supabase-migrate.sh` to apply m078.
9. `curl https://iris-api-gtb3.onrender.com/api/sets/{id}/images` returns the list once auth is presented.
