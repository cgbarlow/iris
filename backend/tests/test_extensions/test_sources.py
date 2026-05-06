"""v5.5.0 (issue #48): test the shared extension source registry."""

from __future__ import annotations

from app.extensions.sources import get_known_sources, get_source


def test_known_sources_includes_mnemos_scenia_docref() -> None:
    sources = get_known_sources()
    assert "mnemos" in sources
    assert "scenia" in sources
    assert "docref" in sources


def test_mnemos_points_at_mnemosv2() -> None:
    src = get_source("mnemos")
    assert src is not None
    assert src["source_method"] == "github"
    assert "MNEMOSv2" in src["source_url"]
    assert src["github_owner"] == "ro0TuX777"
    assert src["github_repo"] == "MNEMOSv2"
    assert src["supports_auto_upgrade"] is True


def test_docref_is_local_no_auto_upgrade() -> None:
    src = get_source("docref")
    assert src is not None
    assert src["source_method"] == "local"
    assert src["source_url"] is None
    assert src["supports_auto_upgrade"] is False


def test_get_source_unknown_returns_none() -> None:
    assert get_source("not-an-extension") is None
