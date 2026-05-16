# ADR-179: Server-side md → docx / pdf renderer + Iris artefact store

Status: Accepted (2026-05-16)
Extends: ADR-145 (image store), ADR-175 (web URL decoration), ADR-176 (cascade destination chooser).

## Context

Issue #133 Phase 1 (v6.1.0) shipped the destination-chooser prompt — the cascade now asks the user "save where?" and "what format(s)?" — but the renderer that actually produces the docx / pdf bytes, and the store that holds them, didn't exist. The Phase-1 cascade explicitly explains the gap and offers fallbacks ("docx and PDF generation ships in v6.2.0").

Two design questions decided in the review for the plan rewrite (issue #133 v2 plan, May 2026):

- **Where are rendered artefacts stored?** The user picked "store the file in Iris (we have a store for images, re-leverage that if suitable or extend) — provide a link to the file to the user". So artefacts persist server-side and MCP returns a download URL.
- **What's the storage scope?** "This should apply by default for any docx or pdf generated, not just big ones." So inline base64 returns are out — every render lands in the store first.

The MCP `web_url` decoration shipped in ADR-175 (v6.0.15) is the natural delivery mechanism — the render tools return `{artefact_id, web_url, mime_type, filename}` so the model can hand the user a one-click link.

## Decision

### Renderer

Build a single renderer module at `backend/app/export/renderers/` with three Python files:

- `markdown.py` — passthrough with stable normalisation (trim trailing whitespace, ensure trailing newline). Same code path as the existing `app/export/markdown.py` bundle renderer — Phase 2 just normalises the output for downstream consumption.
- `docx.py` — md → docx via `python-docx` (already a backend dependency at >=1.1.0) + `markdown-it-py` (new dependency). Recipe modelled on `github.com/anthropics/skills/tree/main/skills/docx` — reads the markdown-it token stream and emits `python-docx` paragraphs / headings / lists / code blocks. Mermaid blocks pass through as triple-backtick code blocks; the docx reader can paste them into a mermaid-rendering tool.
- `pdf.py` — md → pdf via `weasyprint` (new dependency) + a default CSS template. The markdown is converted to HTML via `markdown-it-py`, wrapped in a minimal HTML document with Iris-branded CSS, then passed to `weasyprint.HTML(string=...).write_pdf()`.

Iris-branded CSS lives in `backend/app/export/renderers/styles/iris.css`. The CSS is small (~2 KB) — Iris fonts (system stack), header colour palette, code block styling, table borders. No image embedding by default; mermaid in PDFs stays as code (which the human can read or render in a separate tool).

### Artefact store

New top-level module `backend/app/artefacts/` (NOT a graft onto `app/images/`). The image store has tight magic-byte validation for PNG/JPEG/GIF/WebP — extending it to accept docx + pdf + plain text would either weaken that validation or carve out a separate code path inside it. A sibling module is cleaner: each store enforces the validation appropriate to its content category.

Schema:

```sql
CREATE TABLE artefacts (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    mime TEXT NOT NULL,
    bytes BLOB NOT NULL,
    size_bytes INTEGER NOT NULL,
    source_kind TEXT NOT NULL,  -- 'render_markdown' | 'export_diagram' | future kinds
    source_ref TEXT,            -- diagram id when source_kind='export_diagram', NULL otherwise
    created_by TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_artefacts_source_ref ON artefacts(source_ref);
```

Allowed MIMEs (frozenset constant):
- `text/markdown`
- `application/vnd.openxmlformats-officedocument.wordprocessingml.document` (docx)
- `application/pdf`

Per-artefact size cap: 25 MB (generous — full DoView books fit easily).

### Endpoints

In `backend/app/export/router.py` (new endpoints alongside the existing read endpoints):

- `POST /api/export/diagram/{diagram_id}` body `{format: 'md' | 'docx' | 'pdf'}` — fetches the diagram, extracts a markdown representation (uses the existing `app/export/markdown.py` bundle renderer plus the diagram's `data.content` if it's a markdown-content diagram), renders to the chosen format, stores, returns `{artefact_id, web_url, mime_type, filename}`. Auth-optional (matches the existing export endpoints).
- `POST /api/export/markdown` body `{markdown, title, format}` — ad-hoc render of cascade-generated content not yet saved to a diagram. Same return shape. Auth-optional.

The artefact GET endpoint `GET /api/artefacts/{artefact_id}` is **auth-optional** (matching `/api/images/{id}`) — artefacts are referenced by URL so anyone with the link can fetch them. This is the same model as image embeds. Future ADR can tighten this (signed URLs, time-bounded access) if needed.

### MCP tools

- `export_diagram(diagram_id: str, format: str)` — calls `POST /api/export/diagram/{diagram_id}` and returns the JSON.
- `render_markdown(markdown: str, title: str, format: str)` — calls `POST /api/export/markdown` and returns the JSON.

Both decorated by `with_web_url` so the `web_url` field is fully-qualified (matches ADR-175's pattern for `create_*` returns).

### Cascade prompt update

The Phase-1 docx/pdf fallback in `creation-cascade-destination-v1` is removed. The body now instructs the model: "When the user picks docx or pdf at Q-Dest3, call `render_markdown` for each selected format and present the returned `web_url` to the user as a clickable download link." A new migration applies this update to the seeded row; the seed function `seed_creation_prompts` is updated in lockstep.

The cross-set move fallback ("save into current set, move to target after v6.3.0") **stays** until Phase 3 ships `move_*` tools. Only the renderer-related fallback is dropped in v6.2.0.

## Why not extend the images store

- Image validation logic (magic-byte sniffing for PNG/JPEG/GIF/WebP) is tight; weakening it to accept arbitrary bytes for docx / pdf either erodes the safety net or grows a category-conditional branch that's almost a separate code path anyway.
- `POST /api/images` returning a successful response for a 200-KB DOCX is semantically wrong — clients reading the endpoint contract expect images.
- The two stores have distinct concerns: image uploads come from human paste-in-editor (5 MB cap, image-only); artefact storage comes from server-side render (25 MB cap, doc-only). Sibling modules keep each contract honest.
- A future "merge into one storage subsystem" decision is always available; over-investing in unification now ahead of a concrete use case is a Phase-7+ concern.

## Why store rendered artefacts at all (vs return inline base64)

- The user picked it: "store the file in Iris (we have a store for images, re-leverage that if suitable or extend) - this should apply by default for any docx or pdf generated not just big ones".
- Inline base64 has MCP message-size limits — a multi-MB PDF could be rejected by the client or transport.
- Storing produces a stable URL the user can share, re-download, or hand to other tools — same affordance as Iris's existing image embeds.
- The `web_url` decoration shipped in v6.0.15 is the natural delivery mechanism.

## Why no signed URLs / per-artefact ACLs yet

- The existing `GET /api/images/{id}` is anonymous-readable on the same rationale (referenced by URL in shared content).
- Tightening this is a separate decision worth a future ADR if real users / pen-tests surface the need.
- The artefact endpoint is auth-optional NOT for ergonomic reasons but because the predecessor establishes that pattern; future ADR can supersede.

## Consequences

- New SQLite migration `m{next}_artefacts_table.py` + Supabase mirror creating the `artefacts` table.
- New migration `m{next2}_drop_phase1_docx_fallback.py` + mirror UPDATEing `creation-cascade-destination-v1` to remove the renderer-related fallback paragraph.
- New module `backend/app/artefacts/` (models.py + service.py + router.py).
- New module `backend/app/export/renderers/` (markdown.py + docx.py + pdf.py + styles/iris.css).
- Three new dependencies: `markdown-it-py`, `weasyprint` (new), and `python-docx` is already at >=1.1.0 in pyproject.toml.
- Two new backend endpoints + one new GET (artefact download).
- Two new MCP tools.
- `mcp/src/iris_mcp/links.py` extended to decorate `export_diagram` + `render_markdown` returns with `web_url`.
- `mcp/src/iris_mcp/server_instructions.py:_FALLBACK_INSTRUCTIONS` updated.
- CHANGELOG `[6.2.0]`.
- Version bumps: mcp + frontend 6.1.0 → 6.2.0.
- **WeasyPrint deployment risk:** Render base image needs Pango, Cairo, GDK-PixBuf system libraries. Phase 2 verification per `feedback_render_deploy_verification` memory — curl the live `/api/export/markdown` endpoint after deploy. If 500s, update the Dockerfile to include the system deps before tagging the release.

## Verification

- `pytest backend/tests/export/test_md_to_docx.py` — md → docx → re-parse with `python-docx` → assert structure.
- `pytest backend/tests/export/test_md_to_pdf.py` — md → pdf → assert byte-header `%PDF` + page count.
- `pytest backend/tests/artefacts/test_store_roundtrip.py` — upload → URL → re-download → byte equality.
- `pytest mcp/tests/test_export_tools.py` — MCP tool returns URL, URL resolves, content matches.
- Manual UAT: cascade picks "Both" → md + docx + pdf → user receives three links → all download.

## See also

- [ADR-145] — existing image store, model from which the artefact store branches.
- [ADR-175] — web_url decoration on create_* tools, reused here.
- [ADR-176](ADR-176-Cascade-Shared-Base-Prompts.md) — destination chooser prompt this ADR actuates.
- [SPEC-179-A](specs/SPEC-179-A-Renderer-And-Artefact-Store.md) — schemas, endpoint signatures, dep versions, test plan.
- Anthropic skills `docx` + `pdf` at github.com/anthropics/skills — recipes for md → docx / pdf.
- [`docs/plans/issue-133-doview-mcp-polish.md`](../plans/issue-133-doview-mcp-polish.md) — multi-phase plan, this is Phase 2.
