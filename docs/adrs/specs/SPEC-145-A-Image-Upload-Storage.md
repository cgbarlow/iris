# SPEC-145-A: Image upload storage

ADR: [ADR-145](../ADR-145-Image-Upload-Storage.md)

## Database schema

### `images` table

| Column | SQLite type | Postgres type | Notes |
|---|---|---|---|
| `id` | `TEXT PRIMARY KEY` | `UUID PRIMARY KEY DEFAULT gen_random_uuid()` | Service generates UUIDs in SQLite; Postgres generates them server-side. |
| `mime` | `TEXT NOT NULL` | `TEXT NOT NULL` | One of {`image/png`, `image/jpeg`, `image/gif`, `image/webp`}. |
| `bytes` | `BLOB NOT NULL` | `BYTEA NOT NULL` | Raw file bytes. Max 5 MB. |
| `size_bytes` | `INTEGER NOT NULL` | `INTEGER NOT NULL` | Echoed back on upload responses; lets clients compute totals without reading bytes. |
| `uploaded_by` | `TEXT` | `UUID` | User id from the JWT; `NULL` if a future anonymous-upload mode is added. |
| `created_at` | `TEXT NOT NULL` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | ISO timestamp. |

### Indexes

- `idx_images_uploaded_by ON images(uploaded_by)` — admin queries / future GC.

### Migrations

- `backend/app/migrations/m045_images.py` (SQLite — registered in
  `app/startup.py::_initialize_sqlite`).
- `backend/app/migrations/supabase/m046_images.sql` (Postgres —
  applied by the Supabase migration runner in lex order).

## API

### `POST /api/images` (auth required)

| | |
|---|---|
| Auth | Any signed-in user (FastAPI `Depends(get_current_user)`). |
| Body | `multipart/form-data` with field `file`. |
| Response | `201 Created` + `ImageUploadResponse` (id / mime / size_bytes / created_at). |
| Errors | `400` (empty / unrecognised / declared-vs-actual MIME mismatch); `413` (over 5 MB cap); `415` (unsupported MIME). `401`/`403` for unauthenticated callers. |

### `GET /api/images/{id}` (public)

| | |
|---|---|
| Auth | None — embedded `<img src>` must resolve without sending the JWT on every render. |
| Response | `200` with the raw bytes; `Content-Type` set to the stored `mime`; `Cache-Control: public, max-age=31536000, immutable`. |
| Errors | `404` for unknown id. |

## Validation rules (service layer)

`backend/app/images/service.py::validate_image(data, declared_mime)`:

1. Reject empty uploads.
2. Reject uploads larger than `MAX_IMAGE_BYTES = 5 * 1024 * 1024`.
3. Sniff magic bytes:
   - `\x89PNG\r\n\x1a\n` → `image/png`
   - `\xff\xd8\xff…` → `image/jpeg`
   - `GIF87a` / `GIF89a` → `image/gif`
   - `RIFF…WEBP` → `image/webp`
4. Reject unrecognised magic.
5. If declared Content-Type contradicts detected, reject. Defends
   against text-file-with-fake-MIME attacks.

The detected MIME is what's stored — never the declared one.

## RLS (Supabase)

`m046_images.sql` enables RLS with three policies:

- `images_select` — `USING (TRUE)` (public read; matches the `GET`
  route's no-auth contract).
- `images_insert` — `WITH CHECK (auth.uid() IS NOT NULL)` (any
  authenticated user can upload).
- `images_delete` — `USING (admin OR uploaded_by = auth.uid())`
  (uploader can delete their own; admin can delete any). No
  delete endpoint is exposed yet — this policy reserves the
  semantics for when one is added.

## Frontend integration

### `markdownEditorToolbarHelpers.ts::uploadPastedImage(file)`

```ts
export async function uploadPastedImage(file: File): Promise<UploadedImage> {
    const form = new FormData();
    form.append('file', file, file.name || 'pasted-image.png');
    const resp = await apiFetch<{ id: string; mime: string; size_bytes: number }>(
        '/api/images', { method: 'POST', body: form }
    );
    return { id: resp.id, mime: resp.mime, size_bytes: resp.size_bytes,
             url: `/api/images/${resp.id}` };
}
```

`apiFetch` was extended in v5.4.0 to skip the default
`Content-Type: application/json` when the body is a `FormData`
instance — the browser then sets a proper multipart boundary.

### `TextCanvas.svelte::handlePaste(e)`

The textarea has a new `onpaste={handlePaste}`. The handler scans
`event.clipboardData.items` for the first `image/*` file, calls
`uploadPastedImage`, and splices `![pasted-image](/api/images/<id>)`
at the cursor via the v5.3.0 `applyOp(insertAtCursor(…))` pattern.
Non-image paste falls through to the browser default (text).

### Markdown link form

The inserted snippet is `![pasted-image](/api/images/<id>)`. Note
that this is an **absolute path** (no scheme). The v5.3.0 widening
of `ALLOWED_URI_REGEXP` to `/^(?:(?:https?|mailto|iris):|\/|\.{1,2}\/)/i`
already accepts it. The v5.3.0 `<img src>` post-walk also accepts
absolute paths — they resolve to the same-origin `https:` placeholder
inside `urlIsAllowed`.

## Tests

| File | Coverage |
|---|---|
| `backend/tests/test_images/test_router.py` | (5 tests) PNG upload happy path round-trips bytes; declared-vs-actual MIME mismatch rejected; >5 MB upload rejected; unknown id 404; missing auth rejected. |
| `frontend/tests/unit/markdownPasteImage.test.ts` | (4 tests) `uploadPastedImage` POSTs `/api/images` as multipart; TextCanvas mounts `onpaste`; the handler reads `clipboardData` for `image/*` items; splices via `insertAtCursor`/`applyOp`. |

## Out of scope (deferred per ADR-145)

- Image dedupe by content hash.
- Server-side resizing / thumbnailing.
- Garbage collection of orphaned images.
- Direct-to-bucket presigned-URL upload for >5 MB files.
