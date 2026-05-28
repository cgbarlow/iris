# Plan — Unified Import Surface + Remote Import-by-URL MCP Tool + CLI (ADR-220)

**Status:** Backlogged to the release after v6.32.0. Deferred from the native
Sparx XMI work (ADR-219, shipped in v6.32.0, website-only).
**Tracking issue:** _(this plan is linked from its GitHub issue)_

---

## Context

As of v6.32.0 Iris imports five model formats, each via its own backend
endpoint, and the import UI dispatches by file extension (content-sniffing
`.xml` to separate Sparx native XMI from ArchiMate OEX):

| Format | Endpoint | Module |
|---|---|---|
| ArchiMate Open Exchange | `POST /api/import/archimate` | `backend/app/import_archimate/` |
| SparxEA database `.qea`/`.eap` | `POST /api/import/sparx` | `backend/app/import_sparx/` |
| SparxEA native XMI `.xml` | `POST /api/import/sparx-xml` | `backend/app/import_sparx_xml/` |
| DoView `.pptx` (+ batch) | `POST /api/import/pptx` | `backend/app/import_pptx/` |

Two gaps remain:

1. **The Iris MCP has no import tool at all** (verified: 56 tools, none for
   importing model files), and **the CLI has no import command.** The MCP is a
   remote Streamable-HTTP server (`iris-mcp.onrender.com`, ADR-134) that reaches
   the backend over HTTP and **cannot see the user's local files**. So AI agents
   and scripts cannot import models the way the website can.
2. There is no single source of truth for "import this file" — format dispatch
   is duplicated (frontend extension/content sniff + per-format endpoints).

This addresses both, completing Protocol §14 (write endpoints get MCP + CLI
parity) for the import surface and §13 (one dispatcher, one detector).

### Locked decisions (made during ADR-219 planning)
- **File delivery = URL fetch.** The `import_model` MCP tool takes a `source_url`
  (+ optional `set_id`); the **backend** downloads and imports. This is the only
  mechanism that works for the remote MCP across all formats including multi-MB
  binaries (`.qea`/`.eap`/`.pptx`) — inline base64 can't carry those.
- **Unified endpoint + CLI.** Add a content-sniffing `POST /api/import`
  dispatcher used by the frontend, the MCP tool, and a new `iris import` CLI
  command.

---

## Scope & deliverables

1. **ADR-220** (`docs/adrs/ADR-220-Unified-Import-Surface-and-Remote-Import-by-URL.md`)
   + **SPEC-220-A** (`docs/adrs/specs/SPEC-220-A-Unified-Import-Surface.md`).
   The SSRF threat model is the core of the ADR. Builds on ADR-148/182/134/133.
2. Unified backend dispatcher `POST /api/import`.
3. SSRF-hardened server-side URL download.
4. `iris-client.import_model` + MCP `import_model` tool.
5. `iris import` CLI command.
6. Frontend simplification (post everything to `/api/import`).
7. README + CHANGELOG + version bump; GitHub release.

---

## Architecture

The five per-format importer **services** already exist and stay. New code is a
thin dispatch + transport layer in front of them.

### New `backend/app/imports/` package
- `detect.py` — `detect_format(path) -> str | None` ∈ `{sparx_qea, sparx_eap,
  pptx, archimate_oex, sparx_xmi}`. Magic bytes: `SQLite format 3\x00`→qea;
  `PK\x03\x04`→pptx; JET/ACE signature→eap. Else XML: try `is_oex_file`
  **before** `is_sparx_xmi_file` (both start `<?xml`). Else `None`. Reuses the
  existing detectors `app.import_archimate.reader.is_oex_file` and
  `app.import_sparx_xml.reader.is_sparx_xmi_file`.
- `download.py` — `async fetch_to_temp(source_url, *, max_bytes=64*1024*1024,
  timeout=30.0) -> str`. SSRF safeguards (see below). Uses the existing
  `httpx>=0.27.0` backend dependency — no new dep.
- `router.py` — `APIRouter(prefix="/api/import")`, `POST ""`. Accepts **exactly
  one** of `file: UploadFile` (stream-chunked to a temp file) or
  `source_url: Form`, plus `set_id`. Validates `set_id`, wraps Supabase writes
  in `hold_connection()`, calls `detect_format`, dispatches to the matching
  importer service, returns a **unified summary** dict (`format` + the superset
  of all count fields, read via `getattr(summary, field, None)` so the differing
  summary dataclasses all serialise). `finally`: unlink temp(s).
- A shared `_dispatch_import_path(db, path, fmt, imported_by, set_id)` core; the
  existing per-format routers are refactored to delegate to it (DRY §13), keeping
  their endpoints + extension checks.
