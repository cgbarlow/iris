# SPEC-179-A: Server-side md → docx / pdf renderer + Iris artefact store

ADR: [ADR-179](../ADR-179-Renderer-And-Artefact-Store.md)

## Summary

Build a renderer module under `backend/app/export/renderers/` that converts markdown to docx (via `python-docx` + `markdown-it-py`) and to pdf (via `weasyprint`). Add a generic artefact store at `backend/app/artefacts/` (separate from the image store). Expose render + retrieve via two new POST endpoints plus the artefact GET. Wrap both with MCP tools. Drop the Phase-1 docx/pdf fallback from `creation-cascade-destination-v1`.

## Schema

```sql
CREATE TABLE artefacts (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    mime TEXT NOT NULL,
    bytes BLOB NOT NULL,
    size_bytes INTEGER NOT NULL,
    source_kind TEXT NOT NULL,
    source_ref TEXT,
    created_by TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_artefacts_source_ref ON artefacts(source_ref);
```

`source_kind` values:
- `render_markdown` — ad-hoc render of cascade content. `source_ref = NULL`.
- `export_diagram` — diagram exported via `POST /api/export/diagram/{id}`. `source_ref = diagram_id`.

## ALLOWED MIMEs / cap

```python
ALLOWED_ARTEFACT_MIMES = frozenset({
    "text/markdown",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/pdf",
})
MAX_ARTEFACT_BYTES = 25 * 1024 * 1024  # 25 MB
```

## Renderer signatures

`backend/app/export/renderers/markdown.py`:
```python
def render(markdown: str) -> tuple[bytes, str]:
    """Return (bytes, filename). Normalised UTF-8 markdown."""
```

`backend/app/export/renderers/docx.py`:
```python
def render(markdown: str, title: str) -> tuple[bytes, str]:
    """Return (bytes, filename). Title becomes the docx 'Title' style at the top."""
```

`backend/app/export/renderers/pdf.py`:
```python
def render(markdown: str, title: str) -> tuple[bytes, str]:
    """Return (bytes, filename). Title becomes the HTML <title> and visible <h1>."""
```

Each renderer normalises the filename via slug-of-title + UUID suffix + extension. E.g. `title="Banana Monoculture DoView"` + docx → `banana-monoculture-doview-9f2c.docx`.

## Endpoints

### `POST /api/export/diagram/{diagram_id}`

Request body:
```json
{"format": "md" | "docx" | "pdf"}
```

Behaviour:
- 200: returns `{artefact_id, web_url, mime_type, filename}`.
- 404: diagram not found.
- 400: format not supported.
- 413: rendered output exceeds MAX_ARTEFACT_BYTES.

For markdown-content diagrams (`notation='markdown'`): use `data.content` directly. For visual diagrams: use the existing `app/export/markdown.py` bundle renderer to produce a structured summary, then render via the chosen format. Visual-diagram exports always include the bundle's element listing; pdf/docx exports include diagram metadata at the top.

### `POST /api/export/markdown`

Request body:
```json
{"markdown": "...", "title": "...", "format": "md" | "docx" | "pdf"}
```

Same return shape. For ad-hoc rendering of cascade-generated content that hasn't been saved to a diagram. No source_ref.

### `GET /api/artefacts/{artefact_id}`

Returns the artefact bytes with `Content-Type: <stored mime>` and `Content-Disposition: attachment; filename="<stored filename>"`. Auth-optional (matches `/api/images/{id}`). Long cache header — artefacts are immutable.

- 200: bytes
- 404: artefact not found

## MCP tools

In `mcp/src/iris_mcp/tools.py`:

```python
@server.tool()
async def export_diagram(diagram_id: str, format: str = "md") -> dict:
    """Render a diagram to markdown / docx / pdf and store in Iris.
    Returns {artefact_id, web_url, mime_type, filename} — give the user
    the web_url as a clickable download link."""
    ...

@server.tool()
async def render_markdown(markdown: str, title: str, format: str = "md") -> dict:
    """Render ad-hoc markdown content to md / docx / pdf and store in
    Iris. Used by creation cascades when the user picks "Chat with
    downloadable artefacts". Returns same shape as export_diagram."""
    ...
```

Both wrapped by `with_web_url` so the `web_url` is fully-qualified per ADR-175.

## Cascade prompt update

Migration `m{next}_drop_phase1_docx_fallback.py` UPDATEs `creation-cascade-destination-v1` to remove the docx/pdf-renderer fallback paragraph (Phase-1 fallback section in `docs/prompts/creation-cascade-destination.md`). The cross-set move fallback stays until Phase 3.

The seed file `backend/app/seed/creation_prompts.py` is updated in lockstep — `CASCADE_DESTINATION_PROMPT` constant body has the renderer fallback removed and replaced with: "When the user picks docx or pdf at Q-Dest3, call `render_markdown` for each selected format. The returned `web_url` is a downloadable link — present it to the user as a clickable URL."

