# iris-cli

Command-line interface for Iris. Read-only + AI surface (ADR-130).

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

iris whoami
iris search "payment"
iris diagrams list
iris export diagram <id> --format markdown -o overview.md
iris ask "Summarise the onboarding flow" --set default
```

Configuration resolution order (first match wins):
1. CLI flag (`--url`, `--token`)
2. Environment (`IRIS_URL`, `IRIS_TOKEN`)
3. `~/.config/iris/config.toml`
4. Anonymous defaults (`http://localhost:8000`, no token)

Use `--json` on any command for machine-parsable output.

See [ADR-130](../docs/adrs/ADR-130-CLI-Architecture.md) and
[SPEC-130-A](../docs/adrs/specs/SPEC-130-A-CLI.md) for the full design.
