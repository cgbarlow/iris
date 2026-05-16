# Issue #133 — deploy verification checklist

Step-by-step verification for the v6.1.0 → v6.6.1 release line that
shipped the issue #133 multi-phase plan. Run these against the
deployed env after Render finishes the rebuild triggered by each tag.

Hosts referenced below:

- **Backend (iris-api):** `https://iris-api-gtb3.onrender.com`
- **MCP (iris-mcp):** `https://iris-mcp.onrender.com`
- **Frontend:** `https://iris.chrisbarlow.nz` (or wherever the build is hosted)
- **Supabase:** `db.<your-project-ref>.supabase.co` — direct connection on port 5432

If the backend / MCP / frontend hosts differ from the above, substitute.

## 1. Apply Supabase migrations

Five new SQL files, run in order via the **Supabase dashboard → SQL Editor** (paste each, run, repeat):

1. `backend/app/migrations/supabase/m062_cascade_ux_polish.sql`
2. `backend/app/migrations/supabase/m063_mcp_user_question_rule.sql`
3. `backend/app/migrations/supabase/m064_artefacts_table.sql`
4. `backend/app/migrations/supabase/m065_drop_phase1_docx_fallback.sql`
5. `backend/app/migrations/supabase/m066_drop_phase1_move_fallback.sql`

Order matters — m065 and m066 patch the row m062 created.

Or, if you have `psql` installed locally:

```sh
sudo apt-get install -y postgresql-client   # if missing
./scripts/supabase-migrate.sh "postgresql://postgres:<PASSWORD>@db.<PROJECT>.supabase.co:5432/postgres"
```

The script applies every `m*.sql` in the directory; all migrations are idempotent (`ON CONFLICT DO NOTHING`, `IF NOT EXISTS`, `REPLACE()`-based UPDATEs) so re-running is safe.

## 2. Redeploy the backend

Render dashboard → trigger redeploy of **iris-api** (or push to main if auto-deploy is wired). The `seed_creation_prompts` function runs on startup and re-applies the canonical prompt content for:

- the three new shared cascade base prompts (`creation-cascade-{shared,citations,destination}-v1`)
- the refreshed `creation-doview-notation-v1` and `creation-outcomes-map-v1`
- the refreshed `mcp-server-instructions-v1` (now also seeded on every startup as of v6.1.0)

⚠️ If you've previously hand-edited any of these in `/admin/settings/ai`, the seed will overwrite your customisations. The seed file constants are now the source of truth.

## 3. Verify WeasyPrint deps on Render

The Phase 2 renderer needs Pango / Cairo / GDK-PixBuf system libraries. The v6.6.1 Dockerfile installs them; verify the rebuild picked them up:

```sh
curl -X POST https://iris-api-gtb3.onrender.com/api/export/markdown \
  -H "Content-Type: application/json" \
  -d '{"markdown":"# Test","title":"Test","format":"pdf"}'
```

- **200** with JSON containing `id`, `filename`, `mime_type=application/pdf`, `web_url` → ✅ Renderer fully live
- **500 Internal Server Error** → Pango/Cairo/GDK-PixBuf still missing; check the Render build log for an `OSError: cannot load library` from `weasyprint`. Confirm `backend/Dockerfile` is at v6.6.1 content, then re-trigger the deploy.

When the curl returns 200, fetch the artefact to confirm the bytes are a real PDF:

```sh
ART_ID=$(curl -s -X POST https://iris-api-gtb3.onrender.com/api/export/markdown \
  -H "Content-Type: application/json" \
  -d '{"markdown":"# Test","title":"Test","format":"pdf"}' | jq -r .id)
curl -s https://iris-api-gtb3.onrender.com/api/artefacts/$ART_ID | head -c 4
# Expect: %PDF
```

## 4. Verify MCP-side parity

```sh
# MCP version
curl https://iris-mcp.onrender.com/info | jq .version
# Expect: "6.6.0" or "6.6.1"

# MCP instructions include ASKING QUESTIONS (ADR-177 / v6.1.0)
curl -s -X POST https://iris-mcp.onrender.com/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"0"}}}' \
  | jq -r .result.instructions | grep "ASKING QUESTIONS"
# Expect: ASKING QUESTIONS.
```

If MCP is below 6.6.0, redeploy iris-mcp on Render. Stdio MCP users (Claude Desktop / Claude Code via `uvx`) pick up the new version automatically on next session restart.

## 5. Verify the backend prompt seed

