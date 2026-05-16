# SPEC-182-A: Surface parity discipline

ADR: [ADR-182](../ADR-182-Surface-Parity-Discipline.md)

## Summary

Build `scripts/check_surface_parity.py` and wire it into CI. Add §14 to `docs/protocols.md`. Document deliberate asymmetries.

## Script

`scripts/check_surface_parity.py`:

- Walks `backend/app/*/router.py` and collects every `@router.{post,put,patch,delete}("…", …)` decorator → set of `(entity, verb, path)` tuples.
- Walks `mcp/src/iris_mcp/tools.py` and collects every `Tool(name="…", …)` entry whose name starts with `create_`, `update_`, `move_`, `delete_`.
- Walks `cli/src/iris_cli/main.py` and collects every `@create_app.command`, `@update_app.command`, `@move_app.command`, `@delete_app.command` decorator.
- Cross-references the three sets. Reports:
  - **Hard violations** (exit 1): any write entity verb that exists in one surface but not the others (excluding listed asymmetries).
  - **Soft report** (exit 0 with stdout): read parity coverage, plus a "documented asymmetry" list.
- Second pass: greps every Python file outside `backend/app/export/renderers/` for `weasyprint` and `from docx import` — if either appears outside the renderer module, exit 1 with a DRY violation.

### Documented asymmetries

Hardcoded constant in the script:

```python
DOCUMENTED_ASYMMETRIES = [
    # (surface_present, surface_absent, name, reason_ref)
    ("cli", "mcp", "ask", "ADR-168"),
    ("backend", "all", "delete_*", "out-of-scope-issue-133"),
    ("all", "all", "move_element", "ADR-178-invariant"),
    ("backend", "all", "cross_set_move_diagram", "ADR-178-deferred"),
    ("backend", "all", "cross_set_move_package", "ADR-178-deferred"),
]
```

When a violation matches a documented asymmetry, it's downgraded to a soft warning.

## CI workflow

`.github/workflows/parity-check.yml`:

```yaml
name: Surface parity
on:
  pull_request:
    paths:
      - 'backend/app/**/router.py'
      - 'mcp/src/iris_mcp/tools.py'
      - 'cli/src/iris_cli/main.py'
      - 'scripts/check_surface_parity.py'
      - '.github/workflows/parity-check.yml'

jobs:
  parity:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python3 scripts/check_surface_parity.py
```

Python-only — no extra deps, runs in seconds.

## Protocols update

`docs/protocols.md` gains:

```markdown
## 14. Surface Parity

**Every backend write endpoint MUST have a matching MCP tool AND a
matching CLI subcommand.**

Enforced by `scripts/check_surface_parity.py` (runs in CI on every
PR). Documented asymmetries (CLI `ask`, no `delete_*`, no
`move_element`, no cross-set moves) are codified in the script's
exception list. See [ADR-182](./adrs/ADR-182-Surface-Parity-Discipline.md).
```

`CLAUDE.md` gains a one-liner under "Development Protocols":

```markdown
- §14 Surface Parity: every backend write endpoint needs an MCP tool
  + CLI subcommand. See ADR-182.
```

## Tests

The script itself is the test. Manual verification:

- Run against the current main tree → exit 0, prints "✅ Parity clean".
- Add a fake `@router.delete("/api/delete-test")` somewhere → run script → exit 1, lists the missing MCP / CLI counterparts.
- Revert the fake endpoint.

## Versioning

`mcp/pyproject.toml`: 6.5.0 → 6.6.0.
`frontend/package.json`: matched 6.6.0.

## CHANGELOG

`[6.6.0]` Added: parity check script + CI gate. Changed: protocols.md §14 added; CLAUDE.md references the rule. This is the final phase of issue #133.

## Acceptance criteria

- [ ] `python3 scripts/check_surface_parity.py` exits 0 against `main` after Phase 6 lands.
- [ ] CI workflow file exists and references the script.
- [ ] Protocols §14 + CLAUDE.md reference present.
- [ ] DRY check passes (no `weasyprint` / `python-docx` imports outside the renderer module).
