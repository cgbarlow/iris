"""Shared fixtures for CLI tests."""

from __future__ import annotations

from pathlib import Path

import pytest
import respx


@pytest.fixture
def respx_mock() -> respx.Router:
    with respx.mock(assert_all_called=False) as router:
        yield router


@pytest.fixture(autouse=True)
def _anon_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Force a clean config so tests don't pick up the developer's
    ~/.config/iris/config.toml or env vars."""
    monkeypatch.setenv("IRIS_URL", "http://iris.test")
    monkeypatch.delenv("IRIS_TOKEN", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
