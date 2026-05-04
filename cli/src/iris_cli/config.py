"""Config resolution for the iris CLI (SPEC-130-A).

Order (first match wins):
1. CLI flag value
2. Environment (`IRIS_URL`, `IRIS_TOKEN`)
3. `~/.config/iris/config.toml` (or `$XDG_CONFIG_HOME/iris/config.toml`)
4. Defaults (`http://localhost:8000`, anonymous)
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_URL = "http://localhost:8000"


@dataclass(frozen=True)
class CliConfig:
    url: str
    token: str | None
    source_file: Path | None  # Where the file-based config was loaded from, or None.


def config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "iris" / "config.toml"


def load(url_flag: str | None = None, token_flag: str | None = None) -> CliConfig:
    """Resolve the effective config for this invocation."""
    file_url: str | None = None
    file_token: str | None = None
    source: Path | None = None

    path = config_path()
    if path.is_file():
        source = path
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
        default = data.get("default", {}) if isinstance(data, dict) else {}
        file_url = default.get("url") if isinstance(default, dict) else None
        file_token = default.get("token") if isinstance(default, dict) else None

    url = (
        url_flag
        or os.environ.get("IRIS_URL")
        or file_url
        or DEFAULT_URL
    )
    token = (
        token_flag
        if token_flag is not None
        else os.environ.get("IRIS_TOKEN") or file_token
    )
    return CliConfig(url=url, token=token, source_file=source)


def save(url: str, token: str) -> Path:
    """Persist `url` + `token` to `~/.config/iris/config.toml` with 0600."""
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # TOML doesn't quote values we write — escape quotes in case of unusual input.
    safe_url = url.replace('"', '\\"')
    safe_token = token.replace('"', '\\"')
    content = f'[default]\nurl = "{safe_url}"\ntoken = "{safe_token}"\n'
    path.write_text(content, encoding="utf-8")
    path.chmod(0o600)
    return path