```sh
curl -s https://iris-api-gtb3.onrender.com/api/ai/server-instructions \
  | jq -r .body | grep "ASKING QUESTIONS"
# Expect: ASKING QUESTIONS.

# Composed creation cascade for DoView outcomes_map includes the new shared sections
curl -s "https://iris-api-gtb3.onrender.com/api/ai/response-prompts/composed?notation=doview&diagram_type=outcomes_map&purpose=creation_format" \
  | jq -r .body | grep -E "(AskUserQuestion|Author/Org|Save where|This-Then)"
# Expect: all four matches (shared / citations / destination / DoView notation)

# Cross-notation generality proof — BPMN cascade also gets the shared rules
curl -s "https://iris-api-gtb3.onrender.com/api/ai/response-prompts/composed?notation=bpmn&purpose=creation_format" \
  | jq -r .body | grep -E "(AskUserQuestion|Save where|Author/Org)"
# Expect: all three matches — proves the shared cascade isn't accidentally DoView-shaped
```

## 6. Manual UAT — the acceptance gates each phase called out

Each phase's release notes list these; they need a human against a connected MCP client.

### Phase 1 — banana-monoculture regression

Open Claude Desktop / Claude Code with the iris MCP connector configured. Open the Outcomes Theory Book set. Run a fresh DoView creation cascade ("create a DoView about something"). Verify:

- Every cascade question fires via the client's question tool (AskUserQuestion chips), NOT prose
- Q1 (info source) offers three options including "I will paste my own content" / "I will attach a file"
- Q2 (name) proposes a default like "X DoView" and offers Keep / Use different
- After Stage 1 confirms, the skip-detail question fires with Skip / Review / Refine (default Skip)
- After Stage 2, the destination chooser fires (Iris / artefacts / both)

### Phase 1 generality — BPMN cascade

Start a fresh BPMN creation cascade (not DoView). Confirm the same shared questions fire (info source, default name, skip-detail, destination). This is the cross-notation proof — without it we're shipping a "generic" prompt that only happens to work on DoView.

### Phase 2 — renderer round-trip

In the destination chooser, pick "Both" + check Markdown + Docx + PDF. Verify three downloadable URLs come back, each starts with `https://iris-api-gtb3.onrender.com/api/artefacts/<id>`, and each opens cleanly when clicked (markdown in browser, docx in Word, pdf in any viewer).

### Phase 3 — move recovery

Deliberately save a new bundle to the wrong set via the destination chooser. Then ask the model: "actually move it to the X set". Verify the model calls `move_diagram` / `move_set` (not `create_*` + delete) and the bundle relocates without losing its element IDs / history.

### Phase 4 — CLI parity smoke

```sh
iris login --url https://iris-api-gtb3.onrender.com --token iris_pat_...
iris create set --name "CLI Smoke Test" --collection-id <some-collection>
iris move set <returned-set-id> --to-collection null  # un-group
iris render markdown --title "CLI" --format pdf -o /tmp/cli.pdf <<< "# Hello"
file /tmp/cli.pdf  # expect: PDF document
```

### Phase 5 — GUI export

Open any markdown-content diagram (e.g. a doview_analysis page) in `https://iris.chrisbarlow.nz`. Click Export → PDF. Verify the download is a real text PDF (not a screenshot of the markdown viewer). For a visual diagram, confirm SVG/PNG still produce the canvas screenshot.

### Phase 6 — parity check

```sh
python3 scripts/check_surface_parity.py
# Expect: ✅ Parity clean
```

CI runs this on every PR that touches a router, the MCP tools file, the CLI main file, the renderer module, or the script itself (`.github/workflows/parity-check.yml`).

## What if something fails

- **Phase 2 curl returns 500 with WeasyPrint error** → confirm v6.6.1 Dockerfile changes are in the deployed image; check Render build logs for the `apt-get install` step.
- **MCP version still 6.0.x** → iris-mcp service didn't redeploy; trigger manually in Render.
- **Cascade still asks prose questions** → backend didn't redeploy, or seed function failed (check startup logs for `[AI_CREATION] seed_creation_prompts skipped on Supabase`).
- **`creation-cascade-*-v1` rows missing in the DB** → migrations didn't run; re-apply m062 via SQL Editor.

## Reference

- [Plan](./plans/issue-133-doview-mcp-polish.md)
- [Releases](https://github.com/cgbarlow/iris/releases) — v6.1.0 through v6.6.1
- ADRs 176–182 in `docs/adrs/`
- Issue [#133](https://github.com/cgbarlow/iris/issues/133)
