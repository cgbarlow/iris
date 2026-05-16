# ADR-182: CLI / API / MCP surface parity discipline

Status: Accepted (2026-05-16)
Meta-ADR — cross-references ADR-178, ADR-179, ADR-180, ADR-181.

## Context

Issue #133's Class B feedback called out parity drift between the backend HTTP API, the MCP tool surface, and the `iris` CLI:

- MCP had `create_*` but no `update_*` / `move_*` until ADR-178 / v6.3.0.
- CLI had read + `ask` + `export` only until ADR-180 / v6.4.0.
- The render path lived in three places (or was missing) until ADR-179 / v6.2.0 + ADR-181 / v6.5.0 unified it.

Phases 2–5 of the multi-phase plan (`docs/plans/issue-133-doview-mcp-polish.md`) closed those gaps. Phase 6 codifies the rule going forward so the next backend write endpoint added doesn't quietly skip MCP and CLI.

## Decision

**Every backend write endpoint MUST have a matching MCP tool AND a matching CLI subcommand.**

"Write endpoint" means anything that mutates state: `POST` / `PUT` / `PATCH` / `DELETE` on a domain entity. Read endpoints (`GET`) are out of scope — parity for reads is reported but not enforced (different surfaces have different read affordances; matching them rigidly would over-constrain).

A `scripts/check_surface_parity.py` script encodes the rule by parsing:

- backend routers (`backend/app/*/router.py`) for `@router.{post,put,patch,delete}` decorators.
- MCP tool registrations (`mcp/src/iris_mcp/tools.py`) for entries in the `TOOLS` list.
- CLI commands (`cli/src/iris_cli/main.py`) for `@*_app.command("...")` decorators.

The script reports two views:
- **Hard gate (write parity)** — every write-tool name pattern (`create_*`, `update_*`, `move_*`, `delete_*`) must appear in all three layers (where applicable). CI fails on a write-parity diff.
- **Soft report (read parity + deliberate asymmetries)** — printed for visibility but not gated. Documented asymmetries (CLI `ask`; absence of `delete_*`; absence of `move_element`) are listed as `intended` to suppress noise.

A second check enforces the DRY discipline from protocols §13: the md → docx and md → pdf renderers exist only in `backend/app/export/renderers/`. No other module may import `python-docx` or `weasyprint` for rendering. The frontend's removed jsPDF path is no longer in scope (Phase 5 removed it).

### CI gate

The script runs as a GitHub Action workflow on every PR. Exit code 0 = clean, exit code 1 = write parity violation. The workflow lives at `.github/workflows/parity-check.yml`.

### Documented asymmetries

| Surface gap | Reason | Where documented |
|---|---|---|
| `iris ask` is CLI-only (no MCP tool) | MCP clients bring their own LLM (ADR-168); CLI users don't | ADR-180, `cli/README` |
| No `delete_*` anywhere | Out of scope for issue #133 — needs a separate ADR (audit trail, undo, soft vs hard delete) | This ADR, plan §16 |
| No `move_element` | Elements are owned by their parent diagram and travel with it; cross-diagram element moves are a non-feature (ADR-178 invariant) | ADR-178, this ADR |
| Cross-set `move_diagram` / `move_package` | Backend `/parent` endpoints are in-set only; cross-set requires a `create_*` + re-save round trip | ADR-178, this ADR |

The parity script flags each as `intended` so they don't register as defects.

### Protocols update

`docs/protocols.md` gains a §14 "Surface Parity" with a one-line reference to this ADR.

`CLAUDE.md` gains a corresponding parity-rule reference so future code generation respects it.

## Why a script, not just review discipline

- Reviewers miss things. The 18 months between v5.16.0 (`create_*` in MCP) and v6.3.0 (`update_*` in MCP) is the evidence.
- A script gives a yes/no answer that doesn't depend on which reviewer is on rotation.
- The cost is one Python file (~150 LoC) and one CI workflow. Cheap.

## Why only write parity is gated

- Read endpoints serve different audiences differently. The backend has internal admin endpoints (`/api/admin/...`) that don't belong on MCP. The CLI has `iris search` that bundles a search call with pretty-printing — there's no equivalent MCP tool because MCP clients format their own. Gating reads would either require many `intended` exceptions or force false-parity.
- Writes are different. Every write mutates shared state; every surface should reach it.

## Why not also gate the prompt content (cascade prompts, MCP server instructions)

- Out of scope for parity — those are content, not API surface. Drift in prompt content is caught by the static-parser tests in `backend/tests/test_migrations/test_phase{1,2,3}_*_schema.py` which assert each migration's content matches the seed and the canonical doc.

## Consequences

- New `scripts/check_surface_parity.py` (~150 LoC).
- New `.github/workflows/parity-check.yml` running the script on every PR.
- `docs/protocols.md` §14 added.
- `CLAUDE.md` parity-rule reference added.
- `docs/plans/issue-133-doview-mcp-polish.md` retroactively annotated as "complete" with all six phases shipped.
- CHANGELOG `[6.6.0]`.
- Version bumps: mcp + frontend 6.5.0 → 6.6.0.

## Verification

- `python3 scripts/check_surface_parity.py` exits 0 against the current tree (Phases 1–5 produced full parity).
- A deliberately-broken PR (e.g. adding an MCP tool with no CLI counterpart) makes the CI gate fail.
- The DRY check passes: no module outside `backend/app/export/renderers/` imports `weasyprint` or invokes `markdown-it-py` for HTML rendering.

## See also

- [ADR-178](ADR-178-MCP-Update-Move-Tools.md)
- [ADR-179](ADR-179-Renderer-And-Artefact-Store.md)
- [ADR-180](ADR-180-CLI-Write-Tool-Parity.md)
- [ADR-181](ADR-181-Unified-Diagram-Export-GUI.md)
- [SPEC-182-A](specs/SPEC-182-A-Surface-Parity-Discipline.md)
- [`docs/protocols.md`](../protocols.md) §14
- Issue #133
