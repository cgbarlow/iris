"""token_store tests (ADR-160, SPEC-160-A).

Verifies the on-disk PAT cache used by iris-mcp:

- file path is a stable hash of the Iris URL (multi-instance safety)
- save creates parent dir, writes file mode 0600
- load returns the token when fresh
- load returns None when missing
- load returns None when the stored expires_at is in the past
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from iris_mcp import token_store


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    return tmp_path


class TestPath:
    def test_path_is_stable_and_url_specific(self, home: Path) -> None:
        a = token_store.token_file_path("https://iris-a.example.com")
        b = token_store.token_file_path("https://iris-b.example.com")
        a_again = token_store.token_file_path("https://iris-a.example.com")
        assert a == a_again
        assert a != b
        assert a.parent == home / ".iris-mcp"


class TestSaveLoad:
    def test_save_creates_dir_and_file_mode_0600(self, home: Path) -> None:
        path = token_store.save_token(
            "https://iris.test",
            "iris_pat_abcd1234_secret",
            expires_at="2099-01-01T00:00:00+00:00",
        )
        assert path.exists()
        mode = path.stat().st_mode & 0o777
        # macOS / Linux file mode — best-effort 0600.
        assert mode == 0o600, f"expected 0600, got {oct(mode)}"
        dir_mode = path.parent.stat().st_mode & 0o777
        assert dir_mode == 0o700, f"expected 0700, got {oct(dir_mode)}"

    def test_save_then_load_roundtrips_token(self, home: Path) -> None:
        token_store.save_token(
            "https://iris.test",
            "iris_pat_abcd1234_secret",
            expires_at="2099-01-01T00:00:00+00:00",
        )
        loaded = token_store.load_token("https://iris.test")
        assert loaded == "iris_pat_abcd1234_secret"

    def test_load_missing_returns_none(self, home: Path) -> None:
        assert token_store.load_token("https://does-not-exist.test") is None

    def test_load_expired_returns_none(self, home: Path) -> None:
        past = (datetime.now(tz=UTC) - timedelta(days=1)).isoformat()
        token_store.save_token(
            "https://iris.test", "iris_pat_abcd1234_secret", expires_at=past,
        )
        assert token_store.load_token("https://iris.test") is None

    def test_load_with_no_expires_at_returns_token(self, home: Path) -> None:
        """PAT-paste path persists expires_at=None — backend owns expiry."""
        token_store.save_token(
            "https://iris.test", "iris_pat_abcd1234_secret", expires_at=None,
        )
        assert token_store.load_token("https://iris.test") == "iris_pat_abcd1234_secret"

    def test_load_corrupt_file_returns_none(self, home: Path) -> None:
        path = token_store.token_file_path("https://iris.test")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("this is not json", encoding="utf-8")
        assert token_store.load_token("https://iris.test") is None

    def test_save_overwrites_existing(self, home: Path) -> None:
        token_store.save_token("https://iris.test", "first", expires_at=None)
        token_store.save_token("https://iris.test", "second", expires_at=None)
        assert token_store.load_token("https://iris.test") == "second"

    def test_payload_includes_iris_url(self, home: Path) -> None:
        path = token_store.save_token(
            "https://iris-uat.chrisbarlow.nz", "iris_pat_abcd1234_secret",
            expires_at=None,
        )
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["iris_url"] == "https://iris-uat.chrisbarlow.nz"
        assert payload["token"] == "iris_pat_abcd1234_secret"
