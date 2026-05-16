# iris-cli

Command-line interface for Iris. Read-only + write + AI surface
(ADR-130 + ADR-180 v6.4.0).

## Install (from repo)

```sh
uv tool install --from . iris-cli
```

Or from a repo URL:

```sh
uv tool install "git+https://github.com/cgbarlow/iris#subdirectory=cli"
```

## Quickstart

```sh
# Point at a running Iris backend and log in. `iris login` creates a
# Personal Access Token for you and stores it in ~/.config/iris/config.toml.
iris login --url https://iris.example.com

# Read
iris whoami
iris search "payment"
iris diagrams list
iris export diagram <id> --format markdown -o overview.md
iris ask "Summarise the onboarding flow" --set default

# Write (v6.4.0, ADR-180)
iris create set --name "My Set" --collection-id <col-id>
iris create diagram --name "Overview" --diagram-type simple --set-id <set-id> \
  --data-json '{"nodes": [], "edges": []}'

iris update set <set-id> --description "Updated"        # partial update
iris update diagram <diag-id> --change-summary "fixed labels"
iris update element <el-id> --package-id <pkg-id>       # v6.7.0 ADR-184
iris update element <el-id> --package-id null           # clear membership
iris elements list --package-id <pkg-id>                # filter by package
iris elements list --package-id null                    # list unmembered
iris packages list-elements <pkg-id>                    # all members of a pkg

iris move diagram <diag-id> --to-package <pkg-id>       # in-set re-parent
iris move diagram <diag-id> --to-package null           # move to set root
iris move set <set-id> --to-collection <new-col-id>     # cross-collection
iris move set <set-id> --to-collection null             # un-group

iris render diagram <diag-id> --format pdf -o out.pdf   # store artefact + download
iris render markdown --title T --format docx --input notes.md -o notes.docx
```

### `iris ask` is CLI-only by design

ADR-168 removed `ask` from the MCP surface because MCP clients bring
their own LLM. CLI users don't, so `iris ask` stays. This is a
deliberate asymmetry — documented in ADR-180 and the Phase 6 parity
matrix.

Configuration resolution order (first match wins):
1. CLI flag (`--url`, `--token`)
2. Environment (`IRIS_URL`, `IRIS_TOKEN`)
3. `~/.config/iris/config.toml`
4. Anonymous defaults (`http://localhost:8000`, no token)

Use `--json` on any command for machine-parsable output.

See [ADR-130](../docs/adrs/ADR-130-CLI-Architecture.md) and
[SPEC-130-A](../docs/adrs/specs/SPEC-130-A-CLI.md) for the full design.
