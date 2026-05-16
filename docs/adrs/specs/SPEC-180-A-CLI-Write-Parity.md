# SPEC-180-A: CLI write-tool parity with MCP

ADR: [ADR-180](../ADR-180-CLI-Write-Tool-Parity.md)

## Summary

Add four new Typer sub-apps to the `iris` CLI: `create`, `update`, `move`, `render`. Each command wraps the corresponding backend endpoint via `IrisClient._request`, matching the MCP tool surface from ADR-178 and ADR-179.

## Commands

### `iris create`

```
iris create collection --name X [--description ...]
iris create set --name X [--collection-id ...] [--description ...]
iris create package --name X [--set-id ...] [--parent-package-id ...]
                    [--description ...] [--metadata-json '{}']
iris create diagram --name X --diagram-type DT [--notation N]
                    [--set-id ...] [--parent-package-id ...]
                    [--data-json '{}'] [--description ...]
```

### `iris update` (partial — GET-then-merge-then-PUT)

```
iris update collection <id> [--name ...] [--description ...] [--system-prompt ...]
                            [--mcp-system-context ...] [--thumbnail-source ...]
                            [--thumbnail-diagram-id ...]
iris update set <id>        [same flags except --collection-id]
iris update package <id>    [--name ...] [--description ...] [--metadata-json '{}']
iris update diagram <id>    [--name ...] [--description ...] [--data-json '{}']
                            [--metadata-json '{}'] [--change-summary ...]
iris update element <id>    [--name ...] [--description ...] [--data-json '{}']
```

### `iris move`

```
iris move diagram <id> --to-package <pkg-id-or-`null`>
iris move package <id> --to-parent <pkg-id-or-`null`>
iris move set <id> --to-collection <col-id-or-`null`>
```

The `null` string literal denotes "set to NULL" (move to set root / un-group). Plain omission of the flag is an error.

### `iris render`

```
iris render diagram <diagram-id> --format md|docx|pdf [-o OUT_PATH]
iris render markdown --title X --format md|docx|pdf [-o OUT_PATH]
                     (markdown source from stdin or --input FILE)
```

Each render command POSTs to the new backend endpoint, gets back the `ArtefactResponse`, and either:
- prints the artefact metadata JSON (default), or
- if `-o` is given, downloads the artefact bytes from `/api/artefacts/<id>` and writes to the file.

## Partial-update semantics

CLI `update` commands do the same GET-then-merge-then-PUT dance as the MCP `update_*` tools (see SPEC-178-A). Reason: the backend PUT does full-replace, and we want true partial updates from the CLI without breaking unspecified fields.

## Tests

### `cli/tests/test_create_commands.py` (new)

Per-entity happy path via respx-mocked backend. Asserts the right POST body shape and successful JSON output.

### `cli/tests/test_update_commands.py` (new)

Per-entity happy path. Critical: assert the GET is made first to source the current name, then the PUT body merges the override.

### `cli/tests/test_move_commands.py` (new)

- `iris move diagram <id> --to-package pkg-7` → PUT /api/diagrams/<id>/parent with `{parent_package_id: "pkg-7"}`.
- `iris move diagram <id> --to-package null` → PUT with `{parent_package_id: null}`.
- `iris move set <id> --to-collection col-9` → PUT /api/sets/<id> preserves metadata + sets collection_id.
- `iris move set <id> --to-collection null` → un-groups.

### `cli/tests/test_render_commands.py` (new)

- `iris render markdown --title T --format md` reads stdin, POSTs, prints metadata.
- `iris render markdown --title T --format pdf -o out.pdf` downloads the PDF bytes to disk.
- `iris render diagram <id> --format docx -o out.docx` downloads the docx bytes.

## Versioning

`cli/pyproject.toml`: bump per the existing CLI versioning (look it up; if synced to the global v6 line then 6.3.0 → 6.4.0).
`mcp/pyproject.toml`: 6.3.0 → 6.4.0.
`frontend/package.json`: matched 6.4.0.

## CHANGELOG

`[6.4.0]` Added: `iris create` / `update` / `move` / `render` sub-apps. Documents the deliberate `iris ask` asymmetry.

## Acceptance criteria

- [ ] `pytest cli/tests/test_{create,update,move,render}_commands.py` green.
- [ ] `iris create set --name X` against a live backend succeeds.
- [ ] `iris update set <id> --description "new"` does GET-then-PUT.
- [ ] `iris move set <id> --to-collection col-7` succeeds.
- [ ] `iris render markdown --title T --format pdf -o out.pdf` writes a valid PDF.
- [ ] `iris ask "test question" --set <id>` still works.