## Dependencies

`backend/pyproject.toml`:
- `python-docx>=1.1.0` — already present, unchanged.
- `markdown-it-py>=4.0.0` — new.
- `weasyprint>=68.0` — new. Verified installable in the dev devcontainer. Render base image needs Pango / Cairo / GDK-PixBuf system libraries — verified at Phase 2 deploy gate.

Pin to latest stable as of implementation date per protocols §11.

## Tests

### `backend/tests/test_export/test_md_to_docx.py` (new)

- `test_simple_paragraph_round_trips` — md "Hello world" → docx → reopen via python-docx Document → assert one paragraph with text "Hello world".
- `test_heading_h1_h2_h3` — md with `# H1`, `## H2`, `### H3` → docx → assert paragraphs have styles `Heading 1`, `Heading 2`, `Heading 3`.
- `test_bullet_list_round_trips` — md `- one\n- two\n- three` → docx → assert three list-style paragraphs.
- `test_code_block_preserved` — md fenced code block → docx → assert paragraph with code style or monospace formatting.
- `test_mermaid_block_passes_through` — md ```mermaid``` block → docx → assert the body text contains the mermaid source verbatim.

### `backend/tests/test_export/test_md_to_pdf.py` (new)

- `test_simple_markdown_produces_valid_pdf` — md "Hello" → pdf → assert byte-header `b"%PDF"`.
- `test_multi_page_markdown` — long markdown → pdf → assert page count >= 2 via pdfplumber (already a backend dep).
- `test_title_appears_in_pdf` — md with title="Test" → pdf → extract text via pdfplumber → assert "Test" in text.

### `backend/tests/test_artefacts/test_store_roundtrip.py` (new)

- `test_create_artefact_returns_id` — service.create_artefact(bytes, mime, filename) → returns dict with id.
- `test_get_artefact_returns_bytes` — create + get → bytes match.
- `test_oversized_artefact_rejected` — bytes > 25MB → ValueError.
- `test_disallowed_mime_rejected` — `image/png` mime → ValueError ("use the images endpoint").

### `backend/tests/test_export/test_render_endpoints.py` (new)

- `test_post_render_markdown_md_returns_url` — POST /api/export/markdown with format=md → 200 + web_url + filename ending .md.
- `test_post_render_markdown_docx_returns_url` — same with format=docx → 200 + filename ending .docx + GET URL returns valid docx bytes.
- `test_post_render_markdown_pdf_returns_url` — same with format=pdf → 200 + filename ending .pdf + GET URL returns valid PDF (starts with `%PDF`).
- `test_post_export_diagram_404_for_missing_id` — POST /api/export/diagram/nope → 404.
- `test_post_render_markdown_invalid_format_400` — format=svg → 400.

### `backend/tests/test_migrations/test_artefacts_schema.py` (new)

- Static-parser checks: migration creates `artefacts` table with all required columns + index + idempotency guard.
- Supabase mirror present with same schema using `BOOLEAN`-correct literals where applicable.

### `backend/tests/test_migrations/test_phase2_destination_actuation_schema.py` (new)

- Migration removes the Phase-1 docx/pdf fallback string from `creation-cascade-destination-v1`.
- Migration leaves the cross-set move fallback string intact (move tools ship Phase 3).
- Supabase mirror does the same.
- Seed file constant `CASCADE_DESTINATION_PROMPT` no longer contains the docx-pdf fallback string but still contains the move-tools fallback string.

### `mcp/tests/test_export_tools.py` (new)

- `test_export_diagram_returns_web_url` — fixture diagram → MCP `export_diagram(id, format='md')` → response has `web_url` matching the configured `IRIS_WEB_URL`.
- `test_render_markdown_returns_web_url` — MCP `render_markdown("# Test", "Title", "pdf")` → response has `web_url` ending `/api/artefacts/<id>`.

## Versioning

`mcp/pyproject.toml`: 6.1.0 → 6.2.0. Minor bump — new MCP tools.
`frontend/package.json`: matched 6.2.0.

## CHANGELOG

`[6.2.0]` Added: renderer + artefact store + MCP `export_diagram` / `render_markdown`. Changed: cascade destination prompt drops docx/pdf fallback.

## Acceptance criteria

- [ ] `pytest backend/tests/test_export/` and `backend/tests/test_artefacts/` green.
- [ ] `pytest backend/tests/test_migrations/test_artefacts_schema.py test_phase2_destination_actuation_schema.py` green.
- [ ] `pytest mcp/tests/test_export_tools.py` green.
- [ ] Manual UAT: banana cascade picks "Both" + md+docx+pdf → three downloadable URLs that all open correctly.
- [ ] Render deployment check per `feedback_render_deploy_verification`: curl `/api/export/markdown` against the deployed env; if 500, update Dockerfile for Pango/Cairo/GDK-PixBuf.
