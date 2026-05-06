"""v5.5.0 (issue #48): unit tests for the extension upgrade scanner.

Tests run in dry-run mode so they don't actually open issues. The
GitHub API is mocked.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

# Add scripts/ to sys.path so we can import the script as a module.
SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

import check_extension_updates as cu  # noqa: E402


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        pass

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def test_is_newer_basic() -> None:
    assert cu.is_newer("2.0.0", "1.9.9") is True
    assert cu.is_newer("1.0.0", "1.0.0") is False
    assert cu.is_newer("1.0.0", "1.0.1") is False
    assert cu.is_newer("v2.5.0", "2.4.9") is True


def test_is_newer_tolerates_prerelease() -> None:
    # Numeric prefix is what wins; suffixes ignored.
    assert cu.is_newer("2.0.0-rc1", "1.5.0") is True
    assert cu.is_newer("1.0.0-beta", "1.0.0") is False  # numeric tail equal


def test_fetch_latest_release_returns_tag() -> None:
    payload = {
        "tag_name": "v2.0.0",
        "html_url": "https://github.com/x/y/releases/v2.0.0",
        "body": "Release notes",
    }
    with patch("check_extension_updates.urllib.request.urlopen", return_value=_FakeResponse(payload)):
        result = cu.fetch_latest_release("x", "y", token=None)
    assert result is not None
    assert result["tag_name"] == "v2.0.0"
    assert "v2.0.0" in result["html_url"]


def test_fetch_latest_release_404_returns_none() -> None:
    import urllib.error

    err = urllib.error.HTTPError(
        url="https://api.github.com/...",
        code=404,
        msg="Not Found",
        hdrs=None,  # type: ignore[arg-type]
        fp=None,
    )
    with patch("check_extension_updates.urllib.request.urlopen", side_effect=err):
        result = cu.fetch_latest_release("x", "y", token=None)
    assert result is None


def test_open_issue_dry_run_does_not_call_gh(monkeypatch) -> None:
    called: list[list[str]] = []

    def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        called.append(list(args[0]) if args else [])
        raise AssertionError("subprocess.run should not be called in dry-run")

    monkeypatch.setattr(cu.subprocess, "run", fake_run)

    msg = cu.open_issue_if_missing(
        extension_id="mnemos",
        extension_name="MNEMOS",
        installed="1.0.0",
        latest="2.0.0",
        release_url="https://github.com/ro0TuX777/MNEMOSv2/releases/v2.0.0",
        release_body="Big rewrite",
        dry_run=True,
    )
    assert "dry-run" in msg
    assert "Upgrade: mnemos extension" in msg
    assert called == []


def test_load_sources_includes_mnemos_with_v2_url() -> None:
    sources = cu.load_sources()
    assert "mnemos" in sources
    assert "MNEMOSv2" in sources["mnemos"]["source_url"]


def test_load_manifest_has_mnemos_baseline() -> None:
    manifest = cu.load_manifest()
    assert "mnemos" in manifest
