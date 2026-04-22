"""Unit tests for config resolution order (SPEC-130-A)."""

from __future__ import annotations

from pathlib import Path

import pytest

from iris_cli import config as cfg


class TestLoadOrder:
    def test_flags_win(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("IRIS_URL", "http://env")
        monkeypatch.setenv("IRIS_TOKEN", "env-token")
        result = cfg.load(url_flag="http://flag", token_flag="flag-token")
        assert result.url == "http://flag"
        assert result.token == "flag-token"

    def test_env_beats_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        (tmp_path / "iris").mkdir()
        (tmp_path / "iris" / "config.toml").write_text(
            '[default]\nurl = "http://file"\ntoken = "file-token"\n',
        )
        monkeypatch.setenv("IRIS_URL", "http://env")
        monkeypatch.setenv("IRIS_TOKEN", "env-token")
        result = cfg.load()
        assert result.url == "http://env"
        assert result.token == "env-token"

    def test_file_beats_default(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        (tmp_path / "iris").mkdir()
        (tmp_path / "iris" / "config.toml").write_text(
            '[default]\nurl = "http://file"\ntoken = "file-token"\n',
        )
        monkeypatch.delenv("IRIS_URL", raising=False)
        monkeypatch.delenv("IRIS_TOKEN", raising=False)
        result = cfg.load()
        assert result.url == "http://file"
        assert result.token == "file-token"

    def test_default_when_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        monkeypatch.delenv("IRIS_URL", raising=False)
        monkeypatch.delenv("IRIS_TOKEN", raising=False)
        result = cfg.load()
        assert result.url == cfg.DEFAULT_URL
        assert result.token is None


class TestSave:
    def test_writes_0600(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        path = cfg.save("http://example.com", "iris_pat_xyz")
        assert path == tmp_path / "iris" / "config.toml"
        mode = path.stat().st_mode & 0o777
        assert mode == 0o600, f"expected 0600, got {oct(mode)}"
        content = path.read_text()
        assert 'url = "http://example.com"' in content
        assert 'token = "iris_pat_xyz"' in content

    def test_roundtrip(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        monkeypatch.delenv("IRIS_URL", raising=False)
        monkeypatch.delenv("IRIS_TOKEN", raising=False)
        cfg.save("http://rt.example", "iris_pat_rt")
        loaded = cfg.load()
        assert loaded.url == "http://rt.example"
        assert loaded.token == "iris_pat_rt"