- Register in `backend/app/main.py` next to the other import routers.

### SSRF safeguards (the security-critical core — call out in ADR-220)
1. **Scheme allowlist:** `https` only (reject `http`/`file`/`ftp`/`gopher`/`data`).
2. **IP block:** resolve host via `getaddrinfo`; reject any resolved IP that is
   private / loopback / link-local / reserved / multicast / unspecified;
   explicitly block `169.254.169.254` and `fd00:ec2::254` (cloud metadata).
3. **Pin the vetted IP** for the connection to defeat DNS-rebinding TOCTOU
   (resolve → validate → connect to that IP with the original Host/SNI).
4. **Redirects:** `follow_redirects=False` (or re-validate every hop).
5. **Streaming size cap** to a `NamedTemporaryFile`; early-reject on
   `Content-Length`; abort past `max_bytes`.
6. **Timeout** on connect + read.
7. **Post-download sniff:** `detect_format`; if `None`, delete temp and 400 — so
   the server can't be coerced into importing arbitrary bytes.
8. Non-leaky `ValueError` → 400.

### `iris-client` (`iris-client/src/iris_client/client.py`)
`async def import_model(self, *, source_url, set_id=None) -> dict` →
`self._request("POST", "/api/import", data={...})`, returns the unified summary.

### MCP (`mcp/src/iris_mcp/tools.py`)
`import_model(source_url, set_id?)` tool: handler calls
`client.import_model(...)`; `IrisAuthError` → `_auth_required_payload`; result is
the JSON summary. Includes the shared destination-confirmation preamble.
Description states https-only URL fetch + supported formats + SSRF restriction.
Add a short import paragraph to `server_instructions.py`.

### CLI (`cli/src/iris_cli/main.py`)
Top-level `@app.command("import")` (function `import_cmd`): `file: Path` argument
XOR `--url`, plus `--set`. `file` → multipart POST to `/api/import` (CLI has
filesystem access); `--url` → `client.import_model(...)`. Prints via
`output.print_json`.

### Frontend (`frontend/src/routes/import/+page.svelte`)
Simplify single-file uploads to POST everything to `/api/import` (drop the
client-side extension/content-sniff dispatch added in v6.32.0; the backend now
detects). Keep `/api/import/pptx/batch` for multi-pptx. Update help text.

---

## Tests (TDD)
- `backend/tests/test_imports/`: `test_detect.py` (all five formats from tiny
  fixtures incl. the synthetic XMI, a `.qea`, a `PK\x03\x04` stub, an OEX file, a
  bogus blob → None); `test_router.py` (upload each format to `/api/import`,
  assert `format` + counts; reject both/neither of file/source_url; bad set_id;
  auth); `test_download_ssrf.py` (reject `http://`, `file://`, metadata IP,
  `localhost`, private IP, oversize via mocked stream, unrecognised bytes; assert
  temp cleanup).
- `iris-client/tests/`: `import_model` form body + round-trip (respx).
- `mcp/tests/`: `import_model` in `tool_definitions()`, schema, happy path, 401,
  preamble.
- `cli/tests/`: `iris import <file>` and `iris import --url`.
- `frontend/tests/unit/`: update the dispatch tests for the unified endpoint.

## Surface parity & migrations
- `scripts/check_surface_parity.py` only scans known-entity routers, so the new
  `imports` router + `import_model` tool + `iris import` command don't trip it.
  MCP + CLI are added voluntarily for §14 spirit.
- No DB migration — writes go through existing `create_*` services (§15).

## Release
- Bump the four version files together (frontend/package.json, backend/mcp/
  iris-client pyproject.toml). CHANGELOG `[Unreleased]` → Added + Security
  (SSRF-hardened URL download). Publish a GitHub release.

## Verification
- Backend: `pytest tests/test_imports tests/test_import_*` ; full regression.
- `python3 scripts/check_surface_parity.py` (expect clean).
- `iris-client`/`mcp`/`cli` pytest; frontend unit + check + lint.
- Manual: import the GEANZ XMI via the UI (still works), via `import_model` by a
  public https URL, and via `iris import`; verify an SSRF attempt
  (`source_url="http://169.254.169.254/..."`) is rejected 400; run
  `/security-review` on `backend/app/imports/download.py`.

## Risks
- **SSRF TOCTOU / DNS rebinding** is the sharpest risk — implement resolve-then-
  pin-IP + redirect rejection, not just IP-class checks. Security review required.
- OEX-vs-XMI sniff order (`is_oex_file` first).
- Stream uploads to temp (don't buffer multi-MB files in memory).
