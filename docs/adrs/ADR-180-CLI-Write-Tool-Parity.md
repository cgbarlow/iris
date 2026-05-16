# ADR-180: CLI write-tool parity with MCP

Status: Accepted (2026-05-16)
Extends: ADR-130 (CLI), ADR-161, ADR-178, ADR-179

## Context

Before Phase 4 of issue #133, the `iris` CLI surface was:

| Group | Verbs |
|---|---|
| `diagrams` | list, get, versions |
| `elements` | list, get |
| `packages` | list, get |
| `sets` | list, get |
| `collections` | list, get |
| `export` | diagram / element / package / set / collection (json or markdown) |
| `conversations` | list |
| (top-level) | login, whoami, search, ask |

That's read-only + `ask` (LLM) + `export` (read serialisation). MCP, meanwhile, had `create_*` (v5.16.0–v5.17.0), `update_*` + `move_*` (v6.3.0 / ADR-178), `render_*` (v6.2.0 / ADR-179). The drift is exactly what the issue #133 Class B feedback flagged.

The plan parity rule is: every backend write endpoint MUST have both an MCP tool AND a CLI subcommand. Phase 4 brings CLI to parity for the eight new write tools (5 update, 3 move) plus the two render tools.

## Decision

Add four new CLI sub-applications:

| App | Commands | Wraps |
|---|---|---|
| `iris create` | `collection`, `set`, `package`, `diagram` | MCP `create_*` |
| `iris update` | `collection`, `set`, `package`, `diagram`, `element` | MCP `update_*` |
| `iris move` | `diagram`, `package`, `set` | MCP `move_*` |
| `iris render` | `diagram`, `markdown` | MCP `render_diagram`, `render_markdown` |

Existing `iris export` group (read-only) is kept and unchanged; the new `iris render` group is a distinct verb for the v6.2.0 renderer pipeline that produces docx/pdf artefacts stored in Iris.

Each command calls the backend via `IrisClient._request` (the same HTTP path the MCP tools use). This keeps Phase 4 scope minimal — no iris-client typed surface expansion ahead of need. Phase 6's parity ADR may revisit.

### `iris ask` stays

The existing top-level `iris ask` command stays. ADR-168 removed `ask` from MCP because MCP clients bring their own LLM; CLI users don't. CLI `ask` is a deliberate asymmetry — documented here and in ADR-182. Phase 6's parity matrix marks it as `cli-only-by-design`.

### No `delete_*` yet

Both MCP and CLI lack `delete_*` write tools. Out of scope for issue #133 — needs a separate ADR (audit trail, undo, soft vs hard delete semantics).

## Why not factor a typed iris-client write surface first

The plan (SPEC-180-A) parks this as an open question: does iris-client get typed `update_*` / `move_*` / `render_*` methods, or do CLI + MCP both call `_request` directly?

Factoring now means:
- 10 new typed methods (5 update + 3 move + 2 render) in iris-client.
- ~3 new model classes (`Artefact`, `MoveResult`) added to `models/core.py`.
- Both MCP (Phase 3) and CLI (Phase 4) call sites updated to use the typed methods.

Deferring keeps Phase 4 scope minimal — CLI ships parity with shell-only changes, MCP stays as-is. Phase 6 can re-evaluate when the parity matrix is the live source of truth.

For Phase 4 we accept the trade: typed iris-client methods coexist with `_request`-direct callers in both CLI and MCP. Not the prettiest, but the parity outcome (every write endpoint reachable from every surface) is what the issue #133 feedback actually asked for.

## Consequences

- `cli/src/iris_cli/main.py` grows four new Typer sub-apps + their commands.
- Each command takes positional id + Typer `--option` style flags mirroring the MCP input schema.
- Tests cover happy path + the partial-update merge behaviour (CLI must do the same GET-then-PUT dance as the MCP tools).
- `cli/README.md` updated with the new commands + the deliberate `ask` asymmetry note.
- CHANGELOG `[6.4.0]`.
- Version bumps: mcp + frontend 6.3.0 → 6.4.0. (The CLI version lives in `cli/pyproject.toml`; bump it too.)

## Verification

- `pytest cli/tests/test_create_commands.py test_update_commands.py test_move_commands.py test_render_commands.py` green.
- Manual: `iris create set --name X` and `iris move set <id> --to-collection Y` against a running backend.

## See also

- [ADR-130](ADR-130-Iris-CLI.md) — original CLI design.
- [ADR-168](ADR-168-Remove-Ask-Tool-From-MCP-Surface.md) — context for the deliberate `ask` asymmetry.
- [ADR-178](ADR-178-MCP-Update-Move-Tools.md), [ADR-179](ADR-179-Renderer-And-Artefact-Store.md) — MCP tools this CLI mirrors.
- [SPEC-180-A](specs/SPEC-180-A-CLI-Write-Parity.md) — command signatures, tests.
- Issue #133.
