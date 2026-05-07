"""Tests for the ArchiMate OEX reader."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.import_archimate.reader import is_oex_file, parse_oex

REF = Path(__file__).resolve().parents[3] / "docs" / "reference" / "ArchiMate"
SAMPLE = str(REF / "sample-with-view.xml")
MSD = str(REF / "msd-map.xml")


def test_sample_with_view_parses() -> None:
    model = parse_oex(SAMPLE)
    assert model.name == "Iris Sample (with view)"
    assert len(model.elements) == 3
    assert len(model.relationships) == 2
    assert len(model.views) == 1
    view = model.views[0]
    assert view.name == "Overview"
    assert len(view.nodes) == 3
    assert len(view.connections) == 2
    # Position parsing is integer-typed
    assert view.nodes[0].x == 40
    assert view.nodes[0].y == 40
    assert view.nodes[0].w == 120
    assert view.nodes[0].h == 60
    # xsi:type is preserved unprefixed
    types = {e.xsi_type for e in model.elements}
    assert types == {"BusinessActor", "BusinessProcess", "ApplicationService"}
    rel_types = {r.xsi_type for r in model.relationships}
    assert rel_types == {"Serving", "Realization"}


def test_msd_map_parses_real_world() -> None:
    """The user-supplied MSD fixture: 127 elements, 977 relationships, 0 views."""
    model = parse_oex(MSD)
    assert len(model.elements) == 127
    assert len(model.relationships) == 977
    assert len(model.views) == 0
    seen_xsi = {e.xsi_type for e in model.elements}
    assert seen_xsi == {
        "BusinessService", "BusinessObject", "BusinessProcess",
        "BusinessFunction", "Constraint",
    }
    rel_xsi = {r.xsi_type for r in model.relationships}
    assert rel_xsi == {"Association", "Influence", "Serving"}


def test_non_oex_xml_raises(tmp_path) -> None:  # type: ignore[no-untyped-def]
    p = tmp_path / "bogus.xml"
    p.write_text('<?xml version="1.0"?><root xmlns="urn:other"><foo/></root>')
    with pytest.raises(ValueError, match="ArchiMate"):
        parse_oex(str(p))


def test_empty_file_raises(tmp_path) -> None:  # type: ignore[no-untyped-def]
    p = tmp_path / "empty.xml"
    p.write_text("")
    with pytest.raises(ValueError):
        parse_oex(str(p))


def test_namespace_tolerance(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """3.1 and 3.2 namespace URIs must parse identically to 3.0."""
    for variant in ("3.1", "3.2"):
        p = tmp_path / f"v{variant}.xml"
        p.write_text(
            f'<?xml version="1.0"?>'
            f'<model xmlns="http://www.opengroup.org/xsd/archimate/{variant}/" '
            f'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" identifier="m">'
            f'<name>Tiny</name>'
            f'<elements><element identifier="e1" xsi:type="BusinessActor">'
            f'<name>A</name></element></elements>'
            f'</model>'
        )
        m = parse_oex(str(p))
        assert len(m.elements) == 1
        assert m.elements[0].xsi_type == "BusinessActor"


def test_is_oex_file_sniff_positive_and_negative(tmp_path) -> None:  # type: ignore[no-untyped-def]
    assert is_oex_file(SAMPLE) is True
    assert is_oex_file(MSD) is True
    other = tmp_path / "other.xml"
    other.write_text("<?xml version='1.0'?><root xmlns='urn:elsewhere'/>")
    assert is_oex_file(str(other)) is False
    # Non-existent files don't blow up
    assert is_oex_file(os.path.join(str(tmp_path), "missing.xml")) is False
